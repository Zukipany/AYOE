# Source code is private. This file shows only its classes and function signatures.

"""Config and preset loading."""
from __future__ import annotations
import tomllib
from importlib import resources
from pathlib import Path
from typing import Any
from ayoe.constants import DEFAULT_PRESET
from ayoe.models import BeamConfig, SimulationConfig, StageConfig


def list_presets() -> list[str]:
    ...


def load_preset(name: str=DEFAULT_PRESET) -> SimulationConfig:
    ...


def load_config(path: str | Path | None=None, preset: str | None=None) -> SimulationConfig:
    ...


def _build_config(data: dict[str, Any]) -> SimulationConfig:
    ...
