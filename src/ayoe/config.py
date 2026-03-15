"""Config and preset loading."""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path
from typing import Any

from ayoe.constants import DEFAULT_PRESET
from ayoe.models import BeamConfig, SimulationConfig, StageConfig


def list_presets() -> list[str]:
    preset_root = resources.files("ayoe.presets")
    return sorted(path.stem for path in preset_root.iterdir() if path.name.endswith(".toml"))


def load_preset(name: str = DEFAULT_PRESET) -> SimulationConfig:
    preset_root = resources.files("ayoe.presets")
    preset_path = preset_root.joinpath(f"{name}.toml")
    if not preset_path.is_file():
        available = ", ".join(list_presets())
        raise ValueError(f"unknown preset {name!r}. Available presets: {available}")
    with preset_path.open("rb") as handle:
        data = tomllib.load(handle)
    return _build_config(data)


def load_config(path: str | Path | None = None, preset: str | None = None) -> SimulationConfig:
    if path is not None and preset is not None:
        raise ValueError("choose either a config path or a preset, not both")
    if path is not None:
        config_path = Path(path)
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
        return _build_config(data)
    return load_preset(preset or DEFAULT_PRESET)


def _build_config(data: dict[str, Any]) -> SimulationConfig:
    beam_data = data.get("beam")
    if beam_data is None:
        raise ValueError("config is missing [beam] section")

    stages_data = data.get("stages")
    if stages_data is None:
        raise ValueError("config is missing [stages] section")

    beam = BeamConfig(**beam_data)
    stages = {
        name: StageConfig(name=name, **stage_data)
        for name, stage_data in stages_data.items()
    }

    return SimulationConfig(
        name=data.get("name", "custom"),
        description=data.get("description", ""),
        beam=beam,
        stages=stages,
        near_zero_threshold=data.get("near_zero_threshold", 10),
        expected_shortfall_alpha=data.get("expected_shortfall_alpha", 0.10),
        sensitivity_delta=data.get("sensitivity_delta", 0.10),
    )
