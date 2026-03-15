# Antimatter Yield Optimization Engine

AYOE is a compact quant-style simulation engine for modeling antimatter production as a multi-stage stochastic pipeline. The alpha focuses on a clean Python core that can run one production cycle, execute Monte Carlo batches, and surface stage bottlenecks plus basic sensitivity signals.

## Quick Start

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/ayoe run --preset baseline --seed 42
.venv/bin/ayoe monte-carlo --preset baseline --runs 250 --seed 42
.venv/bin/ayoe sensitivity --preset baseline --runs 150 --seed 42
```

## Commands

- `ayoe run` simulates one full production cycle and can export JSON plus stage CSV output.
- `ayoe monte-carlo` repeats the full pipeline, prints summary statistics, and can export JSON plus run/stage CSV files.
- `ayoe sensitivity` runs one-at-a-time parameter perturbations and reports which core throughput parameters matter most.

## Presets

Built-in presets are bundled under `baseline`, `conservative`, and `aggressive`. They use literature-inspired placeholder values and are intentionally simplified rather than calibrated.

## Notes

- The model is structured for clarity and extension, not microscopic physical fidelity.
- Physics-leaning beam inputs such as target density, magnetic field, vacuum quality, and trap temperature are used as stage modifiers.
- The local virtual environment already targets Python 3.12, and the project metadata is pinned to `>=3.12`.
