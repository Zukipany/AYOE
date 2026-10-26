# Source code is private. This file shows only its classes and function signatures.

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
PIPELINE_WALKTHROUGH: tuple[StageGuide, ...]


def build_walkthrough_text() -> str:
    ...
