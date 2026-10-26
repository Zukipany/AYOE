# Source code is private. This file shows only its classes and function signatures.

"""Scenario registry and multi-scenario comparison utilities."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from ayoe.analytics import compute_bottleneck_frequencies, compute_run_diagnostics
from ayoe.config import load_preset
from ayoe.constants import DEFAULT_SCENARIO_COMPARE_RUNS, DEFAULT_SCENARIO_SET
from ayoe.engine import run_monte_carlo
from ayoe.models import CycleResult, ScenarioComparisonReport, ScenarioResult, SimulationConfig


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    name: str
    description: str
    base_preset: str
SCENARIO_DEFINITIONS: dict[str, ScenarioDefinition]


def list_scenarios() -> list[str]:
    ...


def load_scenario(name: str) -> SimulationConfig:
    ...


def run_scenario_comparison(scenario_names: list[str] | None=None, *, runs: int=DEFAULT_SCENARIO_COMPARE_RUNS, seed: int | None=None) -> tuple[ScenarioComparisonReport, dict[str, list[CycleResult]]]:
    ...
