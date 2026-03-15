"""Premium guided runner layered on top of the existing AYOE engine."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Sequence

import numpy as np

from ayoe.analytics import compute_run_diagnostics
from ayoe.calibration import build_config_calibration_snapshot
from ayoe.config import load_config, list_presets
from ayoe.constants import (
    DEFAULT_FULL_MONTE_CARLO_RUNS,
    DEFAULT_FULL_SENSITIVITY_RUNS,
    DEFAULT_PRESET,
    DEFAULT_SCENARIO_COMPARE_RUNS,
    DEFAULT_SCENARIO_SET,
)
from ayoe.engine import run_monte_carlo, simulate_cycle
from ayoe.exports import (
    write_json,
    write_runs_csv,
    write_scenario_comparison_csv,
    write_sensitivity_csv,
    write_stages_csv,
)
from ayoe.premium_reporting import (
    build_cycle_table,
    build_monte_carlo_table,
    build_scenario_table,
    build_sensitivity_table,
    explain_monte_carlo,
    explain_scenarios,
    explain_sensitivity,
    explain_single_run,
    write_guided_reports,
)
from ayoe.presentation import build_welcome_text
from ayoe.reporting import write_full_report_artifacts
from ayoe.scenarios import list_scenarios, run_scenario_comparison
from ayoe.sensitivity import run_sensitivity_analysis
from ayoe.ui import section, wrap_block
from ayoe.walkthrough import build_walkthrough_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ayoe-enhanced",
        description="Premium guided experience for Antimatter Yield Optimization Engine",
    )
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument("--config", type=Path, default=None, help="path to a TOML config")
    config_group.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        choices=list_presets(),
        help="built-in preset name",
    )
    parser.add_argument("--seed", type=int, default=None, help="root seed for reproducible guided runs")
    parser.add_argument(
        "--monte-carlo-runs",
        type=int,
        default=DEFAULT_FULL_MONTE_CARLO_RUNS,
        help="number of Monte Carlo runs in the guided experience",
    )
    parser.add_argument(
        "--sensitivity-runs",
        type=int,
        default=DEFAULT_FULL_SENSITIVITY_RUNS,
        help="number of Monte Carlo runs per sensitivity perturbation",
    )
    parser.add_argument(
        "--scenario-runs",
        type=int,
        default=DEFAULT_SCENARIO_COMPARE_RUNS,
        help="number of Monte Carlo runs per scenario comparison",
    )
    parser.add_argument(
        "--scenarios",
        nargs="*",
        default=list(DEFAULT_SCENARIO_SET),
        choices=list_scenarios(),
        help="scenario names to compare",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="directory for guided artifacts; defaults to outputs/<config>_guided_<timestamp>",
    )
    return parser


def _resolve_config(args: argparse.Namespace):
    if args.config is not None:
        return load_config(path=args.config)
    return load_config(preset=args.preset)


def _derive_seeds(seed: int | None) -> tuple[int, int, int, int]:
    root = np.random.SeedSequence(seed)
    children = root.spawn(4)
    return tuple(int(child.generate_state(1, dtype=np.uint64)[0]) for child in children)  # type: ignore[return-value]


def _default_output_dir(config_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("outputs") / f"{config_name}_guided_{timestamp}"


def _cycle_payload(config, cycle):
    return {
        **cycle.to_dict(),
        "diagnostics": compute_run_diagnostics(cycle).to_dict(),
        "config_snapshot": config.to_dict(),
        "calibration_snapshot": build_config_calibration_snapshot(config),
    }


def _print_guided_results(config, cycle, summary, sensitivity_report, scenario_report) -> None:
    print(section("Guided Interpretation"))
    print(wrap_block(explain_single_run(cycle)))
    print()
    print(build_cycle_table(cycle).to_string(index=False))
    print()
    print(section("Monte Carlo Reading"))
    print(wrap_block(explain_monte_carlo(summary)))
    print()
    print(build_monte_carlo_table(summary).to_string(index=False))
    print()
    print(section("Sensitivity Reading"))
    print(wrap_block(explain_sensitivity(sensitivity_report)))
    print()
    print(build_sensitivity_table(sensitivity_report, top_n=8).to_string(index=False))
    print()
    print(section("Scenario Reading"))
    print(wrap_block(explain_scenarios(scenario_report)))
    print()
    print(build_scenario_table(scenario_report).to_string(index=False))


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    config = _resolve_config(args)
    output_dir = args.output_dir or _default_output_dir(config.name)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(build_welcome_text(config.name))
    print()
    print(build_walkthrough_text())
    print()

    cycle_seed, monte_carlo_seed, sensitivity_seed, scenario_seed = _derive_seeds(args.seed)
    cycle = simulate_cycle(config, seed=cycle_seed, run_id=1)
    monte_carlo_cycles, monte_carlo_summary = run_monte_carlo(
        config,
        args.monte_carlo_runs,
        seed=monte_carlo_seed,
    )
    sensitivity_report = run_sensitivity_analysis(
        config,
        runs=args.sensitivity_runs,
        seed=sensitivity_seed,
        delta=None,
    )
    scenario_report, scenario_cycles = run_scenario_comparison(
        args.scenarios,
        runs=args.scenario_runs,
        seed=scenario_seed,
    )

    chart_manifest = write_full_report_artifacts(
        config,
        cycle,
        monte_carlo_cycles,
        sensitivity_report,
        scenario_report,
        scenario_cycles,
        output_dir / "charts",
        seed=scenario_seed,
    )
    guided_reports = write_guided_reports(
        config,
        cycle,
        monte_carlo_summary,
        sensitivity_report,
        scenario_report,
        chart_manifest,
        output_dir,
    )

    write_json(output_dir / "cycle.json", _cycle_payload(config, cycle))
    write_stages_csv(output_dir / "cycle_stages.csv", [cycle])
    write_json(
        output_dir / "monte_carlo_summary.json",
        {
            **monte_carlo_summary.to_dict(),
            "config_snapshot": config.to_dict(),
            "calibration_snapshot": build_config_calibration_snapshot(config),
        },
    )
    write_runs_csv(output_dir / "monte_carlo_runs.csv", monte_carlo_cycles)
    write_stages_csv(output_dir / "monte_carlo_stages.csv", monte_carlo_cycles)
    write_json(
        output_dir / "sensitivity.json",
        {
            **sensitivity_report.to_dict(),
            "config_snapshot": config.to_dict(),
            "calibration_snapshot": build_config_calibration_snapshot(config),
        },
    )
    write_sensitivity_csv(output_dir / "sensitivity.csv", sensitivity_report)
    write_json(output_dir / "scenario_comparison.json", scenario_report.to_dict())
    write_scenario_comparison_csv(output_dir / "scenario_comparison.csv", scenario_report)
    write_json(output_dir / "calibration.json", build_config_calibration_snapshot(config))
    write_json(output_dir / "chart_manifest.json", chart_manifest)
    write_json(output_dir / "guided_manifest.json", {**chart_manifest, **guided_reports})

    _print_guided_results(
        config,
        cycle,
        monte_carlo_summary,
        sensitivity_report,
        scenario_report,
    )
    print()
    print(section("Artifacts"))
    print(wrap_block(f"Guided output written to {output_dir}"))
    for name, path in {**chart_manifest, **guided_reports}.items():
        print(f"- {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
