"""Dependency-free ASCII maze renderer."""

from __future__ import annotations

from typing import Protocol

from .parser import MazeConfig

N = 1
E = 2
S = 4
W = 8
CELL_W = 3
CELL_H = 2
_H_WALL = "━"
_V_WALL = "┃"
_TL = "╭"
_TR = "╮"
_BL = "╰"
_BR = "╯"
_TJ = "┳"
_BJ = "┻"
_LJ = "┣"
_RJ = "┫"
_CROSS = "╋"
_BLOCKED = "▓"
_PATH_SEGMENTS = {
    frozenset({"N", "S"}): "│",
    frozenset({"E", "W"}): "─",
    frozenset({"N", "E"}): "╰",
    frozenset({"E", "S"}): "╭",
    frozenset({"S", "W"}): "╮",
    frozenset({"N", "W"}): "╯",
    frozenset({"N"}): "│",
    frozenset({"S"}): "│",
    frozenset({"E"}): "─",
    frozenset({"W"}): "─",
}


def _mode_label(perfect: bool) -> str:
    """Return a human-readable label for the maze mode."""
    return "PERFECT TREE" if perfect else "NOT PERFECT"


def _boxed_lines(title: str, body: list[str]) -> list[str]:
    """Wrap a title and body lines in a Unicode box."""
    width = max(len(title), *(len(line) for line in body))
    lines = [f"{_TL}{_H_WALL * (width + 2)}{_TR}"]
    lines.append(f"{_V_WALL} {title.ljust(width)} {_V_WALL}")
    lines.append(f"{_LJ}{_H_WALL * (width + 2)}{_RJ}")
    lines.extend(f"{_V_WALL} {line.ljust(width)} {_V_WALL}" for line in body)
    lines.append(f"{_BL}{_H_WALL * (width + 2)}{_BR}")
    return lines


def _junction_char(row: int, col: int, rows: int, cols: int) -> str:
    """Return the frame character for a grid intersection."""
    top = row == 0
    bottom = row == rows - 1
    left = col == 0
    right = col == cols - 1
    if top and left:
        return _TL
    if top and right:
        return _TR
    if bottom and left:
        return _BL
    if bottom and right:
        return _BR
    if top:
        return _TJ
    if bottom:
        return _BJ
    if left:
        return _LJ
    if right:
        return _RJ
    return _CROSS


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


def _path_sequence(
    entry: tuple[int, int],
    moves: str,
) -> list[tuple[int, int]]:
    """Expand an NESW move string into an ordered cell sequence."""
    x, y = entry
    cells: list[tuple[int, int]] = [(x, y)]
    deltas = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
    for step in moves:
        if step not in deltas:
            continue
        dx, dy = deltas[step]
        x += dx
        y += dy
        cells.append((x, y))
    return cells


def _path_directions(
    sequence: list[tuple[int, int]],
) -> dict[tuple[int, int], set[str]]:
    """Map each path cell to the directions it connects to."""
    direction_map: dict[tuple[int, int], set[str]] = {}
    move_lookup = {
        (0, -1): "N",
        (1, 0): "E",
        (0, 1): "S",
        (-1, 0): "W",
    }
    opposite = {"N": "S", "E": "W", "S": "N", "W": "E"}
    for current, nxt in zip(sequence, sequence[1:]):
        delta = (nxt[0] - current[0], nxt[1] - current[1])
        direction = move_lookup[delta]
        direction_map.setdefault(current, set()).add(direction)
        direction_map.setdefault(nxt, set()).add(opposite[direction])
    return direction_map


def build_ascii_lines(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool = False,
) -> list[str]:
    """Build Unicode terminal lines representing the maze."""
    rows = cfg.height * (CELL_H + 1) + 1
    cols = cfg.width * (CELL_W + 1) + 1
    canvas: list[list[str]] = [[" " for _ in range(cols)] for _ in range(rows)]

    for row_index, y in enumerate(range(0, rows, CELL_H + 1)):
        for col_index, x in enumerate(range(0, cols, CELL_W + 1)):
            canvas[y][x] = _junction_char(
                row_index,
                col_index,
                cfg.height + 1,
                cfg.width + 1,
            )

    blocked = generator.blocked_cells
    path_moves = generator.path_moves()
    path_sequence = _path_sequence(cfg.entry, path_moves) if show_path else []
    path = set(path_sequence)
    path_dirs = _path_directions(path_sequence) if show_path else {}

    for y in range(cfg.height):
        for x in range(cfg.width):
            cell_left = x * (CELL_W + 1)
            cell_top = y * (CELL_H + 1)
            cx = cell_left + (CELL_W // 2 + 1)
            cy = cell_top + 1
            walls = generator.get_cell_walls(x, y)
            draw_north = bool(walls & N)
            draw_south = bool(walls & S)
            draw_west = bool(walls & W)
            draw_east = bool(walls & E)

            if (x, y) in blocked:
                if (x, y - 1) in blocked:
                    draw_north = False
                if (x, y + 1) in blocked:
                    draw_south = False
                if (x - 1, y) in blocked:
                    draw_west = False
                if (x + 1, y) in blocked:
                    draw_east = False

            if (x, y) in blocked:
                for fill_y in range(1, CELL_H + 1):
                    for fill_x in range(1, CELL_W + 1):
                        canvas[
                            cell_top + fill_y
                        ][cell_left + fill_x] = _BLOCKED
            elif (x, y) in path:
                dirs = path_dirs.get((x, y), set())
                path_char = _PATH_SEGMENTS.get(frozenset(dirs), "•")
                for fill_y in range(1, CELL_H + 1):
                    canvas[cell_top + fill_y][cx] = (
                        "│" if path_char == "│" else " "
                    )
                for fill_x in range(1, CELL_W + 1):
                    if path_char == "─":
                        canvas[cy][cell_left + fill_x] = "─"
                if path_char in {"╰", "╭", "╮", "╯"}:
                    if "N" in dirs:
                        canvas[cell_top + 1][cx] = "│"
                    if "S" in dirs:
                        canvas[cell_top + CELL_H][cx] = "│"
                    if "W" in dirs:
                        canvas[cy][cell_left + 1] = "─"
                    if "E" in dirs:
                        canvas[cy][cell_left + CELL_W] = "─"
                    canvas[cy][cx] = path_char

            if (x, y) == cfg.entry:
                canvas[cy][cx] = "S"
            elif (x, y) == cfg.exit:
                canvas[cy][cx] = "G"
            elif (x, y) not in blocked:
                canvas[cy][cx] = " "
            if draw_north:
                for offset in range(1, CELL_W + 1):
                    canvas[cell_top][cell_left + offset] = _H_WALL
            if draw_south:
                bottom = cell_top + CELL_H + 1
                for offset in range(1, CELL_W + 1):
                    canvas[bottom][cell_left + offset] = _H_WALL
            if draw_west:
                for offset in range(1, CELL_H + 1):
                    canvas[cell_top + offset][cell_left] = _V_WALL
            if draw_east:
                right = cell_left + CELL_W + 1
                for offset in range(1, CELL_H + 1):
                    canvas[cell_top + offset][right] = _V_WALL

    return ["".join(row) for row in canvas]


def render_ascii(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool = False,
) -> str:
    """Return and print a styled terminal representation of the maze."""
    maze_lines = build_ascii_lines(cfg, generator, show_path=show_path)
    path_moves = generator.path_moves()
    mode_label = _mode_label(cfg.perfect)
    entry_text = f"entry  {cfg.entry[0]},{cfg.entry[1]}"
    exit_text = f"exit   {cfg.exit[0]},{cfg.exit[1]}"
    seed_text = cfg.seed if cfg.seed is not None else "random"
    header = _boxed_lines(
        "A-Maze-ing",
        [
            f"size   {cfg.width}x{cfg.height}    mode   {mode_label}",
            f"{entry_text}    {exit_text}",
            f"seed   {seed_text}    path   {len(path_moves)} moves",
        ],
    )
    mode_notice = (
        _boxed_lines(
            "Mode Alert",
            [
                "NOT PERFECT MAZE",
                "extra loops are enabled",
            ],
        )
        if not cfg.perfect
        else []
    )
    legend = _boxed_lines(
        "Legend",
        [
            "S start   G goal   line shortest path",
            "▓ painted 42 mask   renderer ascii fallback",
        ],
    )
    rendered = "\n".join(
        [
            *header,
            *(["", *mode_notice] if mode_notice else []),
            "",
            *maze_lines,
            "",
            *legend,
        ]
    )
    print(rendered)
    return rendered
