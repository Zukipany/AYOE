# Source code is private. This file shows only its classes and function signatures.

from __future__ import annotations
import math
import numpy as np
from ayoe.analytics import compute_bottlenecks
from ayoe.config import load_preset
from ayoe.constants import OPERATIONAL_STAGES
from ayoe.engine import run_monte_carlo
from ayoe.sensitivity import run_sensitivity_analysis


def _median_output(cycles, stage_name: str) -> float:
    ...


def test_baseline_lands_on_published_orders_of_magnitude() -> None:
    ...


def test_presets_are_ordered_by_operating_quality() -> None:
    ...


def test_bottlenecks_rank_operational_stages_by_log_loss_share() -> None:
    ...


def test_sensitivity_covers_physics_inputs_with_signed_elasticity() -> None:
    ...
