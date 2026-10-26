# Source code is private. This file shows only its classes and function signatures.

from __future__ import annotations
from ayoe.analytics import compute_run_diagnostics
from ayoe.config import load_preset
from ayoe.engine import run_monte_carlo, simulate_cycle
from ayoe.sensitivity import run_sensitivity_analysis


def _dominant_trap_config():
    ...


def test_stage_efficiency_correlation_surfaces_dominant_stage() -> None:
    ...


def test_sensitivity_prioritizes_dominant_stage_nominal_efficiency() -> None:
    ...


def test_run_diagnostics_surface_operational_bottleneck() -> None:
    ...
