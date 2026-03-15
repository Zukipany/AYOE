"""Guided reporting layer that explains existing engine outputs without changing them."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

from ayoe.analytics import compute_run_diagnostics
from ayoe.calibration import build_config_calibration_snapshot
from ayoe.models import (
    CycleResult,
    MonteCarloSummary,
    ScenarioComparisonReport,
    SensitivityReport,
    SimulationConfig,
)
from ayoe.presentation import PROJECT_TITLE
from ayoe.walkthrough import PIPELINE_WALKTHROUGH


def build_cycle_table(cycle: CycleResult) -> pd.DataFrame:
    diagnostics = compute_run_diagnostics(cycle)
    return pd.DataFrame(
        [
            {
                "Stage": metric.stage_label,
                "Input": metric.input_count,
                "Output": metric.output_count,
                "Loss": metric.lost_count,
                "Effective Efficiency": round(metric.effective_efficiency, 6),
                "Cumulative Survival": metric.cumulative_survival_ratio,
                "Shock": round(metric.sampled_shock, 6),
            }
            for metric in diagnostics.stage_metrics
        ]
    )


def build_monte_carlo_table(summary: MonteCarloSummary) -> pd.DataFrame:
    return pd.DataFrame([{"Metric": key, "Value": value} for key, value in summary.stats.items()])


def build_sensitivity_table(report: SensitivityReport, top_n: int = 10) -> pd.DataFrame:
    return pd.DataFrame(report.perturbations[:top_n])


def build_scenario_table(report: ScenarioComparisonReport) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Scenario": row.scenario_name,
                "Mean Yield": row.mean_yield,
                "Std Dev": row.std_yield,
                "Mean Cost": row.mean_cycle_cost_units,
                "Stability": row.mean_stability_score,
                "Yield/Cost": row.mean_yield_per_cost_unit,
                "Risk-Adjusted Score": row.risk_adjusted_score,
                "Top Bottleneck": row.top_bottleneck_stage_label,
            }
            for row in report.scenario_results
        ]
    )


def explain_single_run(cycle: CycleResult) -> str:
    diagnostics = compute_run_diagnostics(cycle)
    return (
        f"The single-run view shows how one stochastic realization moved through the whole antimatter pipeline. "
        f"This run finished with a final usable yield of {diagnostics.final_yield:,}, which means only a tiny "
        f"fraction of the initial proton input survived all the way to the end. The operational bottleneck was "
        f"{diagnostics.operational_bottleneck_stage_label}, which is the stage where losses hurt downstream yield "
        f"the most after taking later stages into account.\n\n"
        f"The most important way to read this table is as a chain reaction. Every stage inherits the quality and "
        f"quantity produced by the stage before it. When cumulative survival drops sharply, it means later stages "
        f"are being asked to work with a much smaller inventory. Strong performance means losses stay controlled, "
        f"shocks remain modest, and the realized outcome stays close to the engine's expected yield. Weak performance "
        f"means that early losses compound or that a fragile late stage turns a decent run into a disappointing one.\n\n"
        f"Shocks should be read as temporary run-specific disturbances rather than permanent truths about the system. "
        f"A small shock means the stage behaved close to its baseline assumptions. A large shock means the realized "
        f"run environment nudged that stage away from its normal operating profile."
    )


def explain_monte_carlo(summary: MonteCarloSummary) -> str:
    mean = summary.stats.get("mean")
    median = summary.stats.get("median")
    std = summary.stats.get("std")
    near_zero = summary.stats.get("probability_near_zero")
    top_bottleneck = summary.bottlenecks[0]["stage_label"] if summary.bottlenecks else "n/a"
    return (
        f"The Monte Carlo section answers the question: what happens when we do not trust a single run? "
        f"Across {summary.run_count:,} simulated cycles, the mean final yield was {mean:,.2f}, the median was "
        f"{median:,.2f}, and the standard deviation was {std:,.2f}. If the mean and median are far apart, the "
        f"distribution is being pulled by occasional unusually strong or weak runs.\n\n"
        f"The probability of landing in the near-zero zone was {near_zero:.2%}. That number is a practical risk "
        f"signal: it tells you how often the pipeline drifts into a seriously unproductive state. The leading "
        f"bottleneck by average loss contribution was {top_bottleneck}. In simple terms, that stage deserves the "
        f"most attention if the goal is to improve expected output rather than just admire isolated lucky runs."
    )


def explain_sensitivity(report: SensitivityReport) -> str:
    top = report.perturbations[0] if report.perturbations else None
    if top is None:
        return "No sensitivity perturbations were available."
    return (
        f"Sensitivity analysis asks a causal question: if we nudge one parameter up or down while holding the rest "
        f"of the simulation structure fixed, how much does the final yield move? The strongest observed local driver "
        f"in this run set was {top['parameter']}, with a {top['direction']} perturbation producing a relative change "
        f"of {top['relative_change']:.2%} in mean yield.\n\n"
        f"This matters because it separates what is merely visible from what is truly influential. A stage can look "
        f"dramatic in one run but still have limited leverage compared with a less obvious control variable. Strong "
        f"sensitivity means small improvements may be worth pursuing. Weak sensitivity means a parameter may be easier "
        f"to ignore without sacrificing much performance."
    )


def explain_scenarios(report: ScenarioComparisonReport) -> str:
    if not report.scenario_results:
        return "No scenario comparison results were available."
    best = report.scenario_results[0]
    most_stable = max(report.scenario_results, key=lambda row: row.mean_stability_score)
    return (
        f"Scenario comparison turns the engine into a decision aid. Instead of asking how one configuration behaves, "
        f"it asks how different operating styles trade off yield, stability, and efficiency. In this run set, the best "
        f"risk-adjusted scenario was {best.scenario_name}, while the most stable scenario was {most_stable.scenario_name}.\n\n"
        f"This is the clearest place to think like a quant researcher. A scenario with the highest mean yield is not "
        f"always the best choice if it is much noisier, more fragile, or more expensive. The purpose of this table is "
        f"to show those tradeoffs plainly so that aggressive, conservative, and specialized operating modes can be judged "
        f"on more than a single headline number."
    )


def explain_charts() -> str:
    return (
        "The charts translate raw simulation output into patterns the eye can inspect quickly. The stage bar chart "
        "shows where particles are entering, surviving, and dropping away. The cumulative survival curve shows the "
        "full shrinkage profile of the pipeline. The Monte Carlo histogram shows whether outcomes cluster tightly or "
        "spread into a wide uncertainty band. The scenario boxplot compares operating modes directly. The bottleneck "
        "chart shows which stage most often limits performance. The sensitivity chart ranks which parameters deserve "
        "the most attention. The heatmap shows how late-stage control changes can bend final yield. The cost-vs-yield "
        "scatter helps distinguish productive scenarios from merely expensive ones."
    )


def build_markdown_report(
    config: SimulationConfig,
    cycle: CycleResult,
    summary: MonteCarloSummary,
    sensitivity_report: SensitivityReport,
    scenario_report: ScenarioComparisonReport,
    chart_manifest: dict[str, str],
) -> str:
    calibration_snapshot = build_config_calibration_snapshot(config)
    source_count = sum(
        len(stage_payload.get("sources", []))
        for stage_payload in calibration_snapshot.get("stages", {}).values()
    )
    parts = [
        f"# {PROJECT_TITLE}",
        "",
        f"Guided report for `{config.name}`.",
        "",
        "## What This Project Is",
        "This report wraps the existing AYOE simulation engine in an educational layer. The stochastic core is unchanged; the sections below simply explain its outputs in a more guided way.",
        "",
        "## Pipeline Walkthrough",
    ]
    for index, stage in enumerate(PIPELINE_WALKTHROUGH, start=1):
        parts.extend(
            [
                f"### {index}. {stage.name}",
                stage.meaning,
                f"- Goes in: {stage.goes_in}",
                f"- Comes out: {stage.comes_out}",
                f"- What can be lost: {stage.what_can_be_lost}",
                f"- Why it matters: {stage.why_it_matters}",
                "",
            ]
        )

    parts.extend(
        [
            "## Single-Run Diagnostic",
            explain_single_run(cycle),
            "",
            "```text",
            build_cycle_table(cycle).to_string(index=False),
            "```",
            "",
            "## Monte Carlo Interpretation",
            explain_monte_carlo(summary),
            "",
            "```text",
            build_monte_carlo_table(summary).to_string(index=False),
            "```",
            "",
            "## Sensitivity Interpretation",
            explain_sensitivity(sensitivity_report),
            "",
            "```text",
            build_sensitivity_table(sensitivity_report).to_string(index=False),
            "```",
            "",
            "## Scenario Interpretation",
            explain_scenarios(scenario_report),
            "",
            "```text",
            build_scenario_table(scenario_report).to_string(index=False),
            "```",
            "",
            "## Charts",
            explain_charts(),
            "",
        ]
    )
    for name, path in chart_manifest.items():
        rel_path = Path(path).name if Path(path).parent.name != "charts" else f"charts/{Path(path).name}"
        parts.extend([f"### {name.replace('_', ' ').title()}", f"![{name}]({rel_path})", ""])

    parts.extend(
        [
            "## Calibration Notes",
            f"The active configuration includes calibration metadata for the main stages, with {source_count} source entries recorded in the current assumption catalog. Sourced, estimated, and synthetic assumptions remain explicitly separated so the simulation can be read honestly.",
            "",
        ]
    )
    return "\n".join(parts).strip() + "\n"


def build_html_report(
    config: SimulationConfig,
    cycle: CycleResult,
    summary: MonteCarloSummary,
    sensitivity_report: SensitivityReport,
    scenario_report: ScenarioComparisonReport,
    chart_manifest: dict[str, str],
) -> str:
    cycle_html = build_cycle_table(cycle).to_html(index=False, border=0, classes="table")
    mc_html = build_monte_carlo_table(summary).to_html(index=False, border=0, classes="table")
    sensitivity_html = build_sensitivity_table(sensitivity_report).to_html(index=False, border=0, classes="table")
    scenario_html = build_scenario_table(scenario_report).to_html(index=False, border=0, classes="table")
    walkthrough_html = "".join(
        f"""
        <div class="card">
          <h3>{index}. {html.escape(stage.name)}</h3>
          <p>{html.escape(stage.meaning)}</p>
          <ul>
            <li><strong>Goes in:</strong> {html.escape(stage.goes_in)}</li>
            <li><strong>Comes out:</strong> {html.escape(stage.comes_out)}</li>
            <li><strong>What can be lost:</strong> {html.escape(stage.what_can_be_lost)}</li>
            <li><strong>Why it matters:</strong> {html.escape(stage.why_it_matters)}</li>
          </ul>
        </div>
        """
        for index, stage in enumerate(PIPELINE_WALKTHROUGH, start=1)
    )
    charts_html = "".join(
        f"""
        <div class="chart-card">
          <h3>{html.escape(name.replace('_', ' ').title())}</h3>
          <img src="charts/{html.escape(Path(path).name)}" alt="{html.escape(name)}" />
        </div>
        """
        for name, path in chart_manifest.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(PROJECT_TITLE)} | Guided Report</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; background: #f5f1e8; color: #1f2933; margin: 0; }}
    .shell {{ max-width: 1180px; margin: 0 auto; padding: 40px 28px 80px; }}
    h1, h2, h3 {{ color: #0f2f44; }}
    .hero {{ background: linear-gradient(135deg, #102a43, #1f5f74); color: white; border-radius: 24px; padding: 28px 32px; margin-bottom: 28px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
    .card, .chart-card {{ background: white; border-radius: 18px; padding: 18px 20px; box-shadow: 0 10px 25px rgba(15, 47, 68, 0.08); }}
    .chart-card img {{ width: 100%; border-radius: 12px; border: 1px solid #d9e2ec; }}
    .table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 18px; overflow: hidden; }}
    .table th, .table td {{ padding: 10px 12px; border-bottom: 1px solid #e6ecf1; text-align: left; }}
    .table th {{ background: #d9e9f2; }}
    p {{ line-height: 1.65; }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <h1>{html.escape(PROJECT_TITLE)}</h1>
      <p>Guided report for the <strong>{html.escape(config.name)}</strong> configuration. This document explains the current working engine's outputs without changing how the engine computes them.</p>
    </div>

    <h2>Pipeline Walkthrough</h2>
    <div class="grid">{walkthrough_html}</div>

    <h2>Single-Run Diagnostic</h2>
    <p>{html.escape(explain_single_run(cycle))}</p>
    {cycle_html}

    <h2>Monte Carlo Interpretation</h2>
    <p>{html.escape(explain_monte_carlo(summary))}</p>
    {mc_html}

    <h2>Sensitivity Interpretation</h2>
    <p>{html.escape(explain_sensitivity(sensitivity_report))}</p>
    {sensitivity_html}

    <h2>Scenario Interpretation</h2>
    <p>{html.escape(explain_scenarios(scenario_report))}</p>
    {scenario_html}

    <h2>Charts</h2>
    <p>{html.escape(explain_charts())}</p>
    <div class="grid">{charts_html}</div>
  </div>
</body>
</html>
"""


def write_guided_reports(
    config: SimulationConfig,
    cycle: CycleResult,
    summary: MonteCarloSummary,
    sensitivity_report: SensitivityReport,
    scenario_report: ScenarioComparisonReport,
    chart_manifest: dict[str, str],
    output_dir: str | Path,
) -> dict[str, str]:
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = report_dir / "guided_report.md"
    html_path = report_dir / "guided_report.html"
    markdown_path.write_text(
        build_markdown_report(
            config,
            cycle,
            summary,
            sensitivity_report,
            scenario_report,
            chart_manifest,
        ),
        encoding="utf-8",
    )
    html_path.write_text(
        build_html_report(
            config,
            cycle,
            summary,
            sensitivity_report,
            scenario_report,
            chart_manifest,
        ),
        encoding="utf-8",
    )
    return {
        "guided_markdown_report": str(markdown_path),
        "guided_html_report": str(html_path),
    }
