"""Terminal formatting helpers for the guided experience layer."""

from __future__ import annotations

import textwrap


def banner(title: str, subtitle: str | None = None, width: int = 78) -> str:
    line = "=" * width
    parts = [line, title.center(width)]
    if subtitle:
        parts.append(subtitle.center(width))
    parts.append(line)
    return "\n".join(parts)


def section(title: str, width: int = 78) -> str:
    return f"\n{title}\n" + ("-" * min(width, max(len(title), 12)))


def wrap_block(text: str, width: int = 88, indent: int = 0) -> str:
    prefix = " " * indent
    return textwrap.fill(text.strip(), width=width, initial_indent=prefix, subsequent_indent=prefix)


def bullet_list(items: list[str], width: int = 88) -> str:
    rendered: list[str] = []
    for item in items:
        rendered.append(
            textwrap.fill(
                item,
                width=width,
                initial_indent="- ",
                subsequent_indent="  ",
            )
        )
    return "\n".join(rendered)
