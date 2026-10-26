# Source code is private. This file shows only its classes and function signatures.

"""Simulation engine and Monte Carlo execution."""
from __future__ import annotations
import numpy as np
from ayoe.analytics import summarize_cycles
from ayoe.calibration import sample_run_latent_state, sample_run_proton_count
from ayoe.constants import STAGE_SEQUENCE
from ayoe.models import CycleResult, MonteCarloSummary, SimulationConfig
from ayoe.stages import STAGE_SIMULATORS, build_initial_pipeline_state


def simulate_cycle(config: SimulationConfig, *, seed: int | None=None, rng: np.random.Generator | None=None, run_id: int=0) -> CycleResult:
    ...


def run_monte_carlo(config: SimulationConfig, runs: int, *, seed: int | None=None) -> tuple[list[CycleResult], MonteCarloSummary]:
    ...
