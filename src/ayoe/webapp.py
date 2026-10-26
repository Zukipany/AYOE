# Source code is private. This file shows only its classes and function signatures.

"""Interactive visual simulator: JSON payloads, a tiny HTTP server, and static demo export.

The browser UI lives in ``ayoe/web``. When it is served by ``ayoe serve`` it calls the
real engine through ``/api/*``; when it is opened as plain static files (for example on
GitHub Pages, or straight from disk) it falls back to ``web/data/demo.js`` produced by
``ayoe export-web``. That file is a script rather than JSON so it also loads over file://.
"""
from __future__ import annotations
import json
import math
import threading
import time
import webbrowser
from collections import defaultdict
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any
import numpy as np
from ayoe.analytics import compute_bottlenecks, compute_run_diagnostics, compute_stage_efficiency_correlations
from ayoe.calibration import CALIBRATION_REGISTRY
from ayoe.constants import DEFAULT_SCENARIO_SET, STAGE_DURATION_SECONDS, STAGE_ENERGY_TARGETS_MEV, STAGE_LABELS, STAGE_SEQUENCE
from ayoe.engine import run_monte_carlo
from ayoe.models import CycleResult, SimulationConfig
from ayoe.scenarios import SCENARIO_DEFINITIONS, load_scenario, run_scenario_comparison
from ayoe.sensitivity import run_sensitivity_analysis
WEB_ROOT = ...
DEFAULT_DEMO_PATH = ...
MAX_RUNS = ...
MAX_SENSITIVITY_RUNS = ...
MAX_SCENARIO_RUNS = ...
TRACE_COUNT = ...
BEAM_CONTROLS: tuple[dict[str, Any], ...]
STAGE_MULTIPLIER_RANGE = ...
VOLATILITY_RANGE = ...


def _round(value: float | None, digits: int=6) -> float | None:
    ...


def build_config(base: str='baseline', overrides: dict[str, Any] | None=None) -> SimulationConfig:
    """Load a preset/scenario and apply UI overrides, clamping every value to a safe range."""
    ...


def _quantiles(values: np.ndarray) -> dict[str, float]:
    ...


def _cycle_counts(cycle: CycleResult) -> list[int]:
    ...


def _sample_cycle(cycle: CycleResult) -> dict[str, Any]:
    ...


def simulation_payload(config: SimulationConfig, *, runs: int, seed: int | None) -> dict[str, Any]:
    ...


def sensitivity_payload(config: SimulationConfig, *, runs: int, seed: int | None) -> dict[str, Any]:
    ...


def scenario_payload(*, runs: int, seed: int | None, names: list[str] | None=None) -> dict[str, Any]:
    ...


def meta_payload() -> dict[str, Any]:
    ...


def export_demo_dataset(path: str | Path, *, runs: int=400, sensitivity_runs: int=150, seed: int=42) -> Path:
    ...


class SimulatorRequestHandler(SimpleHTTPRequestHandler):
    """Serves the static UI plus a JSON API backed by the simulation engine."""
    server_version = ...

    def log_message(self, format: str, *args: Any) -> None:
        ...

    def end_headers(self) -> None:
        ...

    def do_GET(self) -> None:
        ...

    def do_POST(self) -> None:
        ...

    def _send_json(self, payload: Any, status: HTTPStatus=HTTPStatus.OK) -> None:
        ...


def create_server(host: str='127.0.0.1', port: int=8765) -> ThreadingHTTPServer:
    ...


def serve(host: str='127.0.0.1', port: int=8765, *, open_browser: bool=True) -> int:
    ...
