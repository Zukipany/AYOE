# Source code is private. This file shows only its classes and function signatures.

"""Plotting and reporting helpers for research-style simulation artifacts."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from ayoe.analytics import compute_bottlenecks, compute_run_diagnostics, compute_stage_efficiency_correlations
from ayoe.constants import DEFAULT_HEATMAP_RUNS, STAGE_ENERGY_TARGETS_MEV
from ayoe.engine import run_monte_carlo
from ayoe.models import CycleResult, ScenarioComparisonReport, SensitivityReport, SimulationConfig


def _prepare_output_dir(path: str | Path) -> Path:
    ...


def _apply_plot_style() -> None:
    ...


def _format_count(value: float) -> str:
    ...


def _format_energy(mev: float) -> str:
    ...


def _parameter_label(path: str) -> str:
    ...


def _plt():
    ...


def plot_pipeline_stage_bars(cycle: CycleResult, path: str | Path) -> Path:
    ...


def plot_cumulative_survival_curve(cycle: CycleResult, path: str | Path) -> Path:
    ...


def plot_monte_carlo_histogram(cycles: list[CycleResult], path: str | Path) -> Path:
    ...


def plot_scenario_boxplot(scenario_cycles: dict[str, list[CycleResult]], path: str | Path) -> Path:
    ...


def plot_bottleneck_analysis(cycles: list[CycleResult], path: str | Path) -> Path:
    ...


def plot_sensitivity_ranking(report: SensitivityReport, path: str | Path, *, top_n: int=12) -> Path:
    ...


def build_parameter_heatmap(config: SimulationConfig, *, seed: int | None=None, runs: int=DEFAULT_HEATMAP_RUNS) -> tuple[np.ndarray, list[float], list[float]]:
    ...


def plot_parameter_heatmap(config: SimulationConfig, path: str | Path, *, seed: int | None=None, runs: int=DEFAULT_HEATMAP_RUNS) -> Path:
    ...


def plot_cost_vs_yield(report: ScenarioComparisonReport, path: str | Path) -> Path:
    ...


def write_full_report_artifacts(config: SimulationConfig, cycle: CycleResult, monte_carlo_cycles: list[CycleResult], sensitivity_report: SensitivityReport, scenario_report: ScenarioComparisonReport, scenario_cycles: dict[str, list[CycleResult]], output_dir: str | Path, *, seed: int | None=None) -> dict[str, str]:
    ...
