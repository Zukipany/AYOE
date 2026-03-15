from __future__ import annotations

from ayoe.scenarios import list_scenarios, load_scenario, run_scenario_comparison


def test_scenario_registry_contains_expected_modes() -> None:
    scenarios = set(list_scenarios())
    assert {
        "conservative",
        "baseline",
        "aggressive",
        "high-cooling",
        "high-trap",
        "high-positron",
        "low-volatility",
        "stress-test",
    }.issubset(scenarios)


def test_loading_custom_scenario_modifies_baseline_controls() -> None:
    scenario = load_scenario("high-positron")
    assert scenario.beam.positron_inventory_scale > 1.0
    assert scenario.name == "high-positron"
    assert scenario.stages["antihydrogen_formation"].nominal_efficiency > 0.18


def test_run_scenario_comparison_returns_ranked_results() -> None:
    report, cycles = run_scenario_comparison(["baseline", "high-cooling"], runs=4, seed=11)
    assert report.run_count == 4
    assert len(report.scenario_results) == 2
    assert set(cycles) == {"baseline", "high-cooling"}
