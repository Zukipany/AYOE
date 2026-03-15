from __future__ import annotations

import textwrap

import pytest

from ayoe.config import load_config, load_preset, list_presets


def test_list_presets_contains_expected_values() -> None:
    presets = list_presets()
    assert {"baseline", "conservative", "aggressive"}.issubset(set(presets))


def test_load_builtin_preset() -> None:
    config = load_preset("baseline")
    assert config.name == "baseline"
    assert config.beam.proton_count > 0
    assert "trap_capture" in config.stages


def test_missing_stage_raises(tmp_path) -> None:
    config_path = tmp_path / "invalid.toml"
    config_path.write_text(
        textwrap.dedent(
            """
            name = "invalid"

            [beam]
            proton_count = 1000

            [stages.proton_beam_input]
            nominal_efficiency = 0.99
            """
        ).strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required stages"):
        load_config(path=config_path)


def test_invalid_probability_raises(tmp_path) -> None:
    config_path = tmp_path / "invalid.toml"
    config_path.write_text(
        textwrap.dedent(
            """
            name = "invalid"

            [beam]
            proton_count = 1000
            beam_stability = 1.2

            [stages.proton_beam_input]
            nominal_efficiency = 0.99

            [stages.antiproton_creation]
            nominal_efficiency = 0.0001

            [stages.particle_selection]
            nominal_efficiency = 0.5

            [stages.ad_survival]
            nominal_efficiency = 0.5

            [stages.elena_survival]
            nominal_efficiency = 0.5

            [stages.trap_capture]
            nominal_efficiency = 0.5

            [stages.antihydrogen_formation]
            nominal_efficiency = 0.5

            [stages.final_usable_yield]
            nominal_efficiency = 0.5
            """
        ).strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="beam.beam_stability"):
        load_config(path=config_path)
