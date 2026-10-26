# Source code is private. This file shows only its classes and function signatures.

from __future__ import annotations
import json
import re
import threading
import urllib.request
import pytest
from ayoe.constants import STAGE_SEQUENCE
from ayoe.webapp import WEB_ROOT, build_config, create_server, export_demo_dataset, scenario_payload, sensitivity_payload, simulation_payload


def test_build_config_clamps_overrides_to_safe_ranges() -> None:
    ...


def test_simulation_payload_describes_every_stage() -> None:
    ...


def test_sensitivity_and_scenario_payloads_are_serialisable() -> None:
    ...


def test_export_demo_dataset_writes_loadable_script(tmp_path) -> None:
    ...


def test_server_serves_ui_and_api() -> None:
    ...


def test_every_explain_bubble_has_an_explanation() -> None:
    ...
