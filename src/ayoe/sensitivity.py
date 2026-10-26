# Source code is private. This file shows only its classes and function signatures.

"""Sensitivity analysis utilities."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np
from ayoe.constants import STAGE_SEQUENCE
from ayoe.engine import run_monte_carlo
from ayoe.models import SensitivityReport, SimulationConfig


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    path: str
    minimum: float
    maximum: float | None
    integer: bool
    group: str
PHYSICS_PARAMETER_SPECS: tuple[ParameterSpec, ...]


def run_sensitivity_analysis(config: SimulationConfig, *, runs: int, seed: int | None=None, delta: float | None=None) -> SensitivityReport:
    ...


def _parameter_specs(config: SimulationConfig) -> list[ParameterSpec]:
    ...


def _get_value(config: SimulationConfig, path: str) -> Any:
    ...


def _set_value(config: SimulationConfig, path: str, value: Any) -> None:
    ...


def _scale_value(value: Any, delta: float, direction: int, spec: ParameterSpec) -> Any:
    ...
