# Source code is private. This file shows only its classes and function signatures.

"""Project-wide constants."""
from __future__ import annotations
from typing import Final
STAGE_SEQUENCE: Final[tuple[str, ...]]
SURVIVAL_STAGES: Final[tuple[str, ...]]
OPERATIONAL_STAGES: Final[tuple[str, ...]]
STAGE_LABELS: Final[dict[str, str]]
DEFAULT_PRESET: Final[str]
DEFAULT_MONTE_CARLO_RUNS: Final[int]
DEFAULT_SENSITIVITY_RUNS: Final[int]
DEFAULT_FULL_MONTE_CARLO_RUNS: Final[int]
DEFAULT_FULL_SENSITIVITY_RUNS: Final[int]
DEFAULT_SCENARIO_COMPARE_RUNS: Final[int]
DEFAULT_HEATMAP_RUNS: Final[int]
DEFAULT_NEAR_ZERO_THRESHOLD: Final[int]
DEFAULT_EXPECTED_SHORTFALL_ALPHA: Final[float]
DEFAULT_SENSITIVITY_DELTA: Final[float]
DEFAULT_QUANTILES: Final[tuple[float, ...]]
DEFAULT_SCENARIO_SET: Final[tuple[str, ...]]
PHYSICS_BASELINES: Final[dict[str, float]]
STAGE_ENERGY_TARGETS_MEV: Final[dict[str, float]]
STAGE_DURATION_SECONDS: Final[dict[str, float]]
STAGE_COST_FACTORS: Final[dict[str, float]]
