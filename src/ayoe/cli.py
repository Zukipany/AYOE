# Source code is private. This file shows only its classes and function signatures.

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
from ayoe.constants import DEFAULT_FULL_MONTE_CARLO_RUNS, DEFAULT_FULL_SENSITIVITY_RUNS, DEFAULT_MONTE_CARLO_RUNS, DEFAULT_PRESET, DEFAULT_SCENARIO_COMPARE_RUNS, DEFAULT_SCENARIO_SET, DEFAULT_SENSITIVITY_RUNS
from ayoe.analytics import compute_run_diagnostics
from ayoe.engine import run_monte_carlo, simulate_cycle
from ayoe.exports import write_json, write_runs_csv, write_scenario_comparison_csv, write_sensitivity_csv, write_stages_csv
from ayoe.models import CycleResult, MonteCarloSummary, ScenarioComparisonReport, SensitivityReport
from ayoe.reporting import write_full_report_artifacts
from ayoe.scenarios import list_scenarios, run_scenario_comparison
from ayoe.sensitivity import run_sensitivity_analysis


def build_parser() -> argparse.ArgumentParser:
    ...


def _add_common_config_args(parser: argparse.ArgumentParser) -> None:
    ...


def _resolve_config(args: argparse.Namespace):
    ...


def _cycle_payload(cycle: CycleResult, config_dict: dict[str, object], calibration_snapshot: dict[str, object]) -> dict[str, object]:
    ...


def _monte_carlo_payload(summary: MonteCarloSummary, config_dict: dict[str, object], calibration_snapshot: dict[str, object]) -> dict[str, object]:
    ...


def _sensitivity_payload(report: SensitivityReport, config_dict: dict[str, object], calibration_snapshot: dict[str, object]) -> dict[str, object]:
    ...


def _scenario_payload(report: ScenarioComparisonReport) -> dict[str, object]:
    ...


def _format_efficiency(value: float) -> str:
    ...


def _format_ratio(value: float) -> str:
    ...


def _print_cycle_summary(cycle: CycleResult) -> None:
    ...


def _print_monte_carlo_summary(summary: MonteCarloSummary) -> None:
    ...


def _print_sensitivity_summary(report: SensitivityReport) -> None:
    ...


def _print_scenario_summary(report: ScenarioComparisonReport) -> None:
    ...


def _derive_workflow_seeds(seed: int | None) -> tuple[int, int, int, int]:
    ...


def _default_output_dir(config_name: str) -> Path:
    ...


def _run_full_workflow(config, *, seed: int | None, monte_carlo_runs: int, sensitivity_runs: int, scenario_runs: int, scenario_names: list[str], output_dir: Path) -> int:
    ...


def main(argv: Sequence[str] | None=None) -> int:
    ...
