"""Plotting and reporting helpers for research-style simulation artifacts."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ayoe.analytics import compute_bottleneck_frequencies, compute_run_diagnostics
from ayoe.constants import DEFAULT_HEATMAP_RUNS
from ayoe.engine import run_monte_carlo
from ayoe.models import (
    CycleResult,
    ScenarioComparisonReport,
    SensitivityReport,
    SimulationConfig,
)


def _prepare_output_dir(path: str | Path) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _apply_plot_style() -> None:
    plt = _plt()
    plt.style.use("default")
    plt.rcParams.update(
        {
            "figure.figsize": (10, 6),
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "axes.grid": True,
            "grid.alpha": 0.18,
            "font.size": 10,
            "savefig.dpi": 160,
        }
    )


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_pipeline_stage_bars(cycle: CycleResult, path: str | Path) -> Path:
    output_path = Path(path)
    diagnostics = compute_run_diagnostics(cycle)
    labels = [metric.stage_label for metric in diagnostics.stage_metrics]
    inputs = np.array([metric.input_count for metric in diagnostics.stage_metrics], dtype=float)
    outputs = np.array([metric.output_count for metric in diagnostics.stage_metrics], dtype=float)
    losses = np.array([metric.lost_count for metric in diagnostics.stage_metrics], dtype=float)
    x = np.arange(len(labels))

    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x - 0.25, inputs, width=0.25, label="Input", color="#5B8FF9")
    ax.bar(x, outputs, width=0.25, label="Output", color="#61DDAA")
    ax.bar(x + 0.25, losses, width=0.25, label="Loss", color="#F6BD16")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("Particle count")
    ax.set_title("Pipeline Stage Accounting")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_cumulative_survival_curve(cycle: CycleResult, path: str | Path) -> Path:
    output_path = Path(path)
    diagnostics = compute_run_diagnostics(cycle)
    labels = [metric.stage_label for metric in diagnostics.stage_metrics]
    survival = [metric.cumulative_survival_ratio for metric in diagnostics.stage_metrics]

    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(labels, survival, marker="o", linewidth=2.2, color="#5D7092")
    ax.fill_between(labels, survival, alpha=0.15, color="#5D7092")
    ax.set_yscale("log")
    ax.set_ylabel("Cumulative survival ratio")
    ax.set_title("Cumulative Survival Across Stages")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_monte_carlo_histogram(cycles: list[CycleResult], path: str | Path) -> Path:
    output_path = Path(path)
    yields = np.array([cycle.final_yield for cycle in cycles], dtype=float)

    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(yields, bins=min(30, max(12, int(np.sqrt(len(yields))))), color="#5B8FF9", edgecolor="white")
    ax.axvline(np.mean(yields), color="#F4664A", linestyle="--", linewidth=2, label="Mean")
    ax.axvline(np.median(yields), color="#30BF78", linestyle="-.", linewidth=2, label="Median")
    ax.set_xlabel("Final usable yield")
    ax.set_ylabel("Run count")
    ax.set_title("Monte Carlo Distribution of Final Yield")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_scenario_boxplot(scenario_cycles: dict[str, list[CycleResult]], path: str | Path) -> Path:
    output_path = Path(path)
    labels = list(scenario_cycles)
    data = [[cycle.final_yield for cycle in scenario_cycles[name]] for name in labels]

    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(12, 6))
    box = ax.boxplot(data, patch_artist=True, tick_labels=labels, showfliers=False)
    palette = ["#5B8FF9", "#61DDAA", "#65789B", "#F6BD16", "#7262FD", "#78D3F8", "#9661BC", "#F08BB4"]
    for patch, color in zip(box["boxes"], palette, strict=False):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
    ax.set_ylabel("Final usable yield")
    ax.set_title("Scenario Distribution Comparison")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_bottleneck_frequency(cycles: list[CycleResult], path: str | Path) -> Path:
    output_path = Path(path)
    rows = compute_bottleneck_frequencies(cycles)
    labels = [row["stage_label"] for row in rows]
    values = [row["frequency"] for row in rows]

    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels, values, color="#F6BD16")
    ax.set_xlabel("Frequency")
    ax.set_title("Operational Bottleneck Frequency")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_sensitivity_ranking(report: SensitivityReport, path: str | Path, *, top_n: int = 10) -> Path:
    output_path = Path(path)
    grouped: dict[str, float] = {}
    for row in report.perturbations:
        score = abs(row["relative_change"]) if row["relative_change"] is not None else 0.0
        grouped[row["parameter"]] = max(grouped.get(row["parameter"], 0.0), score)

    top_rows = sorted(grouped.items(), key=lambda row: row[1], reverse=True)[:top_n]
    labels = [name.replace("stages.", "").replace(".nominal_efficiency", "") for name, _ in top_rows]
    values = [value for _, value in top_rows]

    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(labels[::-1], values[::-1], color="#30BF78")
    ax.set_xlabel("Absolute relative change in mean yield")
    ax.set_title("Sensitivity Ranking")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def build_parameter_heatmap(
    config: SimulationConfig,
    *,
    seed: int | None = None,
    runs: int = DEFAULT_HEATMAP_RUNS,
) -> tuple[np.ndarray, list[float], list[float]]:
    trap_multipliers = [0.80, 0.90, 1.00, 1.10, 1.20]
    mixing_multipliers = [0.85, 0.95, 1.00, 1.10, 1.20]
    matrix = np.zeros((len(mixing_multipliers), len(trap_multipliers)), dtype=float)

    root = np.random.SeedSequence(seed)
    child_sequences = root.spawn(len(trap_multipliers) * len(mixing_multipliers))
    child_index = 0
    for y, mixing_scale in enumerate(mixing_multipliers):
        for x, trap_scale in enumerate(trap_multipliers):
            scenario = config.copy()
            scenario.beam.mixing_efficiency = min(max(scenario.beam.mixing_efficiency * mixing_scale, 0.01), 0.999)
            scenario.stages["trap_capture"].nominal_efficiency = min(
                max(scenario.stages["trap_capture"].nominal_efficiency * trap_scale, 0.001),
                0.95,
            )
            scenario_seed = int(child_sequences[child_index].generate_state(1, dtype=np.uint64)[0])
            child_index += 1
            _, summary = run_monte_carlo(scenario, runs=runs, seed=scenario_seed)
            matrix[y, x] = float(summary.stats["mean"] or 0.0)
    return matrix, trap_multipliers, mixing_multipliers


def plot_parameter_heatmap(
    config: SimulationConfig,
    path: str | Path,
    *,
    seed: int | None = None,
    runs: int = DEFAULT_HEATMAP_RUNS,
) -> Path:
    output_path = Path(path)
    matrix, trap_multipliers, mixing_multipliers = build_parameter_heatmap(config, seed=seed, runs=runs)

    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(np.arange(len(trap_multipliers)))
    ax.set_yticks(np.arange(len(mixing_multipliers)))
    ax.set_xticklabels([f"{value:.2f}x" for value in trap_multipliers])
    ax.set_yticklabels([f"{value:.2f}x" for value in mixing_multipliers])
    ax.set_xlabel("Trap efficiency multiplier")
    ax.set_ylabel("Mixing efficiency multiplier")
    ax.set_title("Late-Stage Yield Surface")
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Mean final yield")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_cost_vs_yield(report: ScenarioComparisonReport, path: str | Path) -> Path:
    output_path = Path(path)
    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(10, 6))
    for row in report.scenario_results:
        ax.scatter(row.mean_cycle_cost_units, row.mean_yield, s=80, label=row.scenario_name)
        ax.annotate(row.scenario_name, (row.mean_cycle_cost_units, row.mean_yield), textcoords="offset points", xytext=(5, 5))
    ax.set_xlabel("Mean cycle cost units")
    ax.set_ylabel("Mean final yield")
    ax.set_title("Cost vs Yield by Scenario")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def write_full_report_artifacts(
    config: SimulationConfig,
    cycle: CycleResult,
    monte_carlo_cycles: list[CycleResult],
    sensitivity_report: SensitivityReport,
    scenario_report: ScenarioComparisonReport,
    scenario_cycles: dict[str, list[CycleResult]],
    output_dir: str | Path,
    *,
    seed: int | None = None,
) -> dict[str, str]:
    report_dir = _prepare_output_dir(output_dir)
    artifacts = {
        "pipeline_stage_chart": plot_pipeline_stage_bars(cycle, report_dir / "pipeline_stage_bar.png"),
        "cumulative_survival_chart": plot_cumulative_survival_curve(cycle, report_dir / "cumulative_survival_curve.png"),
        "monte_carlo_histogram": plot_monte_carlo_histogram(monte_carlo_cycles, report_dir / "monte_carlo_histogram.png"),
        "scenario_boxplot": plot_scenario_boxplot(scenario_cycles, report_dir / "scenario_boxplot.png"),
        "bottleneck_frequency_chart": plot_bottleneck_frequency(monte_carlo_cycles, report_dir / "bottleneck_frequency.png"),
        "sensitivity_ranking_chart": plot_sensitivity_ranking(sensitivity_report, report_dir / "sensitivity_ranking.png"),
        "parameter_heatmap": plot_parameter_heatmap(config, report_dir / "yield_heatmap.png", seed=seed),
        "cost_yield_scatter": plot_cost_vs_yield(scenario_report, report_dir / "cost_vs_yield_scatter.png"),
    }
    return {name: str(path) for name, path in artifacts.items()}
