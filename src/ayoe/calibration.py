# Source code is private. This file shows only its classes and function signatures.

"""Calibration metadata, sourced assumptions, and latent run-state sampling."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any
import numpy as np
from ayoe.constants import STAGE_LABELS
from ayoe.models import BeamConfig, RunLatentState


@dataclass(frozen=True, slots=True)
class CalibrationSource:
    title: str
    url: str
    source_type: str
    note: str

    def to_dict(self) -> dict[str, str]:
        ...


@dataclass(frozen=True, slots=True)
class DistributionCalibration:
    family: str
    low: float
    high: float
    concentration: float

    def to_dict(self) -> dict[str, float | str]:
        ...


@dataclass(frozen=True, slots=True)
class ParameterCalibration:
    key: str
    label: str
    baseline: float
    units: str
    confidence: str
    source_classification: str
    rationale: str
    tunable: bool
    distribution: DistributionCalibration
    sources: tuple[CalibrationSource, ...]

    def to_dict(self) -> dict[str, Any]:
        ...
CALIBRATION_REGISTRY: dict[str, ParameterCalibration]
REGIME_LIBRARY: dict[str, dict[str, float | str]]
LATENT_CORRELATION = ...


def get_parameter_calibration(key: str) -> ParameterCalibration:
    ...


def calibration_snapshot() -> dict[str, dict[str, Any]]:
    ...


def stage_calibration_snapshot(stage_name: str, center: float) -> dict[str, Any]:
    ...


def build_config_calibration_snapshot(config) -> dict[str, Any]:
    ...


def scaled_calibration_bounds(calibration: ParameterCalibration, scenario_center: float) -> tuple[float, float]:
    ...


def sample_calibrated_probability(calibration: ParameterCalibration, scenario_center: float, rng: np.random.Generator) -> float:
    ...


def sample_lognormal_around_center(center: float, low: float, high: float, rng: np.random.Generator) -> float:
    ...


def _clamp_factor(value: float, lower: float=0.55, upper: float=1.45) -> float:
    ...


def _bounded_geometric_mean(values: list[float], lower: float=0.55, upper: float=1.45) -> float:
    ...


def sample_run_latent_state(rng: np.random.Generator) -> RunLatentState:
    ...


def sample_run_proton_count(beam: BeamConfig, latent_state: RunLatentState, rng: np.random.Generator) -> int:
    ...
