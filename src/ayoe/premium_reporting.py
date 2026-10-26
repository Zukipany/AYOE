# Source code is private. This file shows only its classes and function signatures.

"""Guided reporting layer that explains existing engine outputs without changing them."""
from __future__ import annotations
import html
from pathlib import Path
import pandas as pd
from ayoe.analytics import compute_run_diagnostics
from ayoe.calibration import build_config_calibration_snapshot
from ayoe.models import CycleResult, MonteCarloSummary, ScenarioComparisonReport, SensitivityReport, SimulationConfig
from ayoe.presentation import PROJECT_TITLE
from ayoe.walkthrough import PIPELINE_WALKTHROUGH


def build_cycle_table(cycle: CycleResult) -> pd.DataFrame:
    ...


def build_monte_carlo_table(summary: MonteCarloSummary) -> pd.DataFrame:
    ...


def build_sensitivity_table(report: SensitivityReport, top_n: int=10) -> pd.DataFrame:
    ...


def build_scenario_table(report: ScenarioComparisonReport) -> pd.DataFrame:
    ...


def explain_single_run(cycle: CycleResult) -> str:
    ...


def explain_monte_carlo(summary: MonteCarloSummary) -> str:
    ...


def explain_sensitivity(report: SensitivityReport) -> str:
    ...


def explain_scenarios(report: ScenarioComparisonReport) -> str:
    ...


def explain_charts() -> str:
    ...


def build_markdown_report(config: SimulationConfig, cycle: CycleResult, summary: MonteCarloSummary, sensitivity_report: SensitivityReport, scenario_report: ScenarioComparisonReport, chart_manifest: dict[str, str]) -> str:
    ...


def build_html_report(config: SimulationConfig, cycle: CycleResult, summary: MonteCarloSummary, sensitivity_report: SensitivityReport, scenario_report: ScenarioComparisonReport, chart_manifest: dict[str, str]) -> str:
    ...


def write_guided_reports(config: SimulationConfig, cycle: CycleResult, summary: MonteCarloSummary, sensitivity_report: SensitivityReport, scenario_report: ScenarioComparisonReport, chart_manifest: dict[str, str], output_dir: str | Path) -> dict[str, str]:
    ...
