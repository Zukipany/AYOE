# Source code is private. This file shows only its classes and function signatures.

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
from ayoe.constants import DEFAULT_FULL_MONTE_CARLO_RUNS, DEFAULT_FULL_SENSITIVITY_RUNS, DEFAULT_PRESET, DEFAULT_SCENARIO_COMPARE_RUNS, DEFAULT_SCENARIO_SET
from ayoe.engine import run_monte_carlo, simulate_cycle
from ayoe.exports import write_json, write_runs_csv, write_scenario_comparison_csv, write_sensitivity_csv, write_stages_csv
from ayoe.premium_reporting import build_cycle_table, build_monte_carlo_table, build_scenario_table, build_sensitivity_table, explain_monte_carlo, explain_scenarios, explain_sensitivity, explain_single_run, write_guided_reports
from ayoe.presentation import build_welcome_text
from ayoe.reporting import write_full_report_artifacts
from ayoe.scenarios import list_scenarios, run_scenario_comparison
from ayoe.sensitivity import run_sensitivity_analysis
from ayoe.ui import section, wrap_block
from ayoe.walkthrough import build_walkthrough_text


def build_parser() -> argparse.ArgumentParser:
    ...


def _resolve_config(args: argparse.Namespace):
    ...


def _derive_seeds(seed: int | None) -> tuple[int, int, int, int]:
    ...


def _default_output_dir(config_name: str) -> Path:
    ...


def _cycle_payload(config, cycle):
    ...


def _print_guided_results(config, cycle, summary, sensitivity_report, scenario_report) -> None:
    ...


def main(argv: Sequence[str] | None=None) -> int:
    ...


if __name__ == '__main__':
    ...
