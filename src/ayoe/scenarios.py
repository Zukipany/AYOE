"""Scenario registry and multi-scenario comparison utilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ayoe.analytics import compute_bottleneck_frequencies, compute_run_diagnostics
from ayoe.config import load_preset
from ayoe.constants import DEFAULT_SCENARIO_COMPARE_RUNS, DEFAULT_SCENARIO_SET
from ayoe.engine import run_monte_carlo
from ayoe.models import CycleResult, ScenarioComparisonReport, ScenarioResult, SimulationConfig


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    name: str
    description: str
    base_preset: str


SCENARIO_DEFINITIONS: dict[str, ScenarioDefinition] = {
    "conservative": ScenarioDefinition(
        name="conservative",
        description="Lower-volatility operating mode that prefers stability over absolute yield.",
        base_preset="conservative",
    ),
    "baseline": ScenarioDefinition(
        name="baseline",
        description="Balanced reference configuration with calibrated stochastic ranges.",
        base_preset="baseline",
    ),
    "aggressive": ScenarioDefinition(
        name="aggressive",
        description="Higher-throughput operating mode that accepts more volatility for yield.",
        base_preset="aggressive",
    ),
    "high-cooling": ScenarioDefinition(
        name="high-cooling",
        description="Improves deceleration and low-energy capture with colder trapping conditions.",
        base_preset="baseline",
    ),
    "high-trap": ScenarioDefinition(
        name="high-trap",
        description="Biases the system toward stronger late-stage capture and usable yield extraction.",
        base_preset="baseline",
    ),
    "high-positron": ScenarioDefinition(
        name="high-positron",
        description="Increases positron inventory and mixing performance to lift formation output.",
        base_preset="baseline",
    ),
    "low-volatility": ScenarioDefinition(
        name="low-volatility",
        description="Reduces shock amplitudes and jitter to study smoother operational regimes.",
        base_preset="baseline",
    ),
    "stress-test": ScenarioDefinition(
        name="stress-test",
        description="Applies degraded machine quality and amplified shocks to probe resilience.",
        base_preset="baseline",
    ),
}


def list_scenarios() -> list[str]:
    return list(DEFAULT_SCENARIO_SET)


def load_scenario(name: str) -> SimulationConfig:
    if name not in SCENARIO_DEFINITIONS:
        available = ", ".join(list_scenarios())
        raise ValueError(f"unknown scenario {name!r}. Available scenarios: {available}")

    definition = SCENARIO_DEFINITIONS[name]
    config = load_preset(definition.base_preset)
    config.name = definition.name
    config.description = definition.description

    if name == "high-cooling":
        config.beam.trap_temperature_k *= 0.78
        config.stages["ad_survival"].nominal_efficiency = min(
            config.stages["ad_survival"].nominal_efficiency * 1.05,
            0.98,
        )
        config.stages["elena_survival"].nominal_efficiency = min(
            config.stages["elena_survival"].nominal_efficiency * 1.08,
            0.99,
        )
        config.stages["trap_capture"].nominal_efficiency = min(
            config.stages["trap_capture"].nominal_efficiency * 1.18,
            0.75,
        )
    elif name == "high-trap":
        config.beam.magnetic_field_t *= 1.12
        config.stages["trap_capture"].nominal_efficiency = min(
            config.stages["trap_capture"].nominal_efficiency * 1.24,
            0.80,
        )
        config.stages["final_usable_yield"].nominal_efficiency = min(
            config.stages["final_usable_yield"].nominal_efficiency * 1.06,
            0.995,
        )
    elif name == "high-positron":
        config.beam.positron_inventory_scale *= 1.35
        config.beam.mixing_efficiency = min(config.beam.mixing_efficiency * 1.08, 0.99)
        config.stages["antihydrogen_formation"].nominal_efficiency = min(
            config.stages["antihydrogen_formation"].nominal_efficiency * 1.20,
            0.60,
        )
    elif name == "low-volatility":
        config.beam.beam_jitter_sigma *= 0.55
        for stage in config.stages.values():
            stage.shock_sigma *= 0.60
            stage.degradation *= 0.90
    elif name == "stress-test":
        config.beam.beam_stability *= 0.965
        config.beam.vacuum_quality *= 0.975
        config.beam.trap_temperature_k *= 1.18
        config.beam.mixing_efficiency *= 0.92
        config.beam.positron_inventory_scale *= 0.94
        config.beam.beam_jitter_sigma *= 1.60
        for stage_name, stage in config.stages.items():
            stage.shock_sigma *= 1.55
            stage.degradation = min(stage.degradation * 1.30 + 0.01, 0.40)
            if stage_name in {"trap_capture", "antihydrogen_formation", "final_usable_yield"}:
                stage.nominal_efficiency *= 0.90

    return config


def run_scenario_comparison(
    scenario_names: list[str] | None = None,
    *,
    runs: int = DEFAULT_SCENARIO_COMPARE_RUNS,
    seed: int | None = None,
) -> tuple[ScenarioComparisonReport, dict[str, list[CycleResult]]]:
    names = scenario_names or list(DEFAULT_SCENARIO_SET)
    if seed is None:
        root = np.random.SeedSequence()
    else:
        root = np.random.SeedSequence(seed)

    child_sequences = root.spawn(len(names))
    scenario_cycles: dict[str, list[CycleResult]] = {}
    scenario_results: list[ScenarioResult] = []

    for name, child in zip(names, child_sequences):
        config = load_scenario(name)
        scenario_seed = int(child.generate_state(1, dtype=np.uint64)[0])
        cycles, summary = run_monte_carlo(config, runs=runs, seed=scenario_seed)
        scenario_cycles[name] = cycles
        diagnostics = [compute_run_diagnostics(cycle) for cycle in cycles]
        mean_cycle_cost = float(np.mean([row.total_cycle_cost_units for row in diagnostics]))
        mean_stability_score = float(np.mean([row.stability_score for row in diagnostics]))
        mean_yield_per_cost = (
            float(np.mean([row.yield_per_cost_unit for row in diagnostics if row.yield_per_cost_unit is not None]))
            if any(row.yield_per_cost_unit is not None for row in diagnostics)
            else None
        )
        mean_yield_per_hour = (
            float(np.mean([row.yield_per_hour for row in diagnostics if row.yield_per_hour is not None]))
            if any(row.yield_per_hour is not None for row in diagnostics)
            else None
        )
        bottleneck_rows = compute_bottleneck_frequencies(cycles)
        top_bottleneck = bottleneck_rows[0] if bottleneck_rows else {}
        mean_yield = float(summary.stats["mean"] or 0.0)
        std_yield = float(summary.stats["std"] or 0.0)
        yield_per_cost_term = mean_yield_per_cost if mean_yield_per_cost is not None else 0.0
        risk_adjusted_score = yield_per_cost_term * (mean_stability_score / 100.0) * 1_000.0
        scenario_results.append(
            ScenarioResult(
                scenario_name=name,
                description=config.description,
                run_count=runs,
                seed=scenario_seed,
                mean_yield=mean_yield,
                median_yield=float(summary.stats["median"] or 0.0),
                std_yield=std_yield,
                probability_near_zero=float(summary.stats["probability_near_zero"] or 0.0),
                mean_cycle_cost_units=mean_cycle_cost,
                mean_yield_per_cost_unit=mean_yield_per_cost,
                mean_yield_per_hour=mean_yield_per_hour,
                mean_stability_score=mean_stability_score,
                risk_adjusted_score=risk_adjusted_score,
                top_bottleneck_stage_name=top_bottleneck.get("stage_name"),
                top_bottleneck_stage_label=top_bottleneck.get("stage_label"),
                summary=summary,
            )
        )

    report = ScenarioComparisonReport(
        run_count=runs,
        seed=seed,
        scenario_results=sorted(scenario_results, key=lambda row: row.risk_adjusted_score, reverse=True),
    )
    return report, scenario_cycles
