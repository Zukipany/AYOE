"""Command-line interface for AYOE."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from ayoe.calibration import build_config_calibration_snapshot
from ayoe.config import load_config, list_presets
from ayoe.constants import (
    DEFAULT_FULL_MONTE_CARLO_RUNS,
    DEFAULT_FULL_SENSITIVITY_RUNS,
    DEFAULT_MONTE_CARLO_RUNS,
    DEFAULT_PRESET,
    DEFAULT_SCENARIO_COMPARE_RUNS,
    DEFAULT_SCENARIO_SET,
    DEFAULT_SENSITIVITY_RUNS,
)
from ayoe.analytics import compute_run_diagnostics
from ayoe.engine import run_monte_carlo, simulate_cycle
from ayoe.exports import (
    write_json,
    write_runs_csv,
    write_scenario_comparison_csv,
    write_sensitivity_csv,
    write_stages_csv,
)
from ayoe.models import CycleResult, MonteCarloSummary, ScenarioComparisonReport, SensitivityReport
from ayoe.reporting import write_full_report_artifacts
from ayoe.scenarios import list_scenarios, run_scenario_comparison
from ayoe.sensitivity import run_sensitivity_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ayoe", description="Antimatter Yield Optimization Engine")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="simulate one production cycle")
    _add_common_config_args(run_parser)
    run_parser.add_argument("--seed", type=int, default=None, help="seed for deterministic output")
    run_parser.add_argument("--json-out", type=Path, default=None, help="write JSON summary")
    run_parser.add_argument("--stage-csv", type=Path, default=None, help="write stage-level CSV")

    mc_parser = subparsers.add_parser("monte-carlo", help="run repeated Monte Carlo simulations")
    _add_common_config_args(mc_parser)
    mc_parser.add_argument("--runs", type=int, default=DEFAULT_MONTE_CARLO_RUNS, help="number of runs")
    mc_parser.add_argument("--seed", type=int, default=None, help="seed for reproducible Monte Carlo runs")
    mc_parser.add_argument("--json-out", type=Path, default=None, help="write JSON summary")
    mc_parser.add_argument("--runs-csv", type=Path, default=None, help="write run-level CSV")
    mc_parser.add_argument("--stage-csv", type=Path, default=None, help="write stage-level CSV")

    sensitivity_parser = subparsers.add_parser("sensitivity", help="run one-at-a-time sensitivity analysis")
    _add_common_config_args(sensitivity_parser)
    sensitivity_parser.add_argument("--runs", type=int, default=DEFAULT_SENSITIVITY_RUNS, help="Monte Carlo runs per scenario")
    sensitivity_parser.add_argument("--seed", type=int, default=None, help="seed for reproducible output")
    sensitivity_parser.add_argument("--delta", type=float, default=None, help="relative perturbation size, defaults to config value")
    sensitivity_parser.add_argument("--json-out", type=Path, default=None, help="write JSON summary")
    sensitivity_parser.add_argument("--csv-out", type=Path, default=None, help="write perturbation CSV")

    scenario_parser = subparsers.add_parser("scenario-compare", help="compare named operating scenarios")
    scenario_parser.add_argument(
        "--scenarios",
        nargs="*",
        default=list(DEFAULT_SCENARIO_SET),
        choices=list_scenarios(),
        help="scenario names to compare",
    )
    scenario_parser.add_argument("--runs", type=int, default=DEFAULT_SCENARIO_COMPARE_RUNS, help="Monte Carlo runs per scenario")
    scenario_parser.add_argument("--seed", type=int, default=None, help="seed for reproducible scenario comparison")
    scenario_parser.add_argument("--json-out", type=Path, default=None, help="write JSON summary")
    scenario_parser.add_argument("--csv-out", type=Path, default=None, help="write scenario comparison CSV")

    full_parser = subparsers.add_parser("full", help="run the full beta workflow and export artifacts")
    _add_common_config_args(full_parser)
    full_parser.add_argument("--seed", type=int, default=None, help="root seed for reproducible workflow output")
    full_parser.add_argument(
        "--monte-carlo-runs",
        type=int,
        default=DEFAULT_FULL_MONTE_CARLO_RUNS,
        help="number of Monte Carlo runs in the workflow",
    )
    full_parser.add_argument(
        "--sensitivity-runs",
        type=int,
        default=DEFAULT_FULL_SENSITIVITY_RUNS,
        help="number of Monte Carlo runs per sensitivity scenario",
    )
    full_parser.add_argument(
        "--scenario-runs",
        type=int,
        default=DEFAULT_SCENARIO_COMPARE_RUNS,
        help="number of Monte Carlo runs per scenario in the comparison report",
    )
    full_parser.add_argument(
        "--scenarios",
        nargs="*",
        default=list(DEFAULT_SCENARIO_SET),
        choices=list_scenarios(),
        help="scenario names to include in scenario comparison",
    )
    full_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/latest"),
        help="directory for JSON and CSV workflow artifacts",
    )

    return parser


def _add_common_config_args(parser: argparse.ArgumentParser) -> None:
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument("--config", type=Path, default=None, help="path to a TOML config")
    config_group.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        choices=list_presets(),
        help="built-in preset name",
    )


def _resolve_config(args: argparse.Namespace):
    if args.config is not None:
        return load_config(path=args.config)
    return load_config(preset=args.preset)


def _cycle_payload(
    cycle: CycleResult,
    config_dict: dict[str, object],
    calibration_snapshot: dict[str, object],
) -> dict[str, object]:
    payload = cycle.to_dict()
    payload["diagnostics"] = compute_run_diagnostics(cycle).to_dict()
    payload["config_snapshot"] = config_dict
    payload["calibration_snapshot"] = calibration_snapshot
    return payload


def _monte_carlo_payload(
    summary: MonteCarloSummary,
    config_dict: dict[str, object],
    calibration_snapshot: dict[str, object],
) -> dict[str, object]:
    payload = summary.to_dict()
    payload["config_snapshot"] = config_dict
    payload["calibration_snapshot"] = calibration_snapshot
    return payload


def _sensitivity_payload(
    report: SensitivityReport,
    config_dict: dict[str, object],
    calibration_snapshot: dict[str, object],
) -> dict[str, object]:
    payload = report.to_dict()
    payload["config_snapshot"] = config_dict
    payload["calibration_snapshot"] = calibration_snapshot
    return payload


def _scenario_payload(report: ScenarioComparisonReport) -> dict[str, object]:
    return report.to_dict()


def _format_ratio(value: float) -> str:
    if value >= 0.01:
        return f"{value:.2%}"
    return f"{value:.6e}"


def _print_cycle_summary(cycle: CycleResult) -> None:
    diagnostics = compute_run_diagnostics(cycle)
    print(
        f"AYOE cycle | config={cycle.config_name} | run_id={cycle.run_id} | "
        f"seed={cycle.seed} | final_yield={cycle.final_yield}"
    )
    frame = pd.DataFrame(
        [
            {
                "stage": metric.stage_label,
                "input": metric.input_count,
                "output": metric.output_count,
                "loss": metric.lost_count,
                "base_eff": round(metric.sampled_base_efficiency, 6),
                "efficiency": round(metric.effective_efficiency, 6),
                "realized_eff": round(metric.realized_efficiency, 6),
                "latent_mod": round(metric.latent_modifier, 6),
                "shock": round(metric.sampled_shock, 6),
                "loss_pct": f"{metric.stage_loss_ratio:.2%}",
                "cum_survival": _format_ratio(metric.cumulative_survival_ratio),
            }
            for metric in diagnostics.stage_metrics
        ]
    )
    print(frame.to_string(index=False))
    if cycle.latent_state is not None:
        latent_frame = pd.DataFrame(
            [
                {"latent": "regime", "value": cycle.latent_state.regime_name},
                {"latent": "beam_quality", "value": round(cycle.latent_state.beam_quality, 6)},
                {"latent": "cooling_quality", "value": round(cycle.latent_state.cooling_quality, 6)},
                {"latent": "system_stability", "value": round(cycle.latent_state.system_stability, 6)},
                {"latent": "timing_precision", "value": round(cycle.latent_state.timing_precision, 6)},
                {"latent": "shock_pressure", "value": round(cycle.latent_state.shock_pressure, 6)},
                {"latent": "trap_readiness", "value": round(cycle.latent_state.trap_readiness, 6)},
                {"latent": "formation_readiness", "value": round(cycle.latent_state.formation_readiness, 6)},
            ]
        )
        print("\nRun latent state")
        print(latent_frame.to_string(index=False))
    diagnostic_frame = pd.DataFrame(
        [
            {"metric": "scale_bottleneck_stage", "value": diagnostics.largest_scale_loss_stage_label},
            {"metric": "operational_bottleneck_stage", "value": diagnostics.operational_bottleneck_stage_label},
            {"metric": "biggest_proportional_drop_stage", "value": diagnostics.biggest_proportional_drop_stage_label},
            {"metric": "strongest_operational_stage", "value": diagnostics.strongest_operational_stage_label},
            {"metric": "highest_shock_stage", "value": diagnostics.highest_shock_stage_label},
            {"metric": "final_survival_ratio", "value": _format_ratio(diagnostics.final_yield_ratio)},
            {"metric": "total_loss_ratio", "value": f"{diagnostics.total_loss_ratio:.2%}"},
            {
                "metric": "realized_vs_expected_yield",
                "value": (
                    "n/a"
                    if diagnostics.realized_vs_expected_yield is None
                    else f"{diagnostics.realized_vs_expected_yield:.3f}x"
                ),
            },
            {"metric": "stability_score", "value": f"{diagnostics.stability_score:.1f}"},
            {"metric": "pipeline_health_score", "value": f"{diagnostics.pipeline_health_score:.1f}"},
            {"metric": "regime_name", "value": diagnostics.regime_name or "n/a"},
            {"metric": "mean_stage_shock_severity", "value": f"{diagnostics.mean_stage_shock_severity:.4f}"},
            {"metric": "cycle_cost_units", "value": f"{diagnostics.total_cycle_cost_units:.2f}"},
            {"metric": "cycle_duration_minutes", "value": f"{diagnostics.cycle_duration_seconds / 60.0:.2f}"},
            {
                "metric": "yield_per_cost_unit",
                "value": "n/a" if diagnostics.yield_per_cost_unit is None else f"{diagnostics.yield_per_cost_unit:.4f}",
            },
            {
                "metric": "yield_per_hour",
                "value": "n/a" if diagnostics.yield_per_hour is None else f"{diagnostics.yield_per_hour:.2f}",
            },
            {"metric": "quality_rating", "value": diagnostics.quality_rating},
        ]
    )
    print("\nRun diagnostics")
    print(diagnostic_frame.to_string(index=False))


def _print_monte_carlo_summary(summary: MonteCarloSummary) -> None:
    print(
        f"AYOE Monte Carlo | config={summary.config_name} | runs={summary.run_count} | "
        f"seed={summary.seed}"
    )
    stats_frame = pd.DataFrame(
        [{"metric": key, "value": value} for key, value in summary.stats.items()]
    )
    print(stats_frame.to_string(index=False))
    top_bottlenecks = pd.DataFrame(summary.bottlenecks[:5])
    if not top_bottlenecks.empty:
        print("\nTop bottlenecks")
        print(top_bottlenecks.to_string(index=False))


def _print_sensitivity_summary(report: SensitivityReport) -> None:
    print(
        f"AYOE sensitivity | config={report.config_name} | runs={report.runs} | "
        f"seed={report.seed} | delta={report.delta:.2%}"
    )
    base_stats = pd.DataFrame(
        [{"metric": key, "value": value} for key, value in report.base_summary.stats.items()]
    )
    print(base_stats.to_string(index=False))

    perturbations = pd.DataFrame(report.perturbations[:10])
    if not perturbations.empty:
        print("\nTop parameter impacts")
        print(perturbations.to_string(index=False))

    correlations = pd.DataFrame(report.stage_efficiency_correlations[:5])
    if not correlations.empty:
        print("\nStage efficiency correlations")
        print(correlations.to_string(index=False))


def _print_scenario_summary(report: ScenarioComparisonReport) -> None:
    print(f"AYOE scenario comparison | runs_per_scenario={report.run_count} | seed={report.seed}")
    frame = pd.DataFrame(
        [
            {
                "scenario": row.scenario_name,
                "mean_yield": round(row.mean_yield, 3),
                "std_yield": round(row.std_yield, 3),
                "mean_cost": round(row.mean_cycle_cost_units, 3),
                "stability": round(row.mean_stability_score, 2),
                "yield_per_cost": (
                    None if row.mean_yield_per_cost_unit is None else round(row.mean_yield_per_cost_unit, 5)
                ),
                "risk_adjusted": round(row.risk_adjusted_score, 3),
                "top_bottleneck": row.top_bottleneck_stage_label,
            }
            for row in report.scenario_results
        ]
    )
    print(frame.to_string(index=False))


def _derive_workflow_seeds(seed: int | None) -> tuple[int, int, int, int]:
    if seed is None:
        root = np.random.SeedSequence()
    else:
        root = np.random.SeedSequence(seed)
    child_sequences = root.spawn(4)
    cycle_seed, monte_carlo_seed, sensitivity_seed, scenario_seed = (
        int(child.generate_state(1, dtype=np.uint64)[0]) for child in child_sequences
    )
    return cycle_seed, monte_carlo_seed, sensitivity_seed, scenario_seed


def _default_output_dir(config_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("outputs") / f"{config_name}_{timestamp}"


def _run_full_workflow(
    config,
    *,
    seed: int | None,
    monte_carlo_runs: int,
    sensitivity_runs: int,
    scenario_runs: int,
    scenario_names: list[str],
    output_dir: Path,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    cycle_seed, monte_carlo_seed, sensitivity_seed, scenario_seed = _derive_workflow_seeds(seed)
    calibration_snapshot = build_config_calibration_snapshot(config)

    cycle = simulate_cycle(config, seed=cycle_seed, run_id=1)
    cycles, summary = run_monte_carlo(config, monte_carlo_runs, seed=monte_carlo_seed)
    report = run_sensitivity_analysis(
        config,
        runs=sensitivity_runs,
        seed=sensitivity_seed,
        delta=None,
    )
    scenario_report, scenario_cycles = run_scenario_comparison(
        scenario_names,
        runs=scenario_runs,
        seed=scenario_seed,
    )
    chart_manifest = write_full_report_artifacts(
        config,
        cycle,
        cycles,
        report,
        scenario_report,
        scenario_cycles,
        output_dir / "charts",
        seed=scenario_seed,
    )

    print(
        f"AYOE full workflow | config={config.name} | output_dir={output_dir} | "
        f"cycle_seed={cycle_seed} | monte_carlo_seed={monte_carlo_seed} | "
        f"sensitivity_seed={sensitivity_seed} | scenario_seed={scenario_seed}\n"
    )
    _print_cycle_summary(cycle)
    print()
    _print_monte_carlo_summary(summary)
    print()
    _print_sensitivity_summary(report)
    print()
    _print_scenario_summary(scenario_report)

    write_json(output_dir / "cycle.json", _cycle_payload(cycle, config.to_dict(), calibration_snapshot))
    write_stages_csv(output_dir / "cycle_stages.csv", [cycle])
    write_json(
        output_dir / "monte_carlo_summary.json",
        _monte_carlo_payload(summary, config.to_dict(), calibration_snapshot),
    )
    write_runs_csv(output_dir / "monte_carlo_runs.csv", cycles)
    write_stages_csv(output_dir / "monte_carlo_stages.csv", cycles)
    write_json(
        output_dir / "sensitivity.json",
        _sensitivity_payload(report, config.to_dict(), calibration_snapshot),
    )
    write_sensitivity_csv(output_dir / "sensitivity.csv", report)
    write_json(output_dir / "scenario_comparison.json", _scenario_payload(scenario_report))
    write_scenario_comparison_csv(output_dir / "scenario_comparison.csv", scenario_report)
    write_json(output_dir / "calibration.json", calibration_snapshot)
    write_json(output_dir / "chart_manifest.json", chart_manifest)

    print(f"\nWrote workflow artifacts to {output_dir}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    defaulted_to_full = not raw_args
    if defaulted_to_full:
        raw_args = ["full", "--preset", DEFAULT_PRESET]

    args = parser.parse_args(raw_args)
    config = _resolve_config(args) if hasattr(args, "config") or hasattr(args, "preset") else None

    if args.command == "full":
        output_dir = args.output_dir
        if defaulted_to_full and output_dir == Path("outputs/latest"):
            output_dir = _default_output_dir(config.name)
            print("No command provided; defaulting to the full beta workflow.\n")
        return _run_full_workflow(
            config,
            seed=args.seed,
            monte_carlo_runs=args.monte_carlo_runs,
            sensitivity_runs=args.sensitivity_runs,
            scenario_runs=args.scenario_runs,
            scenario_names=args.scenarios,
            output_dir=output_dir,
        )

    if args.command == "run":
        cycle = simulate_cycle(config, seed=args.seed, run_id=1)
        _print_cycle_summary(cycle)
        payload = _cycle_payload(cycle, config.to_dict(), build_config_calibration_snapshot(config))
        if args.json_out is not None:
            path = write_json(args.json_out, payload)
            print(f"\nWrote JSON summary to {path}")
        if args.stage_csv is not None:
            path = write_stages_csv(args.stage_csv, [cycle])
            print(f"Wrote stage CSV to {path}")
        return 0

    if args.command == "monte-carlo":
        cycles, summary = run_monte_carlo(config, args.runs, seed=args.seed)
        _print_monte_carlo_summary(summary)
        payload = _monte_carlo_payload(
            summary,
            config.to_dict(),
            build_config_calibration_snapshot(config),
        )
        if args.json_out is not None:
            path = write_json(args.json_out, payload)
            print(f"\nWrote JSON summary to {path}")
        if args.runs_csv is not None:
            path = write_runs_csv(args.runs_csv, cycles)
            print(f"Wrote run CSV to {path}")
        if args.stage_csv is not None:
            path = write_stages_csv(args.stage_csv, cycles)
            print(f"Wrote stage CSV to {path}")
        return 0

    if args.command == "sensitivity":
        report = run_sensitivity_analysis(config, runs=args.runs, seed=args.seed, delta=args.delta)
        _print_sensitivity_summary(report)
        payload = _sensitivity_payload(
            report,
            config.to_dict(),
            build_config_calibration_snapshot(config),
        )
        if args.json_out is not None:
            path = write_json(args.json_out, payload)
            print(f"\nWrote JSON summary to {path}")
        if args.csv_out is not None:
            path = write_sensitivity_csv(args.csv_out, report)
            print(f"Wrote sensitivity CSV to {path}")
        return 0

    if args.command == "scenario-compare":
        report, _ = run_scenario_comparison(args.scenarios, runs=args.runs, seed=args.seed)
        _print_scenario_summary(report)
        payload = _scenario_payload(report)
        if args.json_out is not None:
            path = write_json(args.json_out, payload)
            print(f"\nWrote JSON summary to {path}")
        if args.csv_out is not None:
            path = write_scenario_comparison_csv(args.csv_out, report)
            print(f"Wrote scenario comparison CSV to {path}")
        return 0

    parser.error(f"unsupported command {args.command!r}")
    return 2
