"""Interactive visual simulator: JSON payloads, a tiny HTTP server, and static demo export.

The browser UI lives in ``ayoe/web``. When it is served by ``ayoe serve`` it calls the
real engine through ``/api/*``; when it is opened as plain static files (for example on
GitHub Pages, or straight from disk) it falls back to ``web/data/demo.js`` produced by
``ayoe export-web``. That file is a script rather than JSON so it also loads over file://.
"""

from __future__ import annotations

import json
import math
import threading
import time
import webbrowser
from collections import defaultdict
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np

from ayoe.analytics import compute_bottlenecks, compute_run_diagnostics, compute_stage_efficiency_correlations
from ayoe.calibration import CALIBRATION_REGISTRY
from ayoe.constants import (
    DEFAULT_SCENARIO_SET,
    STAGE_DURATION_SECONDS,
    STAGE_ENERGY_TARGETS_MEV,
    STAGE_LABELS,
    STAGE_SEQUENCE,
)
from ayoe.engine import run_monte_carlo
from ayoe.models import CycleResult, SimulationConfig
from ayoe.scenarios import SCENARIO_DEFINITIONS, load_scenario, run_scenario_comparison
from ayoe.sensitivity import run_sensitivity_analysis

WEB_ROOT = Path(str(resources.files("ayoe") / "web"))
DEFAULT_DEMO_PATH = WEB_ROOT / "data" / "demo.js"

MAX_RUNS = 5_000
MAX_SENSITIVITY_RUNS = 400
MAX_SCENARIO_RUNS = 1_000
TRACE_COUNT = 60

# Slider definitions shared with the UI. Values are absolute beam settings; stage
# controls are multipliers on the selected scenario's nominal efficiency.
BEAM_CONTROLS: tuple[dict[str, Any], ...] = (
    {"key": "proton_count", "label": "Protons on target", "unit": "p/cycle", "min": 2e12, "max": 3e13, "step": 5e11},
    {"key": "magnetic_field_t", "label": "Magnetic field", "unit": "T", "min": 0.6, "max": 1.8, "step": 0.01},
    {"key": "vacuum_quality", "label": "Vacuum quality", "unit": "", "min": 0.80, "max": 1.0, "step": 0.001},
    {"key": "trap_temperature_k", "label": "Trap temperature", "unit": "K", "min": 0.2, "max": 1.2, "step": 0.01},
    {"key": "mixing_efficiency", "label": "Positron mixing", "unit": "", "min": 0.5, "max": 1.0, "step": 0.005},
    {"key": "positron_inventory_scale", "label": "Positron inventory", "unit": "x", "min": 0.4, "max": 2.0, "step": 0.01},
    {"key": "target_density", "label": "Target density", "unit": "x", "min": 0.6, "max": 1.5, "step": 0.01},
    {"key": "pulse_length_ns", "label": "Pulse length", "unit": "ns", "min": 8.0, "max": 40.0, "step": 0.5},
    {"key": "beam_stability", "label": "Beam stability", "unit": "", "min": 0.90, "max": 1.0, "step": 0.001},
)
STAGE_MULTIPLIER_RANGE = (0.25, 3.0)
VOLATILITY_RANGE = (0.0, 3.0)


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return float(f"{value:.{digits}g}")


def build_config(base: str = "baseline", overrides: dict[str, Any] | None = None) -> SimulationConfig:
    """Load a preset/scenario and apply UI overrides, clamping every value to a safe range."""
    config = load_scenario(base)
    overrides = overrides or {}

    for control in BEAM_CONTROLS:
        value = (overrides.get("beam") or {}).get(control["key"])
        if value is None:
            continue
        clamped = min(max(float(value), control["min"]), control["max"])
        if control["key"] == "proton_count":
            clamped = int(round(clamped))
        setattr(config.beam, control["key"], clamped)

    for stage_name, multiplier in (overrides.get("stage_multipliers") or {}).items():
        if stage_name not in config.stages:
            continue
        factor = min(max(float(multiplier), STAGE_MULTIPLIER_RANGE[0]), STAGE_MULTIPLIER_RANGE[1])
        stage = config.stages[stage_name]
        stage.nominal_efficiency = min(stage.nominal_efficiency * factor, 0.999)
        # Let the clamp window move with the stage so a boosted stage can actually realise its gain.
        stage.max_effective_efficiency = min(max(stage.max_effective_efficiency, stage.nominal_efficiency * 1.5), 0.999)
        stage.min_effective_efficiency = min(stage.min_effective_efficiency, stage.nominal_efficiency)

    volatility = overrides.get("volatility")
    if volatility is not None:
        factor = min(max(float(volatility), VOLATILITY_RANGE[0]), VOLATILITY_RANGE[1])
        config.beam.beam_jitter_sigma *= factor
        for stage in config.stages.values():
            stage.shock_sigma *= factor

    if overrides:
        config.name = f"{base} (custom)"
    return config


def _quantiles(values: np.ndarray) -> dict[str, float]:
    q05, q25, q50, q75, q95 = np.quantile(values, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {"q05": float(q05), "q25": float(q25), "q50": float(q50), "q75": float(q75), "q95": float(q95)}


def _cycle_counts(cycle: CycleResult) -> list[int]:
    return [cycle.stage_results[0].input_count] + [stage.output_count for stage in cycle.stage_results]


def _sample_cycle(cycle: CycleResult) -> dict[str, Any]:
    diagnostics = compute_run_diagnostics(cycle)
    return {
        "run_id": cycle.run_id,
        "final_yield": cycle.final_yield,
        "regime": cycle.latent_state.regime_name if cycle.latent_state is not None else None,
        "counts": _cycle_counts(cycle),
        "efficiencies": [_round(stage.effective_efficiency) for stage in cycle.stage_results],
        "shocks": [_round(stage.sampled_shock, 4) for stage in cycle.stage_results],
        "operational_bottleneck": diagnostics.operational_bottleneck_stage_label,
        "health_score": _round(diagnostics.pipeline_health_score, 4),
        "quality_rating": diagnostics.quality_rating,
    }


def simulation_payload(config: SimulationConfig, *, runs: int, seed: int | None) -> dict[str, Any]:
    runs = int(min(max(runs, 10), MAX_RUNS))
    started = time.perf_counter()
    cycles, summary = run_monte_carlo(config, runs, seed=seed)
    elapsed_ms = (time.perf_counter() - started) * 1_000.0

    counts = np.array([_cycle_counts(cycle) for cycle in cycles], dtype=float)
    yields = counts[:, -1]
    stages = []
    for index, stage_name in enumerate(STAGE_SEQUENCE):
        outputs = counts[:, index + 1]
        inputs = counts[:, index]
        efficiencies = np.array([cycle.stage_results[index].effective_efficiency for cycle in cycles])
        stages.append(
            {
                "key": stage_name,
                "label": STAGE_LABELS[stage_name],
                "energy_mev": STAGE_ENERGY_TARGETS_MEV[stage_name],
                "duration_s": STAGE_DURATION_SECONDS[stage_name],
                "mean_input": float(np.mean(inputs)),
                "output": _quantiles(outputs),
                "mean_effective_efficiency": float(np.mean(efficiencies)),
                "efficiency": _quantiles(efficiencies),
            }
        )

    regimes: dict[str, list[int]] = defaultdict(list)
    for cycle in cycles:
        regimes[cycle.latent_state.regime_name if cycle.latent_state is not None else "n/a"].append(cycle.final_yield)
    regime_rows = [
        {
            "name": name,
            "share": len(values) / len(cycles),
            "mean_yield": float(np.mean(values)),
            "median_yield": float(np.median(values)),
        }
        for name, values in regimes.items()
    ]
    order = ["favourable", "nominal", "stressed", "unstable"]
    regime_rows.sort(key=lambda row: order.index(row["name"]) if row["name"] in order else len(order))

    diagnostics = [compute_run_diagnostics(cycle) for cycle in cycles]
    ranked = sorted(cycles, key=lambda cycle: cycle.final_yield)
    median_cycle = ranked[len(ranked) // 2]

    return {
        "name": config.name,
        "description": config.description,
        "runs": runs,
        "seed": seed,
        "elapsed_ms": round(elapsed_ms, 1),
        "config": config.to_dict(),
        "near_zero_threshold": config.near_zero_threshold,
        "stats": {key: _round(value) for key, value in summary.stats.items()},
        "final_yields": [int(value) for value in yields],
        "initial": _quantiles(counts[:, 0]),
        "stages": stages,
        "bottlenecks": summary.bottlenecks,
        "correlations": compute_stage_efficiency_correlations(cycles),
        "regimes": regime_rows,
        "economics": {
            "mean_cost_units": float(np.mean([row.total_cycle_cost_units for row in diagnostics])),
            "mean_duration_s": float(np.mean([row.cycle_duration_seconds for row in diagnostics])),
            "mean_yield_per_hour": float(np.mean([row.yield_per_hour or 0.0 for row in diagnostics])),
            "mean_stability_score": float(np.mean([row.stability_score for row in diagnostics])),
        },
        "samples": {
            "worst": _sample_cycle(ranked[0]),
            "median": _sample_cycle(median_cycle),
            "best": _sample_cycle(ranked[-1]),
        },
        "traces": [_cycle_counts(cycle) for cycle in cycles[:TRACE_COUNT]],
    }


def sensitivity_payload(config: SimulationConfig, *, runs: int, seed: int | None) -> dict[str, Any]:
    runs = int(min(max(runs, 10), MAX_SENSITIVITY_RUNS))
    started = time.perf_counter()
    report = run_sensitivity_analysis(config, runs=runs, seed=seed)
    grouped: dict[str, dict[str, Any]] = {}
    for row in report.perturbations:
        entry = grouped.setdefault(
            row["parameter"],
            {"parameter": row["parameter"], "group": row["group"], "base_value": row["base_value"]},
        )
        entry[row["direction"]] = _round(row["relative_change"])
        entry[f"elasticity_{row['direction']}"] = _round(row["elasticity"])
    rows = sorted(
        grouped.values(),
        key=lambda row: max(abs(row.get("down") or 0.0), abs(row.get("up") or 0.0)),
        reverse=True,
    )
    return {
        "name": config.name,
        "runs": runs,
        "seed": report.seed,
        "delta": report.delta,
        "base_mean": report.base_summary.stats["mean"],
        "elapsed_ms": round((time.perf_counter() - started) * 1_000.0, 1),
        "rows": rows,
    }


def scenario_payload(*, runs: int, seed: int | None, names: list[str] | None = None) -> dict[str, Any]:
    runs = int(min(max(runs, 10), MAX_SCENARIO_RUNS))
    started = time.perf_counter()
    report, scenario_cycles = run_scenario_comparison(names or list(DEFAULT_SCENARIO_SET), runs=runs, seed=seed)
    rows = []
    for row in report.scenario_results:
        yields = np.array([cycle.final_yield for cycle in scenario_cycles[row.scenario_name]], dtype=float)
        rows.append(
            {
                "name": row.scenario_name,
                "description": row.description,
                "mean": row.mean_yield,
                "std": row.std_yield,
                **_quantiles(yields),
                "probability_near_zero": row.probability_near_zero,
                "mean_cost_units": row.mean_cycle_cost_units,
                "mean_yield_per_cost_unit": row.mean_yield_per_cost_unit,
                "mean_stability_score": row.mean_stability_score,
                "risk_adjusted_score": row.risk_adjusted_score,
                "top_bottleneck": row.top_bottleneck_stage_label,
            }
        )
    return {"runs": runs, "seed": seed, "elapsed_ms": round((time.perf_counter() - started) * 1_000.0, 1), "rows": rows}


def meta_payload() -> dict[str, Any]:
    scenarios = []
    for name in DEFAULT_SCENARIO_SET:
        config = load_scenario(name)
        scenarios.append(
            {
                "name": name,
                "description": SCENARIO_DEFINITIONS[name].description,
                "beam": config.beam.to_dict(),
            }
        )
    calibration = [
        {
            "key": key,
            "label": entry.label,
            "baseline": entry.baseline,
            "units": entry.units,
            "confidence": entry.confidence,
            "rationale": entry.rationale,
            "sources": [source.to_dict() for source in entry.sources],
        }
        for key, entry in CALIBRATION_REGISTRY.items()
    ]
    return {
        "stages": [
            {
                "key": stage,
                "label": STAGE_LABELS[stage],
                "energy_mev": STAGE_ENERGY_TARGETS_MEV[stage],
                "duration_s": STAGE_DURATION_SECONDS[stage],
            }
            for stage in STAGE_SEQUENCE
        ],
        "scenarios": scenarios,
        "beam_controls": list(BEAM_CONTROLS),
        "stage_multiplier_range": list(STAGE_MULTIPLIER_RANGE),
        "volatility_range": list(VOLATILITY_RANGE),
        "calibration": calibration,
    }


def export_demo_dataset(
    path: str | Path,
    *,
    runs: int = 400,
    sensitivity_runs: int = 150,
    seed: int = 42,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_with": {"runs": runs, "sensitivity_runs": sensitivity_runs, "seed": seed},
        "meta": meta_payload(),
        "simulations": {
            name: simulation_payload(load_scenario(name), runs=runs, seed=seed) for name in DEFAULT_SCENARIO_SET
        },
        "sensitivity": {"baseline": sensitivity_payload(load_scenario("baseline"), runs=sensitivity_runs, seed=seed)},
        "scenarios": scenario_payload(runs=runs, seed=seed),
    }
    output_path.write_text(f"window.AYOE_DEMO = {json.dumps(payload, separators=(',', ':'))};\n", encoding="utf-8")
    return output_path


class SimulatorRequestHandler(SimpleHTTPRequestHandler):
    """Serves the static UI plus a JSON API backed by the simulation engine."""

    server_version = "AYOE"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - signature from base class
        if self.path.startswith("/api/"):
            super().log_message(format, *args)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        if self.path.split("?")[0] == "/api/meta":
            self._send_json(meta_payload())
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        route = self.path.split("?")[0]
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            seed = body.get("seed")
            seed = int(seed) if seed not in (None, "") else None
            if route == "/api/simulate":
                config = build_config(body.get("base", "baseline"), body.get("overrides"))
                self._send_json(simulation_payload(config, runs=int(body.get("runs", 400)), seed=seed))
            elif route == "/api/sensitivity":
                config = build_config(body.get("base", "baseline"), body.get("overrides"))
                self._send_json(sensitivity_payload(config, runs=int(body.get("runs", 120)), seed=seed))
            elif route == "/api/scenarios":
                self._send_json(scenario_payload(runs=int(body.get("runs", 300)), seed=seed))
            else:
                self._send_json({"error": f"unknown endpoint {route}"}, HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    handler = partial(SimulatorRequestHandler, directory=str(WEB_ROOT))
    return ThreadingHTTPServer((host, port), handler)


def serve(host: str = "127.0.0.1", port: int = 8765, *, open_browser: bool = True) -> int:
    server = create_server(host, port)
    url = f"http://{host}:{server.server_port}/"
    print(f"AYOE visual simulator running at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping simulator.")
    finally:
        server.server_close()
    return 0
