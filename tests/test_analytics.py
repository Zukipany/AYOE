from __future__ import annotations

from ayoe.analytics import compute_run_diagnostics
from ayoe.config import load_preset
from ayoe.engine import run_monte_carlo, simulate_cycle
from ayoe.sensitivity import run_sensitivity_analysis


def _dominant_trap_config():
    config = load_preset("baseline")
    config.beam.proton_count = 10_000_000
    config.beam.beam_jitter_sigma = 0.0
    for stage in config.stages.values():
        stage.shock_sigma = 0.0
        stage.control_multiplier = 1.0
        stage.degradation = 0.0
    fixed_values = {
        "proton_beam_input": 0.99,
        "antiproton_creation": 0.02,
        "particle_selection": 0.95,
        "ad_survival": 0.95,
        "elena_survival": 0.95,
        "antihydrogen_formation": 0.95,
        "final_usable_yield": 0.95,
    }
    for stage_name, value in fixed_values.items():
        stage = config.stages[stage_name]
        stage.nominal_efficiency = value
        stage.min_effective_efficiency = value
        stage.max_effective_efficiency = value
    config.stages["trap_capture"].nominal_efficiency = 0.15
    config.stages["trap_capture"].min_effective_efficiency = 0.05
    config.stages["trap_capture"].max_effective_efficiency = 0.40
    config.stages["trap_capture"].shock_sigma = 0.35
    return config


def test_stage_efficiency_correlation_surfaces_dominant_stage() -> None:
    config = _dominant_trap_config()
    _, summary = run_monte_carlo(config, runs=60, seed=123)
    assert summary.stage_efficiency_correlations[0]["stage_name"] == "trap_capture"


def test_sensitivity_prioritizes_dominant_stage_nominal_efficiency() -> None:
    config = _dominant_trap_config()
    report = run_sensitivity_analysis(config, runs=25, seed=17, delta=0.10)
    stage_rows = [
        row for row in report.perturbations if row["parameter"].startswith("stages.")
    ]
    assert stage_rows[0]["parameter"] == "stages.trap_capture.nominal_efficiency"


def test_run_diagnostics_surface_operational_bottleneck() -> None:
    config = _dominant_trap_config()
    cycle = simulate_cycle(config, seed=123, run_id=1)
    diagnostics = compute_run_diagnostics(cycle)

    assert diagnostics.operational_bottleneck_stage_name == "trap_capture"
    assert diagnostics.highest_shock_stage_name == "trap_capture"
    assert diagnostics.stage_metrics[-1].cumulative_survival_ratio == diagnostics.final_yield_ratio
