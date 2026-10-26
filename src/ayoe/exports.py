# Source code is private. This file shows only its classes and function signatures.

"""Export helpers for JSON and CSV artifacts."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pandas as pd
from ayoe.analytics import compute_run_diagnostics
from ayoe.models import CycleResult, ScenarioComparisonReport, SensitivityReport


def _prepare_path(path: str | Path) -> Path:
    ...


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    ...


def write_runs_csv(path: str | Path, cycles: list[CycleResult]) -> Path:
    ...


def write_stages_csv(path: str | Path, cycles: list[CycleResult]) -> Path:
    ...


def write_sensitivity_csv(path: str | Path, report: SensitivityReport) -> Path:
    ...


def write_scenario_comparison_csv(path: str | Path, report: ScenarioComparisonReport) -> Path:
    ...
