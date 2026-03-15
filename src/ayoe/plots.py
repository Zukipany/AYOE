"""Non-invasive plotting wrappers around the existing reporting module."""

from ayoe.reporting import (
    plot_bottleneck_frequency,
    plot_cost_vs_yield,
    plot_cumulative_survival_curve,
    plot_monte_carlo_histogram,
    plot_parameter_heatmap,
    plot_pipeline_stage_bars,
    plot_scenario_boxplot,
    plot_sensitivity_ranking,
    write_full_report_artifacts,
)

__all__ = [
    "plot_bottleneck_frequency",
    "plot_cost_vs_yield",
    "plot_cumulative_survival_curve",
    "plot_monte_carlo_histogram",
    "plot_parameter_heatmap",
    "plot_pipeline_stage_bars",
    "plot_scenario_boxplot",
    "plot_sensitivity_ranking",
    "write_full_report_artifacts",
]
