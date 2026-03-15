"""Export helpers for JSON and CSV artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ayoe.analytics import compute_run_diagnostics
from ayoe.models import CycleResult, ScenarioComparisonReport, SensitivityReport


def _prepare_path(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = _prepare_path(path)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return output_path


def write_runs_csv(path: str | Path, cycles: list[CycleResult]) -> Path:
    output_path = _prepare_path(path)
    rows = []
    for cycle in cycles:
        row = cycle.to_run_row()
        diagnostics = compute_run_diagnostics(cycle)
        row.update(
            {
                "initial_proton_count": diagnostics.initial_proton_count,
                "final_yield_ratio": diagnostics.final_yield_ratio,
                "total_loss_ratio": diagnostics.total_loss_ratio,
                "expected_final_yield": diagnostics.expected_final_yield,
                "realized_vs_expected_yield": diagnostics.realized_vs_expected_yield,
                "largest_scale_loss_stage": diagnostics.largest_scale_loss_stage_name,
                "operational_bottleneck_stage": diagnostics.operational_bottleneck_stage_name,
                "biggest_proportional_drop_stage": diagnostics.biggest_proportional_drop_stage_name,
                "strongest_operational_stage": diagnostics.strongest_operational_stage_name,
                "highest_shock_stage": diagnostics.highest_shock_stage_name,
                "stability_score": diagnostics.stability_score,
                "pipeline_health_score": diagnostics.pipeline_health_score,
                "quality_rating": diagnostics.quality_rating,
            }
        )
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame.to_csv(output_path, index=False)
    return output_path


def write_stages_csv(path: str | Path, cycles: list[CycleResult]) -> Path:
    output_path = _prepare_path(path)
    rows = [
        row
        for cycle in cycles
        for row in [
            metric.to_row(run_id=cycle.run_id, seed=cycle.seed)
            for metric in compute_run_diagnostics(cycle).stage_metrics
        ]
    ]
    frame = pd.DataFrame(rows)
    frame.to_csv(output_path, index=False)
    return output_path


def write_sensitivity_csv(path: str | Path, report: SensitivityReport) -> Path:
    output_path = _prepare_path(path)
    frame = pd.DataFrame(report.perturbations)
    frame.to_csv(output_path, index=False)
    return output_path


def write_scenario_comparison_csv(path: str | Path, report: ScenarioComparisonReport) -> Path:
    output_path = _prepare_path(path)
    frame = pd.DataFrame([result.to_dict() for result in report.scenario_results])
    frame.to_csv(output_path, index=False)
    return output_path
