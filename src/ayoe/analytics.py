# Source code is private. This file shows only its classes and function signatures.

"""Run diagnostics and Monte Carlo analytics."""
from __future__ import annotations
import math
from collections import defaultdict
from typing import Any
import numpy as np
from scipy.stats import spearmanr
from ayoe.constants import DEFAULT_QUANTILES, OPERATIONAL_STAGES
from ayoe.models import CycleResult, MonteCarloSummary, RunDiagnostics, SimulationConfig, StageMetrics


def _clamp01(value: float) -> float:
    ...


def _alignment_score(actual: float, expected: float) -> float:
    ...


def _quality_band(score: float) -> str:
    ...


def compute_stage_metrics(cycle: CycleResult) -> list[StageMetrics]:
    ...


def compute_run_diagnostics(cycle: CycleResult) -> RunDiagnostics:
    ...


def summarize_cycles(config: SimulationConfig, cycles: list[CycleResult], seed: int | None=None) -> MonteCarloSummary:
    ...


def compute_summary_stats(final_yields: np.ndarray, *, near_zero_threshold: int, shortfall_alpha: float) -> dict[str, float | None]:
    ...


def compute_bottlenecks(cycles: list[CycleResult]) -> list[dict[str, Any]]:
    """Rank operational stages by their share of the pipeline's log-loss.

    Yield is a product of stage efficiencies, so a stage's contribution to the
    total shortfall is additive in log space: ``-ln(efficiency)``. Raw lost
    counts are kept for reference but are dominated by whichever stage handles
    the most particles, which is why the proton-to-antiproton conversion is
    excluded here and reported as the scale bottleneck instead.
    """
    ...


def compute_bottleneck_frequencies(cycles: list[CycleResult]) -> list[dict[str, Any]]:
    ...


def compute_stage_efficiency_correlations(cycles: list[CycleResult]) -> list[dict[str, Any]]:
    ...
