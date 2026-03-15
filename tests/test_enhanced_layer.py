from __future__ import annotations

import pytest

from ayoe.enhanced_main import main
from ayoe.presentation import PROJECT_TITLE, build_welcome_text
from ayoe.walkthrough import PIPELINE_WALKTHROUGH


def test_welcome_text_mentions_project_and_antimatter() -> None:
    text = build_welcome_text("baseline")
    assert PROJECT_TITLE in text
    assert "antimatter" in text.lower()
    assert "quant-style stochastic simulation" in text.lower()


def test_walkthrough_covers_all_pipeline_stages() -> None:
    assert len(PIPELINE_WALKTHROUGH) == 8
    assert PIPELINE_WALKTHROUGH[0].name == "Proton Beam Input"
    assert PIPELINE_WALKTHROUGH[-1].name == "Final Usable Yield"


def test_enhanced_runner_writes_guided_artifacts(tmp_path, capsys) -> None:
    pytest.importorskip("matplotlib")

    output_dir = tmp_path / "guided"
    exit_code = main(
        [
            "--preset",
            "baseline",
            "--monte-carlo-runs",
            "4",
            "--sensitivity-runs",
            "3",
            "--scenario-runs",
            "3",
            "--scenarios",
            "baseline",
            "stress-test",
            "--seed",
            "42",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert PROJECT_TITLE in captured.out
    assert "Pipeline Walkthrough" in captured.out
    assert (output_dir / "guided_report.md").exists()
    assert (output_dir / "guided_report.html").exists()
    assert (output_dir / "guided_manifest.json").exists()
    assert (output_dir / "charts" / "pipeline_stage_bar.png").exists()
