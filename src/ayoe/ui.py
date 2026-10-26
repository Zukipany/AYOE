# Source code is private. This file shows only its classes and function signatures.

"""Terminal formatting helpers for the guided experience layer."""
from __future__ import annotations
import textwrap


def banner(title: str, subtitle: str | None=None, width: int=78) -> str:
    ...


def section(title: str, width: int=78) -> str:
    ...


def wrap_block(text: str, width: int=88, indent: int=0) -> str:
    ...


def bullet_list(items: list[str], width: int=88) -> str:
    ...
