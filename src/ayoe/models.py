"""Dataclasses for configs and outputs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from ayoe.constants import (
    DEFAULT_EXPECTED_SHORTFALL_ALPHA,
    DEFAULT_NEAR_ZERO_THRESHOLD,
    DEFAULT_SENSITIVITY_DELTA,
    STAGE_LABELS,
    STAGE_SEQUENCE,
)


def _ensure_probability(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1, got {value!r}")


def _ensure_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value!r}")


@dataclass(slots=True)
class BeamConfig:
    proton_count: int
    pulse_length_ns: float = 18.0
    beam_stability: float = 0.985
    target_density: float = 1.0
    magnetic_field_t: float = 1.1
    vacuum_quality: float = 0.985
    trap_temperature_k: float = 0.55
    mixing_efficiency: float = 0.88
    positron_inventory_scale: float = 1.0
    beam_jitter_sigma: float = 0.015

    def __post_init__(self) -> None:
        if self.proton_count <= 0:
            raise ValueError("beam.proton_count must be a positive integer")
        _ensure_positive("beam.pulse_length_ns", self.pulse_length_ns)
        _ensure_probability("beam.beam_stability", self.beam_stability)
        _ensure_positive("beam.target_density", self.target_density)
        _ensure_positive("beam.magnetic_field_t", self.magnetic_field_t)
        _ensure_probability("beam.vacuum_quality", self.vacuum_quality)
        _ensure_positive("beam.trap_temperature_k", self.trap_temperature_k)
        _ensure_probability("beam.mixing_efficiency", self.mixing_efficiency)
        _ensure_positive("beam.positron_inventory_scale", self.positron_inventory_scale)
        if self.beam_jitter_sigma < 0:
            raise ValueError("beam.beam_jitter_sigma must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proton_count": int(self.proton_count),
            "pulse_length_ns": float(self.pulse_length_ns),
            "beam_stability": float(self.beam_stability),
            "target_density": float(self.target_density),
            "magnetic_field_t": float(self.magnetic_field_t),
            "vacuum_quality": float(self.vacuum_quality),
            "trap_temperature_k": float(self.trap_temperature_k),
            "mixing_efficiency": float(self.mixing_efficiency),
            "positron_inventory_scale": float(self.positron_inventory_scale),
            "beam_jitter_sigma": float(self.beam_jitter_sigma),
        }


@dataclass(slots=True)
class StageConfig:
    name: str
    nominal_efficiency: float
    control_multiplier: float = 1.0
    degradation: float = 0.0
    shock_sigma: float = 0.02
    min_effective_efficiency: float = 0.0
    max_effective_efficiency: float = 1.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("stage name cannot be empty")
        _ensure_probability(f"{self.name}.nominal_efficiency", self.nominal_efficiency)
        _ensure_positive(f"{self.name}.control_multiplier", self.control_multiplier)
        _ensure_probability(f"{self.name}.degradation", self.degradation)
        if self.shock_sigma < 0:
            raise ValueError(f"{self.name}.shock_sigma must be non-negative")
        _ensure_probability(
            f"{self.name}.min_effective_efficiency",
            self.min_effective_efficiency,
        )
        _ensure_probability(
            f"{self.name}.max_effective_efficiency",
            self.max_effective_efficiency,
        )
        if self.min_effective_efficiency > self.max_effective_efficiency:
            raise ValueError(
                f"{self.name}.min_effective_efficiency cannot exceed max_effective_efficiency"
            )

    @property
    def label(self) -> str:
        return STAGE_LABELS[self.name]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nominal_efficiency": float(self.nominal_efficiency),
            "control_multiplier": float(self.control_multiplier),
            "degradation": float(self.degradation),
            "shock_sigma": float(self.shock_sigma),
            "min_effective_efficiency": float(self.min_effective_efficiency),
            "max_effective_efficiency": float(self.max_effective_efficiency),
        }


@dataclass(slots=True)
class SimulationConfig:
    name: str
    description: str
    beam: BeamConfig
    stages: dict[str, StageConfig]
    near_zero_threshold: int = DEFAULT_NEAR_ZERO_THRESHOLD
    expected_shortfall_alpha: float = DEFAULT_EXPECTED_SHORTFALL_ALPHA
    sensitivity_delta: float = DEFAULT_SENSITIVITY_DELTA

    def __post_init__(self) -> None:
        missing = [stage for stage in STAGE_SEQUENCE if stage not in self.stages]
        if missing:
            raise ValueError(f"missing required stages: {', '.join(missing)}")

        extras = [stage for stage in self.stages if stage not in STAGE_SEQUENCE]
        if extras:
            raise ValueError(f"unknown stages: {', '.join(extras)}")

        if self.near_zero_threshold < 0:
            raise ValueError("near_zero_threshold must be non-negative")
        if not 0.0 < self.expected_shortfall_alpha < 1.0:
            raise ValueError("expected_shortfall_alpha must be between 0 and 1")
        if not 0.0 < self.sensitivity_delta < 1.0:
            raise ValueError("sensitivity_delta must be between 0 and 1")

    def copy(self) -> "SimulationConfig":
        return deepcopy(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "near_zero_threshold": int(self.near_zero_threshold),
            "expected_shortfall_alpha": float(self.expected_shortfall_alpha),
            "sensitivity_delta": float(self.sensitivity_delta),
            "beam": self.beam.to_dict(),
            "stages": {name: self.stages[name].to_dict() for name in STAGE_SEQUENCE if name in self.stages},
        }


@dataclass(slots=True)
class PipelineState:
    particle_count: int
    energy_mev: float
    energy_bucket: str
    beam_quality: float
    cooling_quality: float
    trap_readiness: float
    formation_readiness: float
    shock_severity: float
    cumulative_cost_units: float = 0.0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "particle_count": int(self.particle_count),
            "energy_mev": float(self.energy_mev),
            "energy_bucket": self.energy_bucket,
            "beam_quality": float(self.beam_quality),
            "cooling_quality": float(self.cooling_quality),
            "trap_readiness": float(self.trap_readiness),
            "formation_readiness": float(self.formation_readiness),
            "shock_severity": float(self.shock_severity),
            "cumulative_cost_units": float(self.cumulative_cost_units),
            "elapsed_seconds": float(self.elapsed_seconds),
        }


@dataclass(slots=True)
class StageResult:
    stage_name: str
    input_count: int
    output_count: int
    lost_count: int
    nominal_efficiency: float
    sampled_base_efficiency: float
    effective_efficiency: float
    control_multiplier: float
    degradation: float
    sampled_shock: float
    distribution: str
    physics_modifier: float
    latent_modifier: float
    input_state: dict[str, Any] | None = None
    output_state: dict[str, Any] | None = None
    stage_cost_units: float = 0.0
    stage_duration_seconds: float = 0.0

    @property
    def stage_label(self) -> str:
        return STAGE_LABELS[self.stage_name]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "stage_label": self.stage_label,
            "input_count": int(self.input_count),
            "output_count": int(self.output_count),
            "lost_count": int(self.lost_count),
            "nominal_efficiency": float(self.nominal_efficiency),
            "sampled_base_efficiency": float(self.sampled_base_efficiency),
            "effective_efficiency": float(self.effective_efficiency),
            "control_multiplier": float(self.control_multiplier),
            "degradation": float(self.degradation),
            "sampled_shock": float(self.sampled_shock),
            "physics_modifier": float(self.physics_modifier),
            "distribution": self.distribution,
            "latent_modifier": float(self.latent_modifier),
            "input_state": self.input_state,
            "output_state": self.output_state,
            "stage_cost_units": float(self.stage_cost_units),
            "stage_duration_seconds": float(self.stage_duration_seconds),
        }

    def to_row(self, run_id: int | None = None, seed: int | None = None) -> dict[str, Any]:
        row = self.to_dict()
        if run_id is not None:
            row["run_id"] = int(run_id)
        if seed is not None:
            row["seed"] = None if seed is None else int(seed)
        return row


@dataclass(slots=True)
class RunLatentState:
    regime_name: str
    beam_quality: float
    cooling_quality: float
    system_stability: float
    timing_precision: float
    shock_pressure: float
    trap_readiness: float
    formation_readiness: float
    regime_shock_scale: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime_name": self.regime_name,
            "beam_quality": float(self.beam_quality),
            "cooling_quality": float(self.cooling_quality),
            "system_stability": float(self.system_stability),
            "timing_precision": float(self.timing_precision),
            "shock_pressure": float(self.shock_pressure),
            "trap_readiness": float(self.trap_readiness),
            "formation_readiness": float(self.formation_readiness),
            "regime_shock_scale": float(self.regime_shock_scale),
        }


@dataclass(slots=True)
class StageMetrics:
    stage_name: str
    stage_label: str
    input_count: int
    output_count: int
    lost_count: int
    sampled_base_efficiency: float
    effective_efficiency: float
    realized_efficiency: float
    sampled_shock: float
    physics_modifier: float
    latent_modifier: float
    stage_loss_ratio: float
    loss_share_of_total_losses: float
    operational_loss_share: float | None
    estimated_final_yield_impact: float
    cumulative_survival_ratio: float
    cumulative_loss_ratio: float
    stage_cost_units: float = 0.0
    stage_duration_seconds: float = 0.0
    output_energy_mev: float = 0.0
    output_energy_bucket: str = ""
    shock_severity: float = 0.0
    cumulative_cost_units: float = 0.0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "stage_label": self.stage_label,
            "input_count": int(self.input_count),
            "output_count": int(self.output_count),
            "lost_count": int(self.lost_count),
            "sampled_base_efficiency": float(self.sampled_base_efficiency),
            "effective_efficiency": float(self.effective_efficiency),
            "realized_efficiency": float(self.realized_efficiency),
            "sampled_shock": float(self.sampled_shock),
            "physics_modifier": float(self.physics_modifier),
            "latent_modifier": float(self.latent_modifier),
            "stage_loss_ratio": float(self.stage_loss_ratio),
            "loss_share_of_total_losses": float(self.loss_share_of_total_losses),
            "operational_loss_share": (
                None if self.operational_loss_share is None else float(self.operational_loss_share)
            ),
            "estimated_final_yield_impact": float(self.estimated_final_yield_impact),
            "cumulative_survival_ratio": float(self.cumulative_survival_ratio),
            "cumulative_loss_ratio": float(self.cumulative_loss_ratio),
            "stage_cost_units": float(self.stage_cost_units),
            "stage_duration_seconds": float(self.stage_duration_seconds),
            "output_energy_mev": float(self.output_energy_mev),
            "output_energy_bucket": self.output_energy_bucket,
            "shock_severity": float(self.shock_severity),
            "cumulative_cost_units": float(self.cumulative_cost_units),
            "elapsed_seconds": float(self.elapsed_seconds),
        }

    def to_row(self, run_id: int | None = None, seed: int | None = None) -> dict[str, Any]:
        row = self.to_dict()
        if run_id is not None:
            row["run_id"] = int(run_id)
        if seed is not None:
            row["seed"] = None if seed is None else int(seed)
        return row


@dataclass(slots=True)
class RunDiagnostics:
    config_name: str
    run_id: int
    seed: int | None
    initial_proton_count: int
    final_yield: int
    expected_final_yield: float
    final_yield_ratio: float
    total_loss_ratio: float
    realized_vs_expected_yield: float | None
    largest_scale_loss_stage_name: str
    largest_scale_loss_stage_label: str
    operational_bottleneck_stage_name: str
    operational_bottleneck_stage_label: str
    biggest_proportional_drop_stage_name: str
    biggest_proportional_drop_stage_label: str
    strongest_operational_stage_name: str
    strongest_operational_stage_label: str
    highest_shock_stage_name: str
    highest_shock_stage_label: str
    stability_score: float
    pipeline_health_score: float
    quality_rating: str
    total_cycle_cost_units: float = 0.0
    cycle_duration_seconds: float = 0.0
    yield_per_cost_unit: float | None = None
    yield_per_hour: float | None = None
    mean_stage_shock_severity: float = 0.0
    regime_name: str | None = None
    stage_metrics: list[StageMetrics] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_name": self.config_name,
            "run_id": int(self.run_id),
            "seed": None if self.seed is None else int(self.seed),
            "initial_proton_count": int(self.initial_proton_count),
            "final_yield": int(self.final_yield),
            "expected_final_yield": float(self.expected_final_yield),
            "final_yield_ratio": float(self.final_yield_ratio),
            "total_loss_ratio": float(self.total_loss_ratio),
            "realized_vs_expected_yield": (
                None
                if self.realized_vs_expected_yield is None
                else float(self.realized_vs_expected_yield)
            ),
            "largest_scale_loss_stage_name": self.largest_scale_loss_stage_name,
            "largest_scale_loss_stage_label": self.largest_scale_loss_stage_label,
            "operational_bottleneck_stage_name": self.operational_bottleneck_stage_name,
            "operational_bottleneck_stage_label": self.operational_bottleneck_stage_label,
            "biggest_proportional_drop_stage_name": self.biggest_proportional_drop_stage_name,
            "biggest_proportional_drop_stage_label": self.biggest_proportional_drop_stage_label,
            "strongest_operational_stage_name": self.strongest_operational_stage_name,
            "strongest_operational_stage_label": self.strongest_operational_stage_label,
            "highest_shock_stage_name": self.highest_shock_stage_name,
            "highest_shock_stage_label": self.highest_shock_stage_label,
            "stability_score": float(self.stability_score),
            "pipeline_health_score": float(self.pipeline_health_score),
            "quality_rating": self.quality_rating,
            "total_cycle_cost_units": float(self.total_cycle_cost_units),
            "cycle_duration_seconds": float(self.cycle_duration_seconds),
            "yield_per_cost_unit": (
                None if self.yield_per_cost_unit is None else float(self.yield_per_cost_unit)
            ),
            "yield_per_hour": None if self.yield_per_hour is None else float(self.yield_per_hour),
            "mean_stage_shock_severity": float(self.mean_stage_shock_severity),
            "regime_name": self.regime_name,
            "stage_metrics": [metric.to_dict() for metric in self.stage_metrics],
        }


@dataclass(slots=True)
class CycleResult:
    run_id: int
    config_name: str
    seed: int | None
    initial_state: PipelineState | None = None
    latent_state: RunLatentState | None = None
    final_state: PipelineState | None = None
    stage_results: list[StageResult] = field(default_factory=list)

    @property
    def final_yield(self) -> int:
        return self.stage_results[-1].output_count if self.stage_results else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": int(self.run_id),
            "config_name": self.config_name,
            "seed": None if self.seed is None else int(self.seed),
            "final_yield": int(self.final_yield),
            "initial_state": None if self.initial_state is None else self.initial_state.to_dict(),
            "latent_state": None if self.latent_state is None else self.latent_state.to_dict(),
            "final_state": None if self.final_state is None else self.final_state.to_dict(),
            "stage_results": [stage.to_dict() for stage in self.stage_results],
        }

    def to_run_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "run_id": int(self.run_id),
            "config_name": self.config_name,
            "seed": None if self.seed is None else int(self.seed),
            "final_yield": int(self.final_yield),
        }
        if self.initial_state is not None:
            row["initial_energy_mev"] = float(self.initial_state.energy_mev)
        if self.latent_state is not None:
            row.update(
                {
                    "regime_name": self.latent_state.regime_name,
                    "beam_quality": float(self.latent_state.beam_quality),
                    "cooling_quality": float(self.latent_state.cooling_quality),
                    "system_stability": float(self.latent_state.system_stability),
                    "timing_precision": float(self.latent_state.timing_precision),
                    "shock_pressure": float(self.latent_state.shock_pressure),
                    "trap_readiness": float(self.latent_state.trap_readiness),
                    "formation_readiness": float(self.latent_state.formation_readiness),
                }
            )
        if self.final_state is not None:
            row.update(
                {
                    "final_energy_mev": float(self.final_state.energy_mev),
                    "final_energy_bucket": self.final_state.energy_bucket,
                    "total_cycle_cost_units": float(self.final_state.cumulative_cost_units),
                    "cycle_duration_seconds": float(self.final_state.elapsed_seconds),
                    "yield_per_cost_unit": (
                        float(self.final_yield / self.final_state.cumulative_cost_units)
                        if self.final_state.cumulative_cost_units > 0
                        else None
                    ),
                    "yield_per_hour": (
                        float(self.final_yield / (self.final_state.elapsed_seconds / 3600.0))
                        if self.final_state.elapsed_seconds > 0
                        else None
                    ),
                }
            )
        for stage in self.stage_results:
            row[f"{stage.stage_name}_output"] = int(stage.output_count)
            row[f"{stage.stage_name}_loss"] = int(stage.lost_count)
            row[f"{stage.stage_name}_efficiency"] = float(stage.effective_efficiency)
        return row

    def to_stage_rows(self) -> list[dict[str, Any]]:
        return [stage.to_row(run_id=self.run_id, seed=self.seed) for stage in self.stage_results]


@dataclass(slots=True)
class MonteCarloSummary:
    config_name: str
    run_count: int
    seed: int | None
    near_zero_threshold: int
    stats: dict[str, float | None]
    bottlenecks: list[dict[str, Any]]
    stage_efficiency_correlations: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_name": self.config_name,
            "run_count": int(self.run_count),
            "seed": None if self.seed is None else int(self.seed),
            "near_zero_threshold": int(self.near_zero_threshold),
            "stats": self.stats,
            "bottlenecks": self.bottlenecks,
            "stage_efficiency_correlations": self.stage_efficiency_correlations,
        }


@dataclass(slots=True)
class SensitivityReport:
    config_name: str
    runs: int
    seed: int | None
    delta: float
    base_summary: MonteCarloSummary
    perturbations: list[dict[str, Any]]
    stage_efficiency_correlations: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_name": self.config_name,
            "runs": int(self.runs),
            "seed": None if self.seed is None else int(self.seed),
            "delta": float(self.delta),
            "base_summary": self.base_summary.to_dict(),
            "perturbations": self.perturbations,
            "stage_efficiency_correlations": self.stage_efficiency_correlations,
        }


@dataclass(slots=True)
class ScenarioResult:
    scenario_name: str
    description: str
    run_count: int
    seed: int | None
    mean_yield: float
    median_yield: float
    std_yield: float
    probability_near_zero: float
    mean_cycle_cost_units: float
    mean_yield_per_cost_unit: float | None
    mean_yield_per_hour: float | None
    mean_stability_score: float
    risk_adjusted_score: float
    top_bottleneck_stage_name: str | None
    top_bottleneck_stage_label: str | None
    summary: MonteCarloSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "description": self.description,
            "run_count": int(self.run_count),
            "seed": None if self.seed is None else int(self.seed),
            "mean_yield": float(self.mean_yield),
            "median_yield": float(self.median_yield),
            "std_yield": float(self.std_yield),
            "probability_near_zero": float(self.probability_near_zero),
            "mean_cycle_cost_units": float(self.mean_cycle_cost_units),
            "mean_yield_per_cost_unit": (
                None if self.mean_yield_per_cost_unit is None else float(self.mean_yield_per_cost_unit)
            ),
            "mean_yield_per_hour": (
                None if self.mean_yield_per_hour is None else float(self.mean_yield_per_hour)
            ),
            "mean_stability_score": float(self.mean_stability_score),
            "risk_adjusted_score": float(self.risk_adjusted_score),
            "top_bottleneck_stage_name": self.top_bottleneck_stage_name,
            "top_bottleneck_stage_label": self.top_bottleneck_stage_label,
            "summary": self.summary.to_dict(),
        }


@dataclass(slots=True)
class ScenarioComparisonReport:
    run_count: int
    seed: int | None
    scenario_results: list[ScenarioResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_count": int(self.run_count),
            "seed": None if self.seed is None else int(self.seed),
            "scenario_results": [result.to_dict() for result in self.scenario_results],
            "ranking_by_mean_yield": [
                result.scenario_name
                for result in sorted(self.scenario_results, key=lambda row: row.mean_yield, reverse=True)
            ],
            "ranking_by_stability": [
                result.scenario_name
                for result in sorted(
                    self.scenario_results,
                    key=lambda row: row.mean_stability_score,
                    reverse=True,
                )
            ],
            "ranking_by_risk_adjusted_score": [
                result.scenario_name
                for result in sorted(
                    self.scenario_results,
                    key=lambda row: row.risk_adjusted_score,
                    reverse=True,
                )
            ],
        }
