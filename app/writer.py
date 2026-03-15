"""Output-file writer for generated mazes."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .parser import MazeConfig


class GeneratorLike(Protocol):
    """Protocol for the generator methods used by this module."""

    def to_hex_lines(self) -> list[str]:
        """Return maze rows in hexadecimal encoding."""

    def path_moves(self) -> str:
        """Return shortest path as NESW moves."""


def write_output(
    path: str | Path,
    cfg: MazeConfig,
    generator: GeneratorLike,
) -> None:
    """Write maze output file using the project-required format."""
    output_path = Path(path)
    hex_lines = generator.to_hex_lines()

    if len(hex_lines) != cfg.height:
        raise ValueError(
            f"generator returned {len(hex_lines)} rows, expected {cfg.height}"
        )
    if any(len(line) != cfg.width for line in hex_lines):
        raise ValueError("generator returned rows with unexpected width")

    payload = "\n".join(
        [
            *hex_lines,
            "",
            f"{cfg.entry[0]},{cfg.entry[1]}",
            f"{cfg.exit[0]},{cfg.exit[1]}",
            generator.path_moves(),
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.write("\n")
