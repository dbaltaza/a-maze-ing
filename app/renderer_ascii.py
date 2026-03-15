"""Dependency-free ASCII maze renderer."""

from __future__ import annotations

from typing import Protocol

from .parser import MazeConfig

N = 1
E = 2
S = 4
W = 8


class GeneratorLike(Protocol):
    """Protocol for the generator methods used by this module."""

    @property
    def blocked_cells(self) -> set[tuple[int, int]]:
        """Set of fully blocked cell coordinates."""

    def get_cell_walls(self, x: int, y: int) -> int:
        """Return the wall bitmask for a cell."""

    def path_moves(self) -> str:
        """Return shortest path as NESW moves."""


def _path_cells(entry: tuple[int, int], moves: str) -> set[tuple[int, int]]:
    """Expand an NESW move string into visited cells."""
    x, y = entry
    cells: set[tuple[int, int]] = {(x, y)}
    deltas = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
    for step in moves:
        if step not in deltas:
            continue
        dx, dy = deltas[step]
        x += dx
        y += dy
        cells.add((x, y))
    return cells


def build_ascii_lines(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool = False,
) -> list[str]:
    """Build ASCII lines representing the maze."""
    rows = cfg.height * 2 + 1
    cols = cfg.width * 2 + 1
    canvas: list[list[str]] = [[" " for _ in range(cols)] for _ in range(rows)]

    for y in range(0, rows, 2):
        for x in range(0, cols, 2):
            canvas[y][x] = "+"

    blocked = generator.blocked_cells
    path = (
        _path_cells(cfg.entry, generator.path_moves())
        if show_path
        else set()
    )

    for y in range(cfg.height):
        for x in range(cfg.width):
            cx = x * 2 + 1
            cy = y * 2 + 1
            walls = generator.get_cell_walls(x, y)

            cell_char = " "
            if (x, y) in blocked:
                cell_char = "#"
            elif (x, y) in path:
                cell_char = "."

            if (x, y) == cfg.entry:
                cell_char = "E"
            elif (x, y) == cfg.exit:
                cell_char = "X"

            canvas[cy][cx] = cell_char
            if walls & N:
                canvas[cy - 1][cx] = "-"
            if walls & S:
                canvas[cy + 1][cx] = "-"
            if walls & W:
                canvas[cy][cx - 1] = "|"
            if walls & E:
                canvas[cy][cx + 1] = "|"

    return ["".join(row) for row in canvas]


def render_ascii(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool = False,
) -> str:
    """Return and print an ASCII representation of the maze."""
    lines = build_ascii_lines(cfg, generator, show_path=show_path)
    rendered = "\n".join(lines)
    print(rendered)
    return rendered
