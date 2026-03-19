"""Output serialization helpers for generated mazes."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ExportableMaze(Protocol):
    """Protocol for generators that can be written to output files."""

    def to_hex_lines(self) -> list[str]:
        """Return maze rows in hexadecimal encoding."""

    def path_moves(self) -> str:
        """Return shortest path as NESW moves."""


def write_output(
    path: str | Path,
    *,
    width: int,
    height: int,
    entry: tuple[int, int],
    exit: tuple[int, int],
    generator: ExportableMaze,
) -> None:
    """Write maze output using the project-required file format."""
    output_path = Path(path)
    hex_lines = generator.to_hex_lines()

    if len(hex_lines) != height:
        raise ValueError(
            f"generator returned {len(hex_lines)} rows, expected {height}"
        )
    if any(len(line) != width for line in hex_lines):
        raise ValueError("generator returned rows with unexpected width")

    payload = "\n".join(
        [
            *hex_lines,
            "",
            f"{entry[0]},{entry[1]}",
            f"{exit[0]},{exit[1]}",
            generator.path_moves(),
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.write("\n")
