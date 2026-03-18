"""Dependency-free ASCII maze renderer."""

from __future__ import annotations

import os
import sys
from typing import Callable, Protocol

from .parser import MazeConfig

N = 1
E = 2
S = 4
W = 8
CELL_W = 3
_H_WALL = "-"
_V_WALL = "|"
_CORNER = "+"
_BLOCKED = "#"
_PATH = "."
_ANSI_RESET = "\033[0m"
_ANSI_CLEAR = "\033[2J\033[H"
_WALL_COLORS = [
    "\033[97m",
    "\033[96m",
    "\033[92m",
    "\033[93m",
    "\033[95m",
]
_BLOCKED_COLOR = "\033[37m"
_PATH_COLOR = "\033[94m"
_START_COLOR = "\033[95m"
_GOAL_COLOR = "\033[91m"
_TEXT_COLOR = "\033[97m"
_MUTED_COLOR = "\033[90m"


def _mode_label(perfect: bool) -> str:
    """Return a human-readable label for the maze mode."""
    return "PERFECT TREE" if perfect else "NOT PERFECT"


def _boxed_lines(title: str, body: list[str]) -> list[str]:
    """Wrap a title and body lines in a simple ASCII box."""
    width = max(len(title), *(len(line) for line in body))
    lines = [f"{_CORNER}{_H_WALL * (width + 2)}{_CORNER}"]
    lines.append(f"{_V_WALL} {title.ljust(width)} {_V_WALL}")
    lines.append(f"{_CORNER}{_H_WALL * (width + 2)}{_CORNER}")
    lines.extend(f"{_V_WALL} {line.ljust(width)} {_V_WALL}" for line in body)
    lines.append(f"{_CORNER}{_H_WALL * (width + 2)}{_CORNER}")
    return lines


class GeneratorLike(Protocol):
    """Protocol for the generator methods used by this module."""

    @property
    def blocked_cells(self) -> set[tuple[int, int]]:
        """Set of fully blocked cell coordinates."""

    def get_cell_walls(self, x: int, y: int) -> int:
        """Return the wall bitmask for a cell."""

    def path_moves(self) -> str:
        """Return shortest path as NESW moves."""


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


def _interior_center(x: int, y: int) -> tuple[int, int]:
    """Return the canvas coordinate for the center of one cell."""
    return (y * 2 + 1, x * (CELL_W + 1) + 2)


def build_ascii_lines(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool = False,
) -> list[str]:
    """Build plain ASCII lines representing the maze."""
    rows = cfg.height * 2 + 1
    cols = cfg.width * (CELL_W + 1) + 1
    canvas: list[list[str]] = [[" " for _ in range(cols)] for _ in range(rows)]

    for y in range(0, rows, 2):
        for x in range(0, cols, CELL_W + 1):
            canvas[y][x] = _CORNER

    blocked = generator.blocked_cells
    path_moves = generator.path_moves() if show_path else ""
    path_sequence = _path_sequence(cfg.entry, path_moves) if show_path else []

    for y in range(cfg.height):
        for x in range(cfg.width):
            walls = generator.get_cell_walls(x, y)
            center_row, center_col = _interior_center(x, y)
            left = x * (CELL_W + 1)
            right = left + CELL_W + 1
            top = y * 2
            bottom = top + 2

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

            if draw_north:
                for offset in range(1, CELL_W + 1):
                    canvas[top][left + offset] = _H_WALL
            if draw_south:
                for offset in range(1, CELL_W + 1):
                    canvas[bottom][left + offset] = _H_WALL
            if draw_west:
                canvas[center_row][left] = _V_WALL
            if draw_east:
                canvas[center_row][right] = _V_WALL

            if (x, y) in blocked:
                for offset in range(1, CELL_W + 1):
                    canvas[center_row][left + offset] = _BLOCKED

    if path_sequence:
        for current, nxt in zip(path_sequence, path_sequence[1:]):
            cur_row, cur_col = _interior_center(*current)
            next_row, next_col = _interior_center(*nxt)
            canvas[cur_row][cur_col] = _PATH
            canvas[next_row][next_col] = _PATH
            if cur_row == next_row:
                start = min(cur_col, next_col)
                end = max(cur_col, next_col)
                for col in range(start + 1, end):
                    canvas[cur_row][col] = _PATH
            else:
                start = min(cur_row, next_row)
                end = max(cur_row, next_row)
                for row in range(start + 1, end):
                    canvas[row][cur_col] = _PATH

    start_row, start_col = _interior_center(*cfg.entry)
    goal_row, goal_col = _interior_center(*cfg.exit)
    canvas[start_row][start_col] = "S"
    canvas[goal_row][goal_col] = "G"

    return ["".join(row).rstrip() for row in canvas]


def render_ascii(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool = False,
) -> str:
    """Return and print a plain ASCII representation of the maze."""
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
            "S start   G goal   . shortest path",
            "# painted 42 mask   plain ASCII fallback",
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


def _supports_ansi() -> bool:
    """Return whether the current terminal likely supports ANSI colors."""
    term = os.environ.get("TERM", "").lower()
    return sys.stdout.isatty() and term not in {"", "dumb"}


def _style_maze_line(
    line: str,
    *,
    palette_index: int,
    show_path: bool,
    use_color: bool,
) -> str:
    """Colorize one maze line for the interactive terminal UI."""
    if not use_color:
        return line

    wall_color = _WALL_COLORS[palette_index % len(_WALL_COLORS)]
    parts: list[str] = []
    for ch in line:
        if ch in {_CORNER, _H_WALL, _V_WALL}:
            parts.append(f"{wall_color}{ch}{_ANSI_RESET}")
        elif ch == _BLOCKED:
            parts.append(f"{_BLOCKED_COLOR}{ch}{_ANSI_RESET}")
        elif ch == "S":
            parts.append(f"{_START_COLOR}{ch}{_ANSI_RESET}")
        elif ch == "G":
            parts.append(f"{_GOAL_COLOR}{ch}{_ANSI_RESET}")
        elif ch == _PATH and show_path:
            parts.append(f"{_PATH_COLOR}{ch}{_ANSI_RESET}")
        else:
            parts.append(ch)
    return "".join(parts)


def _interactive_screen(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool,
    palette_index: int,
    status: str,
    use_color: bool,
) -> str:
    """Build the full interactive ASCII screen."""
    maze_lines = build_ascii_lines(cfg, generator, show_path=show_path)
    styled_maze = [
        _style_maze_line(
            line,
            palette_index=palette_index,
            show_path=show_path,
            use_color=use_color,
        )
        for line in maze_lines
    ]

    seed_text = cfg.seed if cfg.seed is not None else "random"
    summary = (
        f"A-Maze-ing  {cfg.width}x{cfg.height}  {_mode_label(cfg.perfect)}  "
        f"seed {seed_text}"
    )
    if use_color:
        summary = f"{_TEXT_COLOR}{summary}{_ANSI_RESET}"

    menu_lines = [
        f"1. {'Hide' if show_path else 'Show'} path from entry to exit",
        "2. Re-generate a new maze",
        "3. Rotate maze colors",
        "4. Quit",
        f"Status: {status}",
        "Choice (1-4): ",
    ]
    if use_color:
        menu_lines = [
            f"{_MUTED_COLOR}{line}{_ANSI_RESET}"
            if line != "Choice (1-4): "
            else line
            for line in menu_lines
        ]
    return "\n".join([summary, "", *styled_maze, "", *menu_lines[:-1], menu_lines[-1]])


def run_ascii_ui(
    cfg: MazeConfig,
    generator: GeneratorLike,
    regenerate: Callable[[Callable[[], None] | None], None] | None = None,
) -> None:
    """Run a simple interactive terminal UI for the ASCII fallback."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        render_ascii(cfg, generator, show_path=False)
        return

    show_path = False
    palette_index = 0
    status = "Ready"
    use_color = _supports_ansi()

    while True:
        screen = _interactive_screen(
            cfg,
            generator,
            show_path=show_path,
            palette_index=palette_index,
            status=status,
            use_color=use_color,
        )
        print(f"{_ANSI_CLEAR}{screen}", end="", flush=True)

        try:
            choice = input().strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "1":
            show_path = not show_path
            status = f"Path {'enabled' if show_path else 'hidden'}"
            continue
        if choice == "2":
            if regenerate is None:
                status = "Regenerate unavailable"
                continue
            try:
                regenerate(None)
                show_path = False
                status = "Maze regenerated"
            except Exception as exc:  # pragma: no cover - runtime safeguard
                status = f"Regenerate failed: {exc}"
            continue
        if choice == "3":
            palette_index = (palette_index + 1) % len(_WALL_COLORS)
            status = f"Palette {palette_index + 1}/{len(_WALL_COLORS)}"
            continue
        if choice == "4":
            print(_ANSI_CLEAR, end="", flush=True)
            return
        status = "Invalid choice"
