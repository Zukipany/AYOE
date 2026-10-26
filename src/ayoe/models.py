# Source code is private. This file shows only its classes and function signatures.

"""Dataclasses for configs and outputs."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from ayoe.constants import DEFAULT_EXPECTED_SHORTFALL_ALPHA, DEFAULT_NEAR_ZERO_THRESHOLD, DEFAULT_SENSITIVITY_DELTA, STAGE_LABELS, STAGE_SEQUENCE


def _ensure_probability(name: str, value: float) -> None:
    ...


def _ensure_positive(name: str, value: float) -> None:
    ...


@dataclass(slots=True)
class BeamConfig:
    proton_count: int
    pulse_length_ns: float
    beam_stability: float
    target_density: float
    magnetic_field_t: float
    vacuum_quality: float
    trap_temperature_k: float
    mixing_efficiency: float
    positron_inventory_scale: float
    beam_jitter_sigma: float

    def __post_init__(self) -> None:
        ...

    def to_dict(self) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class StageConfig:
    name: str
    nominal_efficiency: float
    control_multiplier: float
    degradation: float
    shock_sigma: float
    min_effective_efficiency: float
    max_effective_efficiency: float

    def __post_init__(self) -> None:
        ...

    @property
    def label(self) -> str:
        ...

    def to_dict(self) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class SimulationConfig:
    name: str
    description: str
    beam: BeamConfig
    stages: dict[str, StageConfig]
    near_zero_threshold: int
    expected_shortfall_alpha: float
    sensitivity_delta: float

    def __post_init__(self) -> None:
        ...

    def copy(self) -> 'SimulationConfig':
        ...

    def to_dict(self) -> dict[str, Any]:
        ...


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
    cumulative_cost_units: float
    elapsed_seconds: float

    def to_dict(self) -> dict[str, Any]:
        ...


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
    input_state: dict[str, Any] | None
    output_state: dict[str, Any] | None
    stage_cost_units: float
    stage_duration_seconds: float

    @property
    def stage_label(self) -> str:
        ...

    def to_dict(self) -> dict[str, Any]:
        ...

    def to_row(self, run_id: int | None=None, seed: int | None=None) -> dict[str, Any]:
        ...


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
        ...


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
    stage_cost_units: float
    stage_duration_seconds: float
    output_energy_mev: float
    output_energy_bucket: str
    shock_severity: float
    cumulative_cost_units: float
    elapsed_seconds: float

    def to_dict(self) -> dict[str, Any]:
        ...

    def to_row(self, run_id: int | None=None, seed: int | None=None) -> dict[str, Any]:
        ...


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
    total_cycle_cost_units: float
    cycle_duration_seconds: float
    yield_per_cost_unit: float | None
    yield_per_hour: float | None
    mean_stage_shock_severity: float
    regime_name: str | None
    stage_metrics: list[StageMetrics]

    def to_dict(self) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class CycleResult:
    run_id: int
    config_name: str
    seed: int | None
    initial_state: PipelineState | None
    latent_state: RunLatentState | None
    final_state: PipelineState | None
    stage_results: list[StageResult]

    @property
    def final_yield(self) -> int:
        ...

    def to_dict(self) -> dict[str, Any]:
        ...

    def to_run_row(self) -> dict[str, Any]:
        ...

    def to_stage_rows(self) -> list[dict[str, Any]]:
        ...


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
        ...


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
        ...


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
        ...


@dataclass(slots=True)
class ScenarioComparisonReport:
    run_count: int
    seed: int | None
    scenario_results: list[ScenarioResult]

    def to_dict(self) -> dict[str, Any]:
        ...
