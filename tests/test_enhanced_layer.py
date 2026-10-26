# Source code is private. This file shows only its classes and function signatures.

from __future__ import annotations
import pytest
from ayoe.enhanced_main import main
from ayoe.presentation import PROJECT_TITLE, build_welcome_text
from ayoe.walkthrough import PIPELINE_WALKTHROUGH


def test_welcome_text_mentions_project_and_antimatter() -> None:
    ...


def test_walkthrough_covers_all_pipeline_stages() -> None:
    ...


def test_enhanced_runner_writes_guided_artifacts(tmp_path, capsys) -> None:
    ...
