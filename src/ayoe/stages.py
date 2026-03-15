"""Stage simulations and shared stochastic helpers."""

from __future__ import annotations

import math

import numpy as np

from ayoe.calibration import get_parameter_calibration, sample_calibrated_probability
from ayoe.constants import (
    PHYSICS_BASELINES,
    STAGE_COST_FACTORS,
    STAGE_DURATION_SECONDS,
    STAGE_ENERGY_TARGETS_MEV,
    STAGE_LABELS,
)
from ayoe.models import BeamConfig, PipelineState, RunLatentState, StageConfig, StageResult


def _clamp(value: float, lower: float, upper: float) -> float:
    return float(np.clip(value, lower, upper))


def _inverse_ratio(value: float, baseline: float) -> float:
    return baseline / value if value > 0 else 0.0


def _bounded_geometric_mean(values: list[float], lower: float = 0.5, upper: float = 1.5) -> float:
    clipped = [_clamp(value, lower, upper) for value in values]
    product = math.prod(clipped)
    return product ** (1.0 / len(clipped))


def energy_bucket_for(energy_mev: float) -> str:
    if energy_mev >= 1_000.0:
        return "high-energy"
    if energy_mev >= 1.0:
        return "decelerated"
    if energy_mev >= 0.01:
        return "ultra-low-energy"
    return "trapped"


def build_initial_pipeline_state(
    beam: BeamConfig,
    proton_count: int,
    latent_state: RunLatentState | None,
) -> PipelineState:
    beam_quality = beam.beam_stability
    cooling_quality = 1.0
    trap_readiness = 1.0
    formation_readiness = 1.0
    shock_severity = 0.0

    if latent_state is not None:
        beam_quality = _bounded_geometric_mean([beam.beam_stability, latent_state.beam_quality], 0.6, 1.5)
        cooling_quality = latent_state.cooling_quality
        trap_readiness = latent_state.trap_readiness
        formation_readiness = latent_state.formation_readiness
        shock_severity = max(latent_state.shock_pressure - 1.0, 0.0)

    return PipelineState(
        particle_count=int(proton_count),
        energy_mev=float(STAGE_ENERGY_TARGETS_MEV["proton_beam_input"]),
        energy_bucket=energy_bucket_for(STAGE_ENERGY_TARGETS_MEV["proton_beam_input"]),
        beam_quality=float(beam_quality),
        cooling_quality=float(cooling_quality),
        trap_readiness=float(trap_readiness),
        formation_readiness=float(formation_readiness),
        shock_severity=float(shock_severity),
    )


def physics_modifier(stage_name: str, beam: BeamConfig) -> float:
    baselines = PHYSICS_BASELINES
    stage_factors: dict[str, list[float]] = {
        "proton_beam_input": [
            beam.beam_stability,
            beam.target_density / baselines["target_density"],
            _inverse_ratio(beam.pulse_length_ns, baselines["pulse_length_ns"]),
        ],
        "antiproton_creation": [
            beam.target_density / baselines["target_density"],
            beam.magnetic_field_t / baselines["magnetic_field_t"],
            _inverse_ratio(beam.pulse_length_ns, baselines["pulse_length_ns"]),
        ],
        "particle_selection": [
            beam.magnetic_field_t / baselines["magnetic_field_t"],
            beam.vacuum_quality / baselines["vacuum_quality"],
        ],
        "ad_survival": [
            beam.beam_stability,
            beam.vacuum_quality / baselines["vacuum_quality"],
        ],
        "elena_survival": [
            beam.vacuum_quality / baselines["vacuum_quality"],
            beam.magnetic_field_t / baselines["magnetic_field_t"],
        ],
        "trap_capture": [
            beam.magnetic_field_t / baselines["magnetic_field_t"],
            _inverse_ratio(beam.trap_temperature_k, baselines["trap_temperature_k"]),
        ],
        "antihydrogen_formation": [
            beam.mixing_efficiency / baselines["mixing_efficiency"],
            beam.positron_inventory_scale / baselines["positron_inventory_scale"],
            _inverse_ratio(beam.trap_temperature_k, baselines["trap_temperature_k"]),
        ],
        "final_usable_yield": [
            beam.vacuum_quality / baselines["vacuum_quality"],
            beam.mixing_efficiency / baselines["mixing_efficiency"],
            beam.positron_inventory_scale / baselines["positron_inventory_scale"],
        ],
    }
    return _bounded_geometric_mean(stage_factors[stage_name])


def latent_modifier(stage_name: str, latent_state: RunLatentState | None) -> float:
    if latent_state is None:
        return 1.0

    stage_factors: dict[str, list[float]] = {
        "proton_beam_input": [
            latent_state.beam_quality,
            latent_state.system_stability,
            latent_state.timing_precision,
        ],
        "antiproton_creation": [
            latent_state.beam_quality,
            latent_state.system_stability,
        ],
        "particle_selection": [
            latent_state.beam_quality,
            latent_state.timing_precision,
        ],
        "ad_survival": [
            latent_state.beam_quality,
            latent_state.system_stability,
            latent_state.cooling_quality,
        ],
        "elena_survival": [
            latent_state.cooling_quality,
            latent_state.system_stability,
            latent_state.timing_precision,
        ],
        "trap_capture": [
            latent_state.cooling_quality,
            latent_state.trap_readiness,
            latent_state.system_stability,
        ],
        "antihydrogen_formation": [
            latent_state.cooling_quality,
            latent_state.formation_readiness,
            latent_state.timing_precision,
        ],
        "final_usable_yield": [
            latent_state.formation_readiness,
            latent_state.system_stability,
            latent_state.timing_precision,
        ],
    }
    return _bounded_geometric_mean(stage_factors[stage_name], lower=0.6, upper=1.45)


def _sample_stage_base_efficiency(
    stage_name: str,
    stage: StageConfig,
    rng: np.random.Generator,
) -> float:
    if np.isclose(stage.min_effective_efficiency, stage.max_effective_efficiency):
        return float(stage.nominal_efficiency)

    calibration = get_parameter_calibration(f"stages.{stage_name}.nominal_efficiency")
    return sample_calibrated_probability(calibration, stage.nominal_efficiency, rng)


def _sample_effective_efficiency(
    stage_name: str,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
) -> tuple[float, float, float, float, float]:
    sampled_base_efficiency = _sample_stage_base_efficiency(stage_name, stage, rng)
    shock_sigma = stage.shock_sigma
    if latent_state is not None:
        shock_sigma *= latent_state.regime_shock_scale * latent_state.shock_pressure
    shock = float(rng.normal(0.0, shock_sigma))
    modifier = physics_modifier(stage_name, beam)
    latent = latent_modifier(stage_name, latent_state)
    raw = (
        sampled_base_efficiency
        * stage.control_multiplier
        * (1.0 - stage.degradation)
        * modifier
        * latent
        * (1.0 + shock)
    )
    effective = _clamp(raw, stage.min_effective_efficiency, stage.max_effective_efficiency)
    return effective, shock, modifier, sampled_base_efficiency, latent


def _compute_stage_duration_seconds(
    stage_name: str,
    input_state: PipelineState,
    latent_state: RunLatentState | None,
) -> float:
    base = STAGE_DURATION_SECONDS[stage_name]
    if latent_state is None:
        return base
    duration_modifier = _bounded_geometric_mean(
        [
            _inverse_ratio(max(input_state.beam_quality, 1e-6), 1.0),
            _inverse_ratio(max(input_state.cooling_quality, 1e-6), 1.0),
            latent_state.shock_pressure,
        ],
        lower=0.75,
        upper=1.45,
    )
    return float(base * duration_modifier)


def _compute_stage_cost_units(
    stage_name: str,
    beam: BeamConfig,
    input_state: PipelineState,
    latent_state: RunLatentState | None,
) -> float:
    baselines = PHYSICS_BASELINES
    scale = STAGE_COST_FACTORS[stage_name]
    stage_factors: dict[str, list[float]] = {
        "proton_beam_input": [
            beam.target_density / baselines["target_density"],
            beam.proton_count / 3.0e12,
        ],
        "antiproton_creation": [
            beam.proton_count / 3.0e12,
            beam.magnetic_field_t / baselines["magnetic_field_t"],
        ],
        "particle_selection": [
            beam.magnetic_field_t / baselines["magnetic_field_t"],
            beam.vacuum_quality / baselines["vacuum_quality"],
        ],
        "ad_survival": [
            _inverse_ratio(max(input_state.beam_quality, 1e-6), 1.0),
            beam.vacuum_quality / baselines["vacuum_quality"],
        ],
        "elena_survival": [
            _inverse_ratio(max(input_state.cooling_quality, 1e-6), 1.0),
            beam.magnetic_field_t / baselines["magnetic_field_t"],
        ],
        "trap_capture": [
            beam.magnetic_field_t / baselines["magnetic_field_t"],
            _inverse_ratio(beam.trap_temperature_k, baselines["trap_temperature_k"]),
            _inverse_ratio(max(input_state.trap_readiness, 1e-6), 1.0),
        ],
        "antihydrogen_formation": [
            beam.positron_inventory_scale / baselines["positron_inventory_scale"],
            beam.mixing_efficiency / baselines["mixing_efficiency"],
            _inverse_ratio(max(input_state.formation_readiness, 1e-6), 1.0),
        ],
        "final_usable_yield": [
            beam.vacuum_quality / baselines["vacuum_quality"],
            beam.mixing_efficiency / baselines["mixing_efficiency"],
        ],
    }
    multiplier = _bounded_geometric_mean(stage_factors[stage_name], lower=0.6, upper=1.8)
    if latent_state is not None:
        multiplier *= _bounded_geometric_mean(
            [latent_state.shock_pressure, _inverse_ratio(latent_state.system_stability, 1.0)],
            lower=0.7,
            upper=1.6,
        )
    return float(scale * multiplier)


def _update_quality(
    current: float,
    target: float,
    shock_severity: float,
    blending: float,
    *,
    lower: float = 0.35,
    upper: float = 1.6,
) -> float:
    blended = ((1.0 - blending) * current) + (blending * target)
    shocked = blended * (1.0 - (0.10 * shock_severity))
    return _clamp(shocked, lower, upper)


def _build_output_state(
    stage_name: str,
    input_state: PipelineState,
    output_count: int,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    effective_efficiency: float,
    shock: float,
    modifier: float,
    stage_cost_units: float,
    stage_duration_seconds: float,
) -> PipelineState:
    target_energy = STAGE_ENERGY_TARGETS_MEV[stage_name]
    shock_severity = abs(shock) * (latent_state.shock_pressure if latent_state is not None else 1.0)

    latent_beam = latent_state.beam_quality if latent_state is not None else input_state.beam_quality
    latent_cooling = latent_state.cooling_quality if latent_state is not None else input_state.cooling_quality
    latent_trap = latent_state.trap_readiness if latent_state is not None else input_state.trap_readiness
    latent_formation = (
        latent_state.formation_readiness if latent_state is not None else input_state.formation_readiness
    )

    beam_quality_target = _bounded_geometric_mean(
        [latent_beam, modifier, max(effective_efficiency, 1e-6)],
        lower=0.45,
        upper=1.55,
    )
    cooling_quality_target = _bounded_geometric_mean(
        [latent_cooling, input_state.cooling_quality, modifier],
        lower=0.45,
        upper=1.55,
    )
    if stage_name in {"ad_survival", "elena_survival"}:
        cooling_quality_target *= 1.04
    if stage_name in {"trap_capture", "antihydrogen_formation"}:
        cooling_quality_target *= _inverse_ratio(beam.trap_temperature_k, PHYSICS_BASELINES["trap_temperature_k"])

    beam_quality = _update_quality(input_state.beam_quality, beam_quality_target, shock_severity, 0.28)
    cooling_quality = _update_quality(input_state.cooling_quality, cooling_quality_target, shock_severity, 0.26)

    trap_target = _bounded_geometric_mean(
        [cooling_quality, latent_trap, beam.magnetic_field_t / PHYSICS_BASELINES["magnetic_field_t"]],
        lower=0.45,
        upper=1.6,
    )
    formation_target = _bounded_geometric_mean(
        [
            cooling_quality,
            latent_formation,
            beam.mixing_efficiency / PHYSICS_BASELINES["mixing_efficiency"],
            beam.positron_inventory_scale / PHYSICS_BASELINES["positron_inventory_scale"],
        ],
        lower=0.45,
        upper=1.7,
    )
    trap_readiness = _update_quality(input_state.trap_readiness, trap_target, shock_severity, 0.32)
    formation_readiness = _update_quality(
        input_state.formation_readiness,
        formation_target,
        shock_severity,
        0.34,
        upper=1.7,
    )

    return PipelineState(
        particle_count=int(output_count),
        energy_mev=float(target_energy),
        energy_bucket=energy_bucket_for(target_energy),
        beam_quality=float(beam_quality),
        cooling_quality=float(cooling_quality),
        trap_readiness=float(trap_readiness),
        formation_readiness=float(formation_readiness),
        shock_severity=float(shock_severity),
        cumulative_cost_units=float(input_state.cumulative_cost_units + stage_cost_units),
        elapsed_seconds=float(input_state.elapsed_seconds + stage_duration_seconds),
    )


def _build_stage_result(
    stage_name: str,
    input_state: PipelineState,
    output_state: PipelineState,
    stage: StageConfig,
    effective_efficiency: float,
    shock: float,
    modifier: float,
    sampled_base_efficiency: float,
    latent: float,
    distribution: str,
    stage_cost_units: float,
    stage_duration_seconds: float,
) -> StageResult:
    lost_count = max(int(input_state.particle_count) - int(output_state.particle_count), 0)
    return StageResult(
        stage_name=stage_name,
        input_count=int(input_state.particle_count),
        output_count=int(output_state.particle_count),
        lost_count=lost_count,
        nominal_efficiency=float(stage.nominal_efficiency),
        sampled_base_efficiency=float(sampled_base_efficiency),
        effective_efficiency=float(effective_efficiency),
        control_multiplier=float(stage.control_multiplier),
        degradation=float(stage.degradation),
        sampled_shock=float(shock),
        distribution=distribution,
        physics_modifier=float(modifier),
        latent_modifier=float(latent),
        input_state=input_state.to_dict(),
        output_state=output_state.to_dict(),
        stage_cost_units=float(stage_cost_units),
        stage_duration_seconds=float(stage_duration_seconds),
    )


def _simulate_stage(
    stage_name: str,
    input_state: PipelineState,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
    *,
    distribution: str,
) -> tuple[StageResult, PipelineState]:
    effective_efficiency, shock, modifier, sampled_base_efficiency, latent = _sample_effective_efficiency(
        stage_name,
        stage,
        beam,
        latent_state,
        rng,
    )
    if distribution == "poisson":
        lam = max(float(input_state.particle_count) * effective_efficiency, 0.0)
        output_count = int(rng.poisson(lam))
    else:
        output_count = int(rng.binomial(input_state.particle_count, effective_efficiency))

    stage_duration_seconds = _compute_stage_duration_seconds(stage_name, input_state, latent_state)
    stage_cost_units = _compute_stage_cost_units(stage_name, beam, input_state, latent_state)
    output_state = _build_output_state(
        stage_name,
        input_state,
        output_count,
        beam,
        latent_state,
        effective_efficiency,
        shock,
        modifier,
        stage_cost_units,
        stage_duration_seconds,
    )
    return (
        _build_stage_result(
            stage_name,
            input_state,
            output_state,
            stage,
            effective_efficiency,
            shock,
            modifier,
            sampled_base_efficiency,
            latent,
            distribution,
            stage_cost_units,
            stage_duration_seconds,
        ),
        output_state,
    )


def simulate_proton_beam_input(
    input_state: PipelineState,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
) -> tuple[StageResult, PipelineState]:
    return _simulate_stage(
        "proton_beam_input",
        input_state,
        stage,
        beam,
        latent_state,
        rng,
        distribution="binomial",
    )


def simulate_antiproton_creation(
    input_state: PipelineState,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
) -> tuple[StageResult, PipelineState]:
    return _simulate_stage(
        "antiproton_creation",
        input_state,
        stage,
        beam,
        latent_state,
        rng,
        distribution="poisson",
    )


def simulate_particle_selection(
    input_state: PipelineState,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
) -> tuple[StageResult, PipelineState]:
    return _simulate_stage(
        "particle_selection",
        input_state,
        stage,
        beam,
        latent_state,
        rng,
        distribution="binomial",
    )


def simulate_ad_survival(
    input_state: PipelineState,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
) -> tuple[StageResult, PipelineState]:
    return _simulate_stage(
        "ad_survival",
        input_state,
        stage,
        beam,
        latent_state,
        rng,
        distribution="binomial",
    )


def simulate_elena_survival(
    input_state: PipelineState,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
) -> tuple[StageResult, PipelineState]:
    return _simulate_stage(
        "elena_survival",
        input_state,
        stage,
        beam,
        latent_state,
        rng,
        distribution="binomial",
    )


def simulate_trap_capture(
    input_state: PipelineState,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
) -> tuple[StageResult, PipelineState]:
    return _simulate_stage(
        "trap_capture",
        input_state,
        stage,
        beam,
        latent_state,
        rng,
        distribution="binomial",
    )


def simulate_antihydrogen_formation(
    input_state: PipelineState,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
) -> tuple[StageResult, PipelineState]:
    return _simulate_stage(
        "antihydrogen_formation",
        input_state,
        stage,
        beam,
        latent_state,
        rng,
        distribution="binomial",
    )


def simulate_final_usable_yield(
    input_state: PipelineState,
    stage: StageConfig,
    beam: BeamConfig,
    latent_state: RunLatentState | None,
    rng: np.random.Generator,
) -> tuple[StageResult, PipelineState]:
    return _simulate_stage(
        "final_usable_yield",
        input_state,
        stage,
        beam,
        latent_state,
        rng,
        distribution="binomial",
    )


STAGE_SIMULATORS = {
    "proton_beam_input": simulate_proton_beam_input,
    "antiproton_creation": simulate_antiproton_creation,
    "particle_selection": simulate_particle_selection,
    "ad_survival": simulate_ad_survival,
    "elena_survival": simulate_elena_survival,
    "trap_capture": simulate_trap_capture,
    "antihydrogen_formation": simulate_antihydrogen_formation,
    "final_usable_yield": simulate_final_usable_yield,
}

assert all(stage in STAGE_LABELS for stage in STAGE_SIMULATORS)
