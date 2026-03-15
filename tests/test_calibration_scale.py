from __future__ import annotations

import math

import numpy as np

from ayoe.analytics import compute_bottlenecks
from ayoe.config import load_preset
from ayoe.constants import OPERATIONAL_STAGES
from ayoe.engine import run_monte_carlo
from ayoe.sensitivity import run_sensitivity_analysis


def _median_output(cycles, stage_name: str) -> float:
    index = [stage.stage_name for stage in cycles[0].stage_results].index(stage_name)
    return float(np.median([cycle.stage_results[index].output_count for cycle in cycles]))


def test_baseline_lands_on_published_orders_of_magnitude() -> None:
    # ALPHA: ~1e5 trapped antiprotons, ~2.5-3e4 antihydrogen formed, ~10-30 trapped per cycle.
    cycles, summary = run_monte_carlo(load_preset("baseline"), runs=300, seed=3)
    assert 1e4 <= _median_output(cycles, "trap_capture") <= 1e6
    assert 5e3 <= _median_output(cycles, "antihydrogen_formation") <= 2e5
    assert 5 <= summary.stats["median"] <= 100


def test_presets_are_ordered_by_operating_quality() -> None:
    medians = {
        name: run_monte_carlo(load_preset(name), runs=200, seed=11)[1].stats["median"]
        for name in ("conservative", "baseline", "aggressive")
    }
    assert medians["conservative"] < medians["baseline"] < medians["aggressive"]


def test_bottlenecks_rank_operational_stages_by_log_loss_share() -> None:
    cycles, summary = run_monte_carlo(load_preset("baseline"), runs=80, seed=5)
    rows = compute_bottlenecks(cycles)

    assert {row["stage_name"] for row in rows} <= set(OPERATIONAL_STAGES)
    assert "antiproton_creation" not in {row["stage_name"] for row in rows}
    shares = [row["log_loss_share"] for row in rows]
    assert shares == sorted(shares, reverse=True)
    assert math.isclose(sum(shares), 1.0, rel_tol=1e-9)
    assert rows[0]["stage_name"] == "final_usable_yield"
    assert summary.bottlenecks == rows


def test_sensitivity_covers_physics_inputs_with_signed_elasticity() -> None:
    report = run_sensitivity_analysis(load_preset("baseline"), runs=60, seed=8, delta=0.10)
    rows = {(row["parameter"], row["direction"]): row for row in report.perturbations}

    assert ("beam.magnetic_field_t", "up") in rows
    assert rows[("beam.magnetic_field_t", "up")]["group"] == "physics"
    assert rows[("beam.magnetic_field_t", "up")]["elasticity"] > 1.0
    # Colder traps capture more antiprotons, so heating the trap must cost yield.
    assert rows[("beam.trap_temperature_k", "up")]["relative_change"] < 0
    # Vacuum quality is capped at 1.0, so elasticity is measured on the change actually applied.
    vacuum_up = rows[("beam.vacuum_quality", "up")]
    assert vacuum_up["perturbed_value"] == 1.0
    assert vacuum_up["elasticity"] is not None
