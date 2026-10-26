# Source code is private. This file shows only its classes and function signatures.

from __future__ import annotations
import textwrap
import pytest
from ayoe.config import load_config, load_preset, list_presets


def test_list_presets_contains_expected_values() -> None:
    ...


def test_load_builtin_preset() -> None:
    ...


def test_missing_stage_raises(tmp_path) -> None:
    ...


def test_invalid_probability_raises(tmp_path) -> None:
    ...
