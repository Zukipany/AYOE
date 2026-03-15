"""Plotting and reporting helpers for research-style simulation artifacts."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ayoe.analytics import (
    compute_bottlenecks,
    compute_run_diagnostics,
    compute_stage_efficiency_correlations,
)
from ayoe.constants import DEFAULT_HEATMAP_RUNS, STAGE_ENERGY_TARGETS_MEV
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
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _format_count(value: float) -> str:
    if value >= 1e5:
        mantissa, exponent = f"{value:.2e}".split("e")
        return f"{mantissa}e{int(exponent)}"
    return f"{value:,.0f}"


def _format_energy(mev: float) -> str:
    if mev >= 1_000.0:
        return f"{mev / 1_000.0:g} GeV"
    if mev >= 1.0:
        return f"{mev:g} MeV"
    return f"{mev * 1_000.0:g} keV"


def _parameter_label(path: str) -> str:
    return path.replace("stages.", "").replace(".nominal_efficiency", " efficiency").replace("beam.", "")


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_pipeline_stage_bars(cycle: CycleResult, path: str | Path) -> Path:
    output_path = Path(path)
    diagnostics = compute_run_diagnostics(cycle)
    metrics = diagnostics.stage_metrics
    # Counts span ~13 orders of magnitude (protons -> trapped anti-atoms), so a
    # linear axis hides every stage after antiproton creation.
    labels = ["Protons on target"] + [metric.stage_label for metric in metrics]
    counts = np.array([metrics[0].input_count] + [metric.output_count for metric in metrics], dtype=float)
    plotted = np.maximum(counts, 0.8)
    x = np.arange(len(labels))

    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(13, 6.5))
    colors = plt.cm.plasma(np.linspace(0.12, 0.85, len(labels)))
    ax.bar(x, plotted, color=colors, width=0.68, zorder=2)
    ax.set_yscale("log")
    ax.set_ylim(0.5, plotted.max() * 40)
    for index, count in enumerate(counts):
        ax.text(index, plotted[index] * 1.6, _format_count(count), ha="center", va="bottom", fontsize=9, fontweight="bold")
        if index > 0:
            metric = metrics[index - 1]
            efficiency = metric.realized_efficiency
            label = f"{efficiency:.1%}" if efficiency >= 0.001 else f"{efficiency:.1e}"
            ax.text(
                index,
                0.62,
                f"x {label}",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.85, "linewidth": 0},
            )
    energies = [STAGE_ENERGY_TARGETS_MEV["proton_beam_input"]] + [
        STAGE_ENERGY_TARGETS_MEV[metric.stage_name] for metric in metrics
    ]
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{label}\n{_format_energy(energy)}" for label, energy in zip(labels, energies)],
        rotation=30,
        ha="right",
        fontsize=9,
    )
    ax.set_ylabel("Particles surviving (log scale)")
    ax.set_title(f"Particle Funnel: one {cycle.config_name} cycle ({cycle.final_yield} usable anti-atoms)")
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


def plot_bottleneck_analysis(cycles: list[CycleResult], path: str | Path) -> Path:
    output_path = Path(path)
    share_rows = compute_bottlenecks(cycles)
    correlation_rows = compute_stage_efficiency_correlations(cycles)

    _apply_plot_style()
    plt = _plt()
    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 5.5))

    share_labels = [row["stage_label"] for row in share_rows][::-1]
    share_values = [row["log_loss_share"] for row in share_rows][::-1]
    left.barh(share_labels, share_values, color="#7262FD")
    for y, value in enumerate(share_values):
        left.text(value + 0.01, y, f"{value:.0%}", va="center", fontsize=9)
    left.set_xlim(0, max(share_values) * 1.2 if share_values else 1)
    left.set_xlabel("Mean share of pipeline log-loss  (-ln efficiency)")
    left.set_title("Where the Yield Is Lost")

    correlation_labels = [row["stage_label"] for row in correlation_rows][::-1]
    correlation_values = [row["spearman_correlation"] for row in correlation_rows][::-1]
    right.barh(
        correlation_labels,
        correlation_values,
        color=["#30BF78" if value >= 0 else "#F4664A" for value in correlation_values],
    )
    right.axvline(0, color="#333333", linewidth=0.8)
    right.set_xlim(min(-0.05, min(correlation_values, default=0) * 1.15), 1.0)
    right.set_xlabel("Spearman correlation of stage efficiency with final yield")
    right.set_title("What Drives Run-to-Run Variation")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_sensitivity_ranking(report: SensitivityReport, path: str | Path, *, top_n: int = 12) -> Path:
    output_path = Path(path)
    grouped: dict[str, dict[str, float]] = {}
    for row in report.perturbations:
        change = row["relative_change"] if row["relative_change"] is not None else 0.0
        grouped.setdefault(row["parameter"], {})[row["direction"]] = change

    ranked = sorted(
        grouped.items(),
        key=lambda item: max(abs(value) for value in item[1].values()),
        reverse=True,
    )[:top_n][::-1]
    labels = [_parameter_label(name) for name, _ in ranked]
    downs = [values.get("down", 0.0) for _, values in ranked]
    ups = [values.get("up", 0.0) for _, values in ranked]
    y = np.arange(len(labels))

    _apply_plot_style()
    plt = _plt()
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.barh(y, downs, color="#F4664A", label=f"parameter -{report.delta:.0%}")
    ax.barh(y, ups, color="#30BF78", label=f"parameter +{report.delta:.0%}")
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:+.0%}"))
    ax.set_xlabel("Change in mean final yield")
    ax.set_title(f"Sensitivity Tornado ({report.config_name}, {report.runs} runs per perturbation)")
    ax.legend(loc="lower right")
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

    # Every cell reuses the same seed (common random numbers) so differences
    # between cells come from the parameters rather than sampling noise.
    cell_seed = int(np.random.SeedSequence(seed).generate_state(1, dtype=np.uint64)[0])
    for y, mixing_scale in enumerate(mixing_multipliers):
        for x, trap_scale in enumerate(trap_multipliers):
            scenario = config.copy()
            scenario.beam.mixing_efficiency = min(max(scenario.beam.mixing_efficiency * mixing_scale, 0.01), 0.999)
            scenario.stages["trap_capture"].nominal_efficiency = min(
                max(scenario.stages["trap_capture"].nominal_efficiency * trap_scale, 0.001),
                0.95,
            )
            _, summary = run_monte_carlo(scenario, runs=runs, seed=cell_seed)
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
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]
            shade = "white" if value > (matrix.min() + matrix.max()) / 2 else "#1d1d1d"
            ax.text(column, row, f"{value:.1f}", ha="center", va="center", fontsize=9, color=shade)
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
        "bottleneck_analysis_chart": plot_bottleneck_analysis(monte_carlo_cycles, report_dir / "bottleneck_analysis.png"),
        "sensitivity_ranking_chart": plot_sensitivity_ranking(sensitivity_report, report_dir / "sensitivity_ranking.png"),
        "parameter_heatmap": plot_parameter_heatmap(config, report_dir / "yield_heatmap.png", seed=seed),
        "cost_yield_scatter": plot_cost_vs_yield(scenario_report, report_dir / "cost_vs_yield_scatter.png"),
    }
    return {name: str(path) for name, path in artifacts.items()}
