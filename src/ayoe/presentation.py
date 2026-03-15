"""Welcome and onboarding content for the guided AYOE experience."""

from __future__ import annotations

from ayoe.ui import banner, bullet_list, section, wrap_block


PROJECT_TITLE = "Antimatter Yield Optimization Engine"


def build_welcome_text(config_name: str) -> str:
    return "\n".join(
        [
            banner(PROJECT_TITLE, f"Guided Research Experience | active configuration: {config_name}"),
            section("Welcome"),
            wrap_block(
                "This project is a quant-style stochastic simulation platform inspired by the public "
                "logic of antimatter production pipelines. It does not try to reproduce every microscopic "
                "physics detail. Instead, it treats the system as a chain of probabilistic transformations "
                "that can be simulated, stress-tested, compared, and interpreted."
            ),
            section("What Is Antimatter?"),
            wrap_block(
                "Antimatter is the mirror-image partner of ordinary matter. An antiproton has the same mass "
                "as a proton but the opposite charge. When matter and antimatter meet, they can annihilate and "
                "release energy. Because antimatter is difficult to create, slow down, trap, and preserve, its "
                "production pipeline is naturally a high-loss, uncertainty-heavy system."
            ),
            section("What This Engine Does"),
            bullet_list(
                [
                    "Models antimatter production as a multi-stage yield pipeline under uncertainty.",
                    "Tracks how particles are lost, preserved, or improved from one stage to the next.",
                    "Treats randomness as a core feature to study, not something to hide.",
                    "Uses Monte Carlo simulation, bottleneck analysis, sensitivity analysis, and scenario comparison.",
                ]
            ),
            section("What You Are About To See"),
            bullet_list(
                [
                    "A guided walkthrough of the pipeline stages in simple language.",
                    "A single-run diagnostic showing where yield was gained or lost.",
                    "A Monte Carlo view of uncertainty across many runs.",
                    "Scenario and sensitivity results that help explain what matters most.",
                    "Graphical artifacts that make the pipeline easier to interpret like a research report.",
                ]
            ),
        ]
    )
