from __future__ import annotations

from ayoe.analytics import compute_run_diagnostics
from ayoe.config import load_preset
from ayoe.constants import STAGE_SEQUENCE, SURVIVAL_STAGES
from ayoe.engine import run_monte_carlo, simulate_cycle


def test_simulate_cycle_is_seed_deterministic() -> None:
    config = load_preset("baseline")
    first = simulate_cycle(config, seed=123, run_id=1)
    second = simulate_cycle(config, seed=123, run_id=1)
    assert first.to_dict() == second.to_dict()
    assert first.latent_state is not None
    assert first.initial_state is not None
    assert first.final_state is not None


def test_pipeline_stage_order_matches_constant() -> None:
    config = load_preset("baseline")
    cycle = simulate_cycle(config, seed=7, run_id=1)
    assert [stage.stage_name for stage in cycle.stage_results] == list(STAGE_SEQUENCE)


def test_survival_stages_never_exceed_input_and_counts_stay_non_negative() -> None:
    config = load_preset("baseline")
    cycle = simulate_cycle(config, seed=99, run_id=1)
    for stage in cycle.stage_results:
        assert stage.input_count >= 0
        assert stage.output_count >= 0
        assert stage.lost_count >= 0
        if stage.stage_name in SURVIVAL_STAGES:
            assert stage.output_count <= stage.input_count


def test_run_monte_carlo_returns_expected_run_count() -> None:
    config = load_preset("baseline")
    cycles, summary = run_monte_carlo(config, runs=12, seed=5)
    assert len(cycles) == 12
    assert summary.run_count == 12
    assert summary.stats["mean"] is not None


def test_run_diagnostics_include_cumulative_survival_and_scores() -> None:
    config = load_preset("baseline")
    cycle = simulate_cycle(config, seed=42, run_id=1)
    diagnostics = compute_run_diagnostics(cycle)

    assert diagnostics.initial_proton_count == cycle.stage_results[0].input_count
    assert diagnostics.stage_metrics[-1].cumulative_survival_ratio == diagnostics.final_yield_ratio
    assert diagnostics.operational_bottleneck_stage_name in SURVIVAL_STAGES
    assert 0.0 <= diagnostics.stability_score <= 100.0
    assert 0.0 <= diagnostics.pipeline_health_score <= 100.0
