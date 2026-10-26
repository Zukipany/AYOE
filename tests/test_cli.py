# Source code is private. This file shows only its classes and function signatures.

from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from ayoe.cli import main


def test_run_command_writes_outputs(tmp_path, capsys) -> None:
    ...


def test_no_command_defaults_to_full_workflow(tmp_path, monkeypatch, capsys) -> None:
    ...


def test_monte_carlo_command_writes_csv_outputs(tmp_path, capsys) -> None:
    ...


def test_sensitivity_command_writes_outputs(tmp_path, capsys) -> None:
    ...


def test_scenario_compare_command_writes_outputs(tmp_path, capsys) -> None:
    ...


def test_full_command_writes_all_artifacts(tmp_path, capsys) -> None:
    ...


def test_run_command_prints_tiny_efficiencies_in_scientific_notation(capsys) -> None:
    ...


def test_guided_subcommand_dispatches_to_guided_runner(tmp_path, capsys) -> None:
    ...


def test_export_web_command_writes_dataset(tmp_path, capsys) -> None:
    ...
