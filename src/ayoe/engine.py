"""Simulation engine and Monte Carlo execution."""

from __future__ import annotations

import numpy as np

from ayoe.analytics import summarize_cycles
from ayoe.calibration import sample_run_latent_state, sample_run_proton_count
from ayoe.constants import STAGE_SEQUENCE
from ayoe.models import CycleResult, MonteCarloSummary, SimulationConfig
from ayoe.stages import STAGE_SIMULATORS, build_initial_pipeline_state


def simulate_cycle(
    config: SimulationConfig,
    *,
    seed: int | None = None,
    rng: np.random.Generator | None = None,
    run_id: int = 0,
) -> CycleResult:
    generator = rng or np.random.default_rng(seed)
    stage_results = []
    latent_state = sample_run_latent_state(generator)
    initial_proton_count = sample_run_proton_count(config.beam, latent_state, generator)
    initial_state = build_initial_pipeline_state(config.beam, initial_proton_count, latent_state)
    current_state = initial_state

    for stage_name in STAGE_SEQUENCE:
        stage_config = config.stages[stage_name]
        stage_result, current_state = STAGE_SIMULATORS[stage_name](
            current_state,
            stage_config,
            config.beam,
            latent_state,
            generator,
        )
        stage_results.append(stage_result)

    return CycleResult(
        run_id=run_id,
        config_name=config.name,
        seed=seed,
        initial_state=initial_state,
        latent_state=latent_state,
        final_state=current_state,
        stage_results=stage_results,
    )


def run_monte_carlo(
    config: SimulationConfig,
    runs: int,
    *,
    seed: int | None = None,
) -> tuple[list[CycleResult], MonteCarloSummary]:
    if runs <= 0:
        raise ValueError("runs must be a positive integer")

    if seed is None:
        root_seed = np.random.SeedSequence()
    else:
        root_seed = np.random.SeedSequence(seed)

    child_sequences = root_seed.spawn(runs)
    run_seeds = [int(child.generate_state(1, dtype=np.uint64)[0]) for child in child_sequences]

    cycles = []
    for run_id, (child_sequence, run_seed) in enumerate(zip(child_sequences, run_seeds), start=1):
        generator = np.random.default_rng(child_sequence)
        cycles.append(simulate_cycle(config, seed=run_seed, rng=generator, run_id=run_id))

    summary = summarize_cycles(config, cycles, seed=seed)
    return cycles, summary
