"""Educational walkthrough content for the antimatter pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from ayoe.ui import bullet_list, section, wrap_block


@dataclass(frozen=True, slots=True)
class StageGuide:
    name: str
    meaning: str
    goes_in: str
    comes_out: str
    what_can_be_lost: str
    why_it_matters: str


PIPELINE_WALKTHROUGH: tuple[StageGuide, ...] = (
    StageGuide(
        name="Proton Beam Input",
        meaning="The run begins with a prepared proton beam aimed at a production target.",
        goes_in="High-energy protons and the machine conditions that deliver them.",
        comes_out="A realized proton pulse that actually reaches the target under current run conditions.",
        what_can_be_lost="Beam quality, timing accuracy, and delivered intensity can all slip before production begins.",
        why_it_matters="A weak start limits every later stage because the whole pipeline depends on the quality of the initial beam.",
    ),
    StageGuide(
        name="Antiproton Creation",
        meaning="Protons strike a target and only a tiny fraction of interactions produce useful antiprotons.",
        goes_in="The delivered proton pulse from the first stage.",
        comes_out="A much smaller antiproton population available for downstream transport.",
        what_can_be_lost="Almost everything. This is one of the harshest conversion stages in the pipeline.",
        why_it_matters="It sets the scale of the whole run. If production is weak, later improvements have less raw material to work with.",
    ),
    StageGuide(
        name="Particle Selection",
        meaning="The system filters for antiprotons that have the right momentum and transport properties.",
        goes_in="A raw antiproton population with mixed conditions.",
        comes_out="A cleaner, more usable beam for deceleration and cooling.",
        what_can_be_lost="Particles outside the acceptable window for transport and handling.",
        why_it_matters="Selection trades quantity for quality. Good selection makes later stages more stable even if it reduces count.",
    ),
    StageGuide(
        name="AD Survival",
        meaning="Antiprotons move through the Antiproton Decelerator, where they are slowed and cooled.",
        goes_in="Selected antiprotons that are still relatively energetic.",
        comes_out="A lower-energy beam that is more suitable for later handling.",
        what_can_be_lost="Particles can be lost during deceleration, storage, and cooling.",
        why_it_matters="This is the first major transition from raw production toward usable low-energy antimatter.",
    ),
    StageGuide(
        name="ELENA Survival",
        meaning="The ELENA ring slows the beam even further to a regime that experiments can use more effectively.",
        goes_in="Antiprotons from the AD stage.",
        comes_out="Very low-energy antiprotons that are far closer to trapping conditions.",
        what_can_be_lost="Additional deceleration and delivery losses, especially if run conditions are unstable.",
        why_it_matters="ELENA is a bridge into the low-energy world where trapping and antihydrogen formation become realistic.",
    ),
    StageGuide(
        name="Trap Capture",
        meaning="Low-energy antiprotons are captured in trapping hardware instead of simply passing through.",
        goes_in="ELENA-delivered antiprotons ready for capture.",
        comes_out="A trapped antiproton population available for controlled mixing and experimentation.",
        what_can_be_lost="A large share of particles can fail to trap, especially if cooling or field conditions are poor.",
        why_it_matters="Trap capture is often a major bottleneck because it is where low-energy handling becomes operationally demanding.",
    ),
    StageGuide(
        name="Antihydrogen Formation",
        meaning="Trapped antiprotons are combined with positrons to create antihydrogen atoms.",
        goes_in="Trapped antiprotons plus formation conditions such as cooling and mixing quality.",
        comes_out="Antihydrogen atoms rather than bare antiprotons.",
        what_can_be_lost="Formation can be inefficient if mixing, timing, or trapped-particle conditions are weak.",
        why_it_matters="This stage turns stored antimatter ingredients into the actual neutral anti-atoms many experiments care about.",
    ),
    StageGuide(
        name="Final Usable Yield",
        meaning="Only a portion of formed antihydrogen is stable or controllable enough to count as usable output.",
        goes_in="Formed antihydrogen atoms.",
        comes_out="The final yield the run can realistically use for research or downstream study.",
        what_can_be_lost="Late-stage instability, imperfect trapping, and handling losses.",
        why_it_matters="This is the end product. It is the number that determines whether a run was merely interesting or truly productive.",
    ),
)


def build_walkthrough_text() -> str:
    sections: list[str] = [section("Pipeline Walkthrough")]
    for index, stage in enumerate(PIPELINE_WALKTHROUGH, start=1):
        sections.append(f"{index}. {stage.name}")
        sections.append(wrap_block(stage.meaning, indent=2))
        sections.append(
            bullet_list(
                [
                    f"Goes in: {stage.goes_in}",
                    f"Comes out: {stage.comes_out}",
                    f"What can be lost: {stage.what_can_be_lost}",
                    f"Why it matters: {stage.why_it_matters}",
                ]
            )
        )
        sections.append("")
    return "\n".join(sections).rstrip()
