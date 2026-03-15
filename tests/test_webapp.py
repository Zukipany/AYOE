from __future__ import annotations

import json
import re
import threading
import urllib.request

import pytest

from ayoe.constants import STAGE_SEQUENCE
from ayoe.webapp import (
    WEB_ROOT,
    build_config,
    create_server,
    export_demo_dataset,
    scenario_payload,
    sensitivity_payload,
    simulation_payload,
)


def test_build_config_clamps_overrides_to_safe_ranges() -> None:
    config = build_config(
        "baseline",
        {
            "beam": {"magnetic_field_t": 99.0, "vacuum_quality": 0.5},
            "stage_multipliers": {"trap_capture": 2.0, "not_a_stage": 4.0},
            "volatility": 0.0,
        },
    )
    assert config.beam.magnetic_field_t == 1.8
    assert config.beam.vacuum_quality == 0.8
    assert config.stages["trap_capture"].nominal_efficiency == pytest.approx(0.16)
    assert all(stage.shock_sigma == 0.0 for stage in config.stages.values())
    assert config.name == "baseline (custom)"


def test_simulation_payload_describes_every_stage() -> None:
    payload = simulation_payload(build_config("baseline"), runs=40, seed=1)
    assert payload["runs"] == 40
    assert len(payload["final_yields"]) == 40
    assert [stage["key"] for stage in payload["stages"]][-1] == "final_usable_yield"
    assert set(payload["samples"]) == {"worst", "median", "best"}
    assert len(payload["samples"]["median"]["counts"]) == 9
    assert payload["samples"]["worst"]["final_yield"] <= payload["samples"]["best"]["final_yield"]
    assert sum(row["share"] for row in payload["regimes"]) == pytest.approx(1.0)
    json.dumps(payload)


def test_sensitivity_and_scenario_payloads_are_serialisable() -> None:
    sensitivity = sensitivity_payload(build_config("baseline"), runs=12, seed=2)
    assert {"up", "down"} <= set(sensitivity["rows"][0])
    scenarios = scenario_payload(runs=10, seed=2, names=["baseline", "aggressive"])
    assert {row["name"] for row in scenarios["rows"]} == {"baseline", "aggressive"}
    json.dumps(sensitivity)
    json.dumps(scenarios)


def test_export_demo_dataset_writes_loadable_script(tmp_path) -> None:
    path = export_demo_dataset(tmp_path / "demo.js", runs=12, sensitivity_runs=10, seed=4)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("window.AYOE_DEMO = ")
    payload = json.loads(text[len("window.AYOE_DEMO = ") : text.rindex(";")])
    assert set(payload["simulations"]) >= {"baseline", "aggressive", "stress-test"}
    assert payload["sensitivity"]["baseline"]["rows"]


def test_server_serves_ui_and_api() -> None:
    assert (WEB_ROOT / "index.html").is_file()
    server = create_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(f"{base}/", timeout=10) as response:
            assert b"AYOE Visual Simulator" in response.read()
        with urllib.request.urlopen(f"{base}/api/meta", timeout=10) as response:
            meta = json.loads(response.read())
        assert len(meta["stages"]) == 8
        request = urllib.request.Request(
            f"{base}/api/simulate",
            data=json.dumps({"base": "high-trap", "runs": 20, "seed": 3}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
        assert payload["name"] == "high-trap"
        assert payload["runs"] == 20
    finally:
        server.shutdown()
        server.server_close()


def test_every_explain_bubble_has_an_explanation() -> None:
    explain_source = (WEB_ROOT / "explain.js").read_text(encoding="utf-8")
    page_keys = set(re.findall(r'data-explain="([^"]+)"', (WEB_ROOT / "index.html").read_text(encoding="utf-8")))
    stage_keys = {"stage:protons"} | {f"stage:{stage}" for stage in STAGE_SEQUENCE}
    for key in page_keys | stage_keys:
        assert re.search(rf"(^|\s)'?{re.escape(key)}'?: \{{", explain_source, re.MULTILINE), key
