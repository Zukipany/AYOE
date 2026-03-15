"""Sensitivity analysis utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ayoe.constants import STAGE_SEQUENCE
from ayoe.engine import run_monte_carlo
from ayoe.models import SensitivityReport, SimulationConfig


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    path: str
    minimum: float
    maximum: float | None = None
    integer: bool = False
    group: str = "stage"


PHYSICS_PARAMETER_SPECS: tuple[ParameterSpec, ...] = (
    ParameterSpec("beam.beam_stability", minimum=0.0, maximum=1.0, group="physics"),
    ParameterSpec("beam.target_density", minimum=1e-6, group="physics"),
    ParameterSpec("beam.pulse_length_ns", minimum=1e-6, group="physics"),
    ParameterSpec("beam.magnetic_field_t", minimum=1e-6, group="physics"),
    ParameterSpec("beam.vacuum_quality", minimum=0.0, maximum=1.0, group="physics"),
    ParameterSpec("beam.trap_temperature_k", minimum=1e-6, group="physics"),
    ParameterSpec("beam.mixing_efficiency", minimum=0.0, maximum=1.0, group="physics"),
    ParameterSpec("beam.positron_inventory_scale", minimum=1e-6, group="physics"),
)


def run_sensitivity_analysis(
    config: SimulationConfig,
    *,
    runs: int,
    seed: int | None = None,
    delta: float | None = None,
) -> SensitivityReport:
    perturbation = delta if delta is not None else config.sensitivity_delta
    if not 0.0 < perturbation < 1.0:
        raise ValueError("delta must be between 0 and 1")

    # Reuse the same Monte Carlo seed across perturbations so common random
    # numbers reduce sampling noise and keep comparisons parameter-driven.
    base_seed = (
        int(np.random.SeedSequence().generate_state(1, dtype=np.uint64)[0])
        if seed is None
        else seed
    )
    _, base_summary = run_monte_carlo(config, runs=runs, seed=base_seed)
    base_mean = float(base_summary.stats["mean"] or 0.0)

    perturbations = []
    specs = _parameter_specs(config)
    for spec in specs:
        for direction in (-1, 1):
            scenario_config = config.copy()
            base_value = _get_value(scenario_config, spec.path)
            perturbed_value = _scale_value(base_value, perturbation, direction, spec)
            _set_value(scenario_config, spec.path, perturbed_value)
            _, summary = run_monte_carlo(scenario_config, runs=runs, seed=base_seed)
            mean_yield = float(summary.stats["mean"] or 0.0)
            delta_yield = mean_yield - base_mean
            relative_change = (delta_yield / base_mean) if base_mean else None
            # Bounded parameters (e.g. vacuum quality) can move less than the
            # requested delta, so elasticity uses the change actually applied.
            parameter_change = (float(perturbed_value) - float(base_value)) / float(base_value)
            elasticity = (
                relative_change / parameter_change
                if relative_change is not None and parameter_change
                else None
            )
            perturbations.append(
                {
                    "parameter": spec.path,
                    "group": spec.group,
                    "direction": "down" if direction < 0 else "up",
                    "base_value": base_value,
                    "perturbed_value": perturbed_value,
                    "mean_yield": mean_yield,
                    "delta_mean_yield": delta_yield,
                    "relative_change": relative_change,
                    "elasticity": elasticity,
                    "scenario_seed": base_seed,
                }
            )

    perturbations.sort(
        key=lambda row: abs(row["relative_change"]) if row["relative_change"] is not None else 0.0,
        reverse=True,
    )

    return SensitivityReport(
        config_name=config.name,
        runs=runs,
        seed=base_seed,
        delta=perturbation,
        base_summary=base_summary,
        perturbations=perturbations,
        stage_efficiency_correlations=base_summary.stage_efficiency_correlations,
    )


def _parameter_specs(config: SimulationConfig) -> list[ParameterSpec]:
    specs = [ParameterSpec("beam.proton_count", minimum=1, integer=True, group="beam")]
    specs.extend(PHYSICS_PARAMETER_SPECS)
    specs.extend(
        ParameterSpec(f"stages.{stage_name}.nominal_efficiency", minimum=0.0, maximum=1.0)
        for stage_name in STAGE_SEQUENCE
    )
    return specs


def _get_value(config: SimulationConfig, path: str) -> Any:
    current: Any = config
    for part in path.split("."):
        if isinstance(current, dict):
            current = current[part]
        else:
            current = getattr(current, part)
    return current


def _set_value(config: SimulationConfig, path: str, value: Any) -> None:
    parts = path.split(".")
    current: Any = config
    for part in parts[:-1]:
        if isinstance(current, dict):
            current = current[part]
        else:
            current = getattr(current, part)
    final_part = parts[-1]
    if isinstance(current, dict):
        current[final_part] = value
    else:
        setattr(current, final_part, value)


def _scale_value(value: Any, delta: float, direction: int, spec: ParameterSpec) -> Any:
    scaled = float(value) * (1.0 + (delta * direction))
    if spec.maximum is not None:
        scaled = min(scaled, spec.maximum)
    scaled = max(scaled, spec.minimum)
    if spec.integer:
        return max(int(round(scaled)), int(spec.minimum))
    return scaled
