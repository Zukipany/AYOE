"""Project-wide constants."""

from __future__ import annotations

from typing import Final

STAGE_SEQUENCE: Final[tuple[str, ...]] = (
    "proton_beam_input",
    "antiproton_creation",
    "particle_selection",
    "ad_survival",
    "elena_survival",
    "trap_capture",
    "antihydrogen_formation",
    "final_usable_yield",
)

SURVIVAL_STAGES: Final[tuple[str, ...]] = (
    "particle_selection",
    "ad_survival",
    "elena_survival",
    "trap_capture",
    "antihydrogen_formation",
    "final_usable_yield",
)

OPERATIONAL_STAGES: Final[tuple[str, ...]] = SURVIVAL_STAGES

STAGE_LABELS: Final[dict[str, str]] = {
    "proton_beam_input": "Proton Beam Input",
    "antiproton_creation": "Antiproton Creation",
    "particle_selection": "Particle Selection",
    "ad_survival": "AD Survival",
    "elena_survival": "ELENA Survival",
    "trap_capture": "Trap Capture",
    "antihydrogen_formation": "Antihydrogen Formation",
    "final_usable_yield": "Final Usable Yield",
}

DEFAULT_PRESET: Final[str] = "baseline"
DEFAULT_MONTE_CARLO_RUNS: Final[int] = 500
DEFAULT_SENSITIVITY_RUNS: Final[int] = 200
DEFAULT_FULL_MONTE_CARLO_RUNS: Final[int] = 250
DEFAULT_FULL_SENSITIVITY_RUNS: Final[int] = 150
DEFAULT_SCENARIO_COMPARE_RUNS: Final[int] = 120
DEFAULT_HEATMAP_RUNS: Final[int] = 40
DEFAULT_NEAR_ZERO_THRESHOLD: Final[int] = 10
DEFAULT_EXPECTED_SHORTFALL_ALPHA: Final[float] = 0.10
DEFAULT_SENSITIVITY_DELTA: Final[float] = 0.10
DEFAULT_QUANTILES: Final[tuple[float, ...]] = (0.05, 0.25, 0.5, 0.75, 0.95)
DEFAULT_SCENARIO_SET: Final[tuple[str, ...]] = (
    "conservative",
    "baseline",
    "aggressive",
    "high-cooling",
    "high-trap",
    "high-positron",
    "low-volatility",
    "stress-test",
)

PHYSICS_BASELINES: Final[dict[str, float]] = {
    "pulse_length_ns": 18.0,
    "target_density": 1.0,
    "magnetic_field_t": 1.1,
    "vacuum_quality": 0.985,
    "trap_temperature_k": 0.55,
    "mixing_efficiency": 0.88,
    "positron_inventory_scale": 1.0,
}

STAGE_ENERGY_TARGETS_MEV: Final[dict[str, float]] = {
    "proton_beam_input": 26_000.0,
    "antiproton_creation": 3_500.0,
    "particle_selection": 150.0,
    "ad_survival": 5.3,
    "elena_survival": 0.1,
    "trap_capture": 0.005,
    "antihydrogen_formation": 0.0005,
    "final_usable_yield": 0.0001,
}

STAGE_DURATION_SECONDS: Final[dict[str, float]] = {
    "proton_beam_input": 4.0,
    "antiproton_creation": 7.0,
    "particle_selection": 10.0,
    "ad_survival": 90.0,
    "elena_survival": 28.0,
    "trap_capture": 18.0,
    "antihydrogen_formation": 24.0,
    "final_usable_yield": 8.0,
}

STAGE_COST_FACTORS: Final[dict[str, float]] = {
    "proton_beam_input": 8.0,
    "antiproton_creation": 16.0,
    "particle_selection": 7.5,
    "ad_survival": 12.0,
    "elena_survival": 10.0,
    "trap_capture": 14.0,
    "antihydrogen_formation": 16.0,
    "final_usable_yield": 5.0,
}
