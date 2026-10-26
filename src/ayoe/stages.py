# Source code is private. This file shows only its classes and function signatures.

"""Stage simulations and shared stochastic helpers."""
from __future__ import annotations
import math
import numpy as np
from ayoe.calibration import get_parameter_calibration, sample_calibrated_probability
from ayoe.constants import PHYSICS_BASELINES, STAGE_COST_FACTORS, STAGE_DURATION_SECONDS, STAGE_ENERGY_TARGETS_MEV, STAGE_LABELS
from ayoe.models import BeamConfig, PipelineState, RunLatentState, StageConfig, StageResult


def _clamp(value: float, lower: float, upper: float) -> float:
    ...


def _isclose(a: float, b: float) -> bool:
    ...


def _inverse_ratio(value: float, baseline: float) -> float:
    ...


def _bounded_geometric_mean(values: list[float], lower: float=0.5, upper: float=1.5) -> float:
    ...


def energy_bucket_for(energy_mev: float) -> str:
    ...


def build_initial_pipeline_state(beam: BeamConfig, proton_count: int, latent_state: RunLatentState | None) -> PipelineState:
    ...


def physics_modifier(stage_name: str, beam: BeamConfig) -> float:
    ...


def latent_modifier(stage_name: str, latent_state: RunLatentState | None) -> float:
    ...


def _sample_stage_base_efficiency(stage_name: str, stage: StageConfig, rng: np.random.Generator) -> float:
    ...


def _sample_effective_efficiency(stage_name: str, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator) -> tuple[float, float, float, float, float]:
    ...


def _compute_stage_duration_seconds(stage_name: str, input_state: PipelineState, latent_state: RunLatentState | None) -> float:
    ...


def _compute_stage_cost_units(stage_name: str, beam: BeamConfig, input_state: PipelineState, latent_state: RunLatentState | None) -> float:
    ...


def _update_quality(current: float, target: float, shock_severity: float, blending: float, *, lower: float=0.35, upper: float=1.6) -> float:
    ...


def _build_output_state(stage_name: str, input_state: PipelineState, output_count: int, beam: BeamConfig, latent_state: RunLatentState | None, effective_efficiency: float, shock: float, modifier: float, stage_cost_units: float, stage_duration_seconds: float) -> PipelineState:
    ...


def _build_stage_result(stage_name: str, input_state: PipelineState, output_state: PipelineState, stage: StageConfig, effective_efficiency: float, shock: float, modifier: float, sampled_base_efficiency: float, latent: float, distribution: str, stage_cost_units: float, stage_duration_seconds: float) -> StageResult:
    ...


def _simulate_stage(stage_name: str, input_state: PipelineState, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator, *, distribution: str) -> tuple[StageResult, PipelineState]:
    ...


def simulate_proton_beam_input(input_state: PipelineState, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator) -> tuple[StageResult, PipelineState]:
    ...


def simulate_antiproton_creation(input_state: PipelineState, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator) -> tuple[StageResult, PipelineState]:
    ...


def simulate_particle_selection(input_state: PipelineState, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator) -> tuple[StageResult, PipelineState]:
    ...


def simulate_ad_survival(input_state: PipelineState, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator) -> tuple[StageResult, PipelineState]:
    ...


def simulate_elena_survival(input_state: PipelineState, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator) -> tuple[StageResult, PipelineState]:
    ...


def simulate_trap_capture(input_state: PipelineState, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator) -> tuple[StageResult, PipelineState]:
    ...


def simulate_antihydrogen_formation(input_state: PipelineState, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator) -> tuple[StageResult, PipelineState]:
    ...


def simulate_final_usable_yield(input_state: PipelineState, stage: StageConfig, beam: BeamConfig, latent_state: RunLatentState | None, rng: np.random.Generator) -> tuple[StageResult, PipelineState]:
    ...
STAGE_SIMULATORS = ...
