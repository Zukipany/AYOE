from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ayoe.cli import main


def test_run_command_writes_outputs(tmp_path, capsys) -> None:
    json_path = tmp_path / "run.json"
    csv_path = tmp_path / "stages.csv"

    exit_code = main(
        [
            "run",
            "--preset",
            "baseline",
            "--seed",
            "42",
            "--json-out",
            str(json_path),
            "--stage-csv",
            str(csv_path),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "final_yield" in captured.out
    assert json_path.exists()
    assert csv_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["config_name"] == "baseline"
    assert payload["latent_state"]["regime_name"] in {"favourable", "nominal", "stressed", "unstable"}
    assert "calibration_snapshot" in payload
    assert "trap_capture" in payload["calibration_snapshot"]["stages"]
    assert payload["diagnostics"]["operational_bottleneck_stage_name"] in {
        "particle_selection",
        "ad_survival",
        "elena_survival",
        "trap_capture",
        "antihydrogen_formation",
        "final_usable_yield",
    }
    stage_frame = pd.read_csv(csv_path)
    assert "cumulative_survival_ratio" in stage_frame.columns


def test_no_command_defaults_to_full_workflow(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    exit_code = main([])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "defaulting to the full beta workflow" in captured.out
    assert "final_yield" in captured.out
    assert "Run diagnostics" in captured.out
    outputs = list((tmp_path / "outputs").glob("baseline_*"))
    assert len(outputs) == 1
    output_dir = outputs[0]
    assert (output_dir / "cycle.json").exists()
    assert (output_dir / "monte_carlo_summary.json").exists()
    assert (output_dir / "sensitivity.json").exists()
    assert captured.err == ""


def test_monte_carlo_command_writes_csv_outputs(tmp_path, capsys) -> None:
    json_path = tmp_path / "summary.json"
    runs_csv = tmp_path / "runs.csv"
    stage_csv = tmp_path / "stages.csv"

    exit_code = main(
        [
            "monte-carlo",
            "--preset",
            "baseline",
            "--runs",
            "10",
            "--seed",
            "42",
            "--json-out",
            str(json_path),
            "--runs-csv",
            str(runs_csv),
            "--stage-csv",
            str(stage_csv),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Top bottlenecks" in captured.out
    assert json_path.exists()
    assert runs_csv.exists()
    assert stage_csv.exists()


def test_sensitivity_command_writes_outputs(tmp_path, capsys) -> None:
    json_path = tmp_path / "sensitivity.json"
    csv_path = tmp_path / "sensitivity.csv"

    exit_code = main(
        [
            "sensitivity",
            "--preset",
            "baseline",
            "--runs",
            "8",
            "--seed",
            "42",
            "--json-out",
            str(json_path),
            "--csv-out",
            str(csv_path),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Top parameter impacts" in captured.out
    assert json_path.exists()
    assert csv_path.exists()


def test_scenario_compare_command_writes_outputs(tmp_path, capsys) -> None:
    json_path = tmp_path / "scenarios.json"
    csv_path = tmp_path / "scenarios.csv"

    exit_code = main(
        [
            "scenario-compare",
            "--scenarios",
            "baseline",
            "high-cooling",
            "stress-test",
            "--runs",
            "6",
            "--seed",
            "42",
            "--json-out",
            str(json_path),
            "--csv-out",
            str(csv_path),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "AYOE scenario comparison" in captured.out
    assert json_path.exists()
    assert csv_path.exists()


def test_full_command_writes_all_artifacts(tmp_path, capsys) -> None:
    output_dir = tmp_path / "workflow"

    exit_code = main(
        [
            "full",
            "--preset",
            "baseline",
            "--seed",
            "42",
            "--monte-carlo-runs",
            "8",
            "--sensitivity-runs",
            "6",
            "--scenario-runs",
            "5",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "AYOE full workflow" in captured.out
    assert "Wrote workflow artifacts" in captured.out
    expected_files = {
        "cycle.json",
        "cycle_stages.csv",
        "monte_carlo_summary.json",
        "monte_carlo_runs.csv",
        "monte_carlo_stages.csv",
        "sensitivity.json",
        "sensitivity.csv",
        "scenario_comparison.json",
        "scenario_comparison.csv",
        "calibration.json",
        "chart_manifest.json",
    }
    assert expected_files.issubset({path.name for path in output_dir.iterdir() if path.is_file()})
    charts_dir = output_dir / "charts"
    assert charts_dir.exists()
    assert {
        "pipeline_stage_bar.png",
        "cumulative_survival_curve.png",
        "monte_carlo_histogram.png",
        "scenario_boxplot.png",
        "bottleneck_analysis.png",
        "sensitivity_ranking.png",
        "yield_heatmap.png",
        "cost_vs_yield_scatter.png",
    }.issubset({path.name for path in charts_dir.iterdir() if path.is_file()})


def test_run_command_prints_tiny_efficiencies_in_scientific_notation(capsys) -> None:
    assert main(["run", "--preset", "baseline", "--seed", "7"]) == 0
    output = capsys.readouterr().out
    creation_row = next(line for line in output.splitlines() if line.strip().startswith("Antiproton Creation"))
    assert "e-07" in creation_row or "e-06" in creation_row
    assert "0.000000" not in creation_row


def test_guided_subcommand_dispatches_to_guided_runner(tmp_path, capsys) -> None:
    output_dir = tmp_path / "guided"
    exit_code = main(
        [
            "guided",
            "--monte-carlo-runs",
            "4",
            "--sensitivity-runs",
            "3",
            "--scenario-runs",
            "3",
            "--scenarios",
            "baseline",
            "--seed",
            "1",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0
    assert "Pipeline Walkthrough" in capsys.readouterr().out
    assert (output_dir / "guided_report.html").exists()


def test_export_web_command_writes_dataset(tmp_path, capsys) -> None:
    target = tmp_path / "demo.js"
    exit_code = main(["export-web", "--output", str(target), "--runs", "10", "--sensitivity-runs", "10"])
    assert exit_code == 0
    assert target.read_text(encoding="utf-8").startswith("window.AYOE_DEMO = ")
    assert "Wrote static simulator dataset" in capsys.readouterr().out
