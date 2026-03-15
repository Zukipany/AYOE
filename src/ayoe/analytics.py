"""Run diagnostics and Monte Carlo analytics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
from scipy.stats import spearmanr

from ayoe.constants import DEFAULT_QUANTILES, OPERATIONAL_STAGES
from ayoe.models import (
    CycleResult,
    MonteCarloSummary,
    RunDiagnostics,
    SimulationConfig,
    StageMetrics,
)


def _clamp01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _alignment_score(actual: float, expected: float) -> float:
    if expected <= 0:
        return 1.0 if actual <= 0 else 0.0
    return _clamp01(1.0 - (abs(actual - expected) / expected))


def _quality_band(score: float) -> str:
    if score >= 90.0:
        return "Elite"
    if score >= 80.0:
        return "Strong"
    if score >= 70.0:
        return "Stable"
    if score >= 55.0:
        return "Watchlist"
    return "Fragile"


def compute_stage_metrics(cycle: CycleResult) -> list[StageMetrics]:
    if not cycle.stage_results:
        return []

    initial_proton_count = (
        cycle.initial_state.particle_count if cycle.initial_state is not None else cycle.stage_results[0].input_count
    )
    total_losses = sum(stage.lost_count for stage in cycle.stage_results)
    operational_losses = sum(
        stage.lost_count for stage in cycle.stage_results if stage.stage_name in OPERATIONAL_STAGES
    )

    metrics = []
    for stage in cycle.stage_results:
        realized_efficiency = (stage.output_count / stage.input_count) if stage.input_count else 0.0
        cumulative_survival_ratio = (
            (stage.output_count / initial_proton_count) if initial_proton_count else 0.0
        )
        metrics.append(
            StageMetrics(
                stage_name=stage.stage_name,
                stage_label=stage.stage_label,
                input_count=stage.input_count,
                output_count=stage.output_count,
                lost_count=stage.lost_count,
                sampled_base_efficiency=stage.sampled_base_efficiency,
                effective_efficiency=stage.effective_efficiency,
                realized_efficiency=realized_efficiency,
                sampled_shock=stage.sampled_shock,
                physics_modifier=stage.physics_modifier,
                latent_modifier=stage.latent_modifier,
                stage_loss_ratio=((stage.lost_count / stage.input_count) if stage.input_count else 0.0),
                loss_share_of_total_losses=((stage.lost_count / total_losses) if total_losses else 0.0),
                operational_loss_share=(
                    (stage.lost_count / operational_losses)
                    if stage.stage_name in OPERATIONAL_STAGES and operational_losses
                    else None
                ),
                estimated_final_yield_impact=0.0,
                cumulative_survival_ratio=cumulative_survival_ratio,
                cumulative_loss_ratio=1.0 - cumulative_survival_ratio,
                stage_cost_units=float(stage.stage_cost_units),
                stage_duration_seconds=float(stage.stage_duration_seconds),
                output_energy_mev=float((stage.output_state or {}).get("energy_mev", 0.0)),
                output_energy_bucket=str((stage.output_state or {}).get("energy_bucket", "")),
                shock_severity=float((stage.output_state or {}).get("shock_severity", abs(stage.sampled_shock))),
                cumulative_cost_units=float((stage.output_state or {}).get("cumulative_cost_units", 0.0)),
                elapsed_seconds=float((stage.output_state or {}).get("elapsed_seconds", 0.0)),
            )
        )

    downstream_realized_multiplier = 1.0
    for metric in reversed(metrics):
        metric.estimated_final_yield_impact = metric.lost_count * downstream_realized_multiplier
        downstream_realized_multiplier *= metric.realized_efficiency

    return metrics


def compute_run_diagnostics(cycle: CycleResult) -> RunDiagnostics:
    stage_metrics = compute_stage_metrics(cycle)
    if not stage_metrics:
        raise ValueError("cannot compute diagnostics for a cycle with no stage results")

    initial_proton_count = stage_metrics[0].input_count
    final_yield = cycle.final_yield
    final_yield_ratio = (final_yield / initial_proton_count) if initial_proton_count else 0.0
    total_loss_ratio = 1.0 - final_yield_ratio
    total_cycle_cost_units = (
        cycle.final_state.cumulative_cost_units
        if cycle.final_state is not None
        else float(sum(stage.stage_cost_units for stage in cycle.stage_results))
    )
    cycle_duration_seconds = (
        cycle.final_state.elapsed_seconds
        if cycle.final_state is not None
        else float(sum(stage.stage_duration_seconds for stage in cycle.stage_results))
    )
    yield_per_cost_unit = (final_yield / total_cycle_cost_units) if total_cycle_cost_units > 0 else None
    yield_per_hour = (final_yield / (cycle_duration_seconds / 3600.0)) if cycle_duration_seconds > 0 else None
    expected_final_yield = float(
        initial_proton_count * np.prod([stage.effective_efficiency for stage in cycle.stage_results])
    )
    realized_vs_expected_yield = (
        (final_yield / expected_final_yield) if expected_final_yield > 0 else None
    )

    largest_scale_loss_stage = max(stage_metrics, key=lambda metric: metric.lost_count)
    operational_metrics = [
        metric for metric in stage_metrics if metric.stage_name in OPERATIONAL_STAGES
    ] or stage_metrics
    operational_bottleneck_stage = max(
        operational_metrics,
        key=lambda metric: (metric.estimated_final_yield_impact, metric.stage_loss_ratio),
    )
    biggest_proportional_drop_stage = max(
        operational_metrics,
        key=lambda metric: (metric.stage_loss_ratio, metric.lost_count),
    )
    strongest_operational_stage = max(
        operational_metrics,
        key=lambda metric: (metric.realized_efficiency, -metric.stage_loss_ratio),
    )
    highest_shock_stage = max(stage_metrics, key=lambda metric: abs(metric.sampled_shock))

    shock_calmness = _clamp01(
        1.0 - (float(np.mean([abs(metric.sampled_shock) for metric in stage_metrics])) / 0.15)
    )
    mean_stage_shock_severity = float(np.mean([metric.shock_severity for metric in stage_metrics]))
    latent_stability = (
        _clamp01(
            (
                (0.40 * cycle.latent_state.system_stability)
                + (0.25 * cycle.latent_state.cooling_quality)
                + (0.20 * cycle.latent_state.timing_precision)
                + (0.15 * (1.0 / max(cycle.latent_state.shock_pressure, 1e-9)))
            )
            / 1.05
        )
        if cycle.latent_state is not None
        else 0.5
    )
    operational_efficiencies = np.array(
        [metric.realized_efficiency for metric in operational_metrics],
        dtype=float,
    )
    mean_operational_efficiency = float(np.mean(operational_efficiencies))
    efficiency_consistency = _clamp01(
        1.0
        - (
            float(np.std(operational_efficiencies))
            / (mean_operational_efficiency + 1e-9)
        )
    )
    stability_score = 100.0 * (
        (0.42 * shock_calmness) + (0.33 * efficiency_consistency) + (0.25 * latent_stability)
    )

    execution_alignment = float(
        np.mean(
            [
                _alignment_score(metric.realized_efficiency, metric.effective_efficiency)
                for metric in stage_metrics
            ]
        )
    )
    yield_execution_score = (
        _alignment_score(float(final_yield), expected_final_yield)
        if expected_final_yield > 0
        else 0.0
    )
    bottleneck_balance = _clamp01(
        1.0 - max(metric.stage_loss_ratio for metric in operational_metrics)
    )
    pipeline_health_score = 100.0 * (
        (0.40 * yield_execution_score)
        + (0.30 * execution_alignment)
        + (0.20 * (stability_score / 100.0))
        + (0.10 * bottleneck_balance)
    )
    quality_rating = _quality_band(pipeline_health_score)

    return RunDiagnostics(
        config_name=cycle.config_name,
        run_id=cycle.run_id,
        seed=cycle.seed,
        initial_proton_count=initial_proton_count,
        final_yield=final_yield,
        expected_final_yield=expected_final_yield,
        final_yield_ratio=final_yield_ratio,
        total_loss_ratio=total_loss_ratio,
        realized_vs_expected_yield=realized_vs_expected_yield,
        largest_scale_loss_stage_name=largest_scale_loss_stage.stage_name,
        largest_scale_loss_stage_label=largest_scale_loss_stage.stage_label,
        operational_bottleneck_stage_name=operational_bottleneck_stage.stage_name,
        operational_bottleneck_stage_label=operational_bottleneck_stage.stage_label,
        biggest_proportional_drop_stage_name=biggest_proportional_drop_stage.stage_name,
        biggest_proportional_drop_stage_label=biggest_proportional_drop_stage.stage_label,
        strongest_operational_stage_name=strongest_operational_stage.stage_name,
        strongest_operational_stage_label=strongest_operational_stage.stage_label,
        highest_shock_stage_name=highest_shock_stage.stage_name,
        highest_shock_stage_label=highest_shock_stage.stage_label,
        stability_score=stability_score,
        pipeline_health_score=pipeline_health_score,
        quality_rating=quality_rating,
        total_cycle_cost_units=total_cycle_cost_units,
        cycle_duration_seconds=cycle_duration_seconds,
        yield_per_cost_unit=yield_per_cost_unit,
        yield_per_hour=yield_per_hour,
        mean_stage_shock_severity=mean_stage_shock_severity,
        regime_name=(cycle.latent_state.regime_name if cycle.latent_state is not None else None),
        stage_metrics=stage_metrics,
    )


def summarize_cycles(
    config: SimulationConfig,
    cycles: list[CycleResult],
    seed: int | None = None,
) -> MonteCarloSummary:
    final_yields = np.array([cycle.final_yield for cycle in cycles], dtype=float)
    stats = compute_summary_stats(
        final_yields,
        near_zero_threshold=config.near_zero_threshold,
        shortfall_alpha=config.expected_shortfall_alpha,
    )
    bottlenecks = compute_bottlenecks(cycles)
    correlations = compute_stage_efficiency_correlations(cycles)
    return MonteCarloSummary(
        config_name=config.name,
        run_count=len(cycles),
        seed=seed,
        near_zero_threshold=config.near_zero_threshold,
        stats=stats,
        bottlenecks=bottlenecks,
        stage_efficiency_correlations=correlations,
    )


def compute_summary_stats(
    final_yields: np.ndarray,
    *,
    near_zero_threshold: int,
    shortfall_alpha: float,
) -> dict[str, float | None]:
    if final_yields.size == 0:
        raise ValueError("cannot summarize an empty yield series")

    quantile_values = {
        f"q{int(quantile * 100):02d}": float(np.quantile(final_yields, quantile))
        for quantile in DEFAULT_QUANTILES
    }
    mean = float(np.mean(final_yields))
    std = float(np.std(final_yields, ddof=1)) if final_yields.size > 1 else 0.0
    coefficient_of_variation = (std / mean) if mean else None
    var_cutoff = float(np.quantile(final_yields, shortfall_alpha))
    tail = final_yields[final_yields <= var_cutoff]
    expected_shortfall = float(np.mean(tail)) if tail.size else float(var_cutoff)

    return {
        "mean": mean,
        "std": std,
        "median": float(np.median(final_yields)),
        "min": float(np.min(final_yields)),
        "max": float(np.max(final_yields)),
        "coefficient_of_variation": coefficient_of_variation,
        "probability_zero": float(np.mean(final_yields == 0)),
        "probability_near_zero": float(np.mean(final_yields <= near_zero_threshold)),
        f"expected_shortfall_{int(shortfall_alpha * 100):02d}": expected_shortfall,
        **quantile_values,
    }


def compute_bottlenecks(cycles: list[CycleResult]) -> list[dict[str, Any]]:
    loss_totals: dict[str, float] = defaultdict(float)
    efficiency_totals: dict[str, float] = defaultdict(float)
    labels: dict[str, str] = {}

    for cycle in cycles:
        for stage in cycle.stage_results:
            labels[stage.stage_name] = stage.stage_label
            loss_totals[stage.stage_name] += stage.lost_count
            efficiency_totals[stage.stage_name] += stage.effective_efficiency

    total_losses = sum(loss_totals.values()) or 1.0
    run_count = max(len(cycles), 1)
    rows = []
    for stage_name, total_loss in loss_totals.items():
        mean_loss = total_loss / run_count
        rows.append(
            {
                "stage_name": stage_name,
                "stage_label": labels[stage_name],
                "mean_lost_count": float(mean_loss),
                "loss_share": float(total_loss / total_losses),
                "mean_effective_efficiency": float(efficiency_totals[stage_name] / run_count),
            }
        )
    rows.sort(key=lambda row: row["loss_share"], reverse=True)
    return rows


def compute_bottleneck_frequencies(cycles: list[CycleResult]) -> list[dict[str, Any]]:
    if not cycles:
        return []

    counts: dict[str, int] = defaultdict(int)
    labels: dict[str, str] = {}
    for cycle in cycles:
        diagnostics = compute_run_diagnostics(cycle)
        counts[diagnostics.operational_bottleneck_stage_name] += 1
        labels[diagnostics.operational_bottleneck_stage_name] = diagnostics.operational_bottleneck_stage_label

    run_count = len(cycles)
    rows = [
        {
            "stage_name": stage_name,
            "stage_label": labels[stage_name],
            "count": count,
            "frequency": float(count / run_count),
        }
        for stage_name, count in counts.items()
    ]
    rows.sort(key=lambda row: row["count"], reverse=True)
    return rows


def compute_stage_efficiency_correlations(cycles: list[CycleResult]) -> list[dict[str, Any]]:
    if not cycles:
        return []

    final_yields = np.array([cycle.final_yield for cycle in cycles], dtype=float)
    rows: list[dict[str, Any]] = []

    for index in range(len(cycles[0].stage_results)):
        stage_name = cycles[0].stage_results[index].stage_name
        stage_label = cycles[0].stage_results[index].stage_label
        efficiencies = np.array(
            [cycle.stage_results[index].effective_efficiency for cycle in cycles],
            dtype=float,
        )
        if np.allclose(efficiencies, efficiencies[0]) or np.allclose(final_yields, final_yields[0]):
            coefficient = 0.0
            pvalue = None
        else:
            coefficient, pvalue = spearmanr(efficiencies, final_yields)
            if np.isnan(coefficient):
                coefficient = 0.0
            if np.isnan(pvalue):
                pvalue = None
        rows.append(
            {
                "stage_name": stage_name,
                "stage_label": stage_label,
                "spearman_correlation": float(coefficient),
                "p_value": None if pvalue is None else float(pvalue),
            }
        )

    rows.sort(key=lambda row: abs(row["spearman_correlation"]), reverse=True)
    return rows
