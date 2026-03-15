"""Interactive curses-based maze renderer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .errors import RenderError
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
        """Return cell wall bitmask."""

    def path_moves(self) -> str:
        """Return shortest path as NESW moves."""


@dataclass
class _UiState:
    show_path: bool = False
    color_index: int = 0
    status: str = "Keys: r regenerate, p path, c color, q quit"


def _path_cells(entry: tuple[int, int], moves: str) -> set[tuple[int, int]]:
    x, y = entry
    cells: set[tuple[int, int]] = {(x, y)}
    deltas = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
    for step in moves:
        delta = deltas.get(step)
        if delta is None:
            continue
        dx, dy = delta
        x += dx
        y += dy
        cells.add((x, y))
    return cells


def _draw_maze(
    stdscr: Any,
    cfg: MazeConfig,
    generator: GeneratorLike,
    state: _UiState,
) -> None:
    import curses

    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    needed_rows = cfg.height * 2 + 3
    needed_cols = cfg.width * 2 + 1

    if max_y < needed_rows or max_x < needed_cols:
        msg = (
            f"Terminal too small ({max_x}x{max_y}), "
            f"need at least {needed_cols}x{needed_rows}"
        )
        stdscr.addnstr(0, 0, msg, max_x - 1)
        stdscr.addnstr(1, 0, "Resize terminal or press q to quit.", max_x - 1)
        stdscr.refresh()
        return

    wall_pair = (
        curses.color_pair(state.color_index + 1)
        if curses.has_colors()
        else 0
    )
    blocked_pair = curses.color_pair(6) if curses.has_colors() else 0
    path_pair = curses.color_pair(7) if curses.has_colors() else 0

    blocked = generator.blocked_cells
    path = (
        _path_cells(cfg.entry, generator.path_moves())
        if state.show_path
        else set()
    )

    for y in range(0, cfg.height * 2 + 1, 2):
        for x in range(0, cfg.width * 2 + 1, 2):
            stdscr.addch(y, x, "+", wall_pair)

    for y in range(cfg.height):
        for x in range(cfg.width):
            cx = x * 2 + 1
            cy = y * 2 + 1
            walls = generator.get_cell_walls(x, y)

            attr = 0
            char = " "
            if (x, y) in blocked:
                char = "#"
                attr = blocked_pair
            elif (x, y) in path:
                char = "."
                attr = path_pair

            if (x, y) == cfg.entry:
                char = "E"
                attr = curses.A_BOLD
            elif (x, y) == cfg.exit:
                char = "X"
                attr = curses.A_BOLD

            stdscr.addch(cy, cx, char, attr)
            if walls & N:
                stdscr.addch(cy - 1, cx, "-", wall_pair)
            if walls & S:
                stdscr.addch(cy + 1, cx, "-", wall_pair)
            if walls & W:
                stdscr.addch(cy, cx - 1, "|", wall_pair)
            if walls & E:
                stdscr.addch(cy, cx + 1, "|", wall_pair)

    stdscr.addnstr(cfg.height * 2 + 1, 0, state.status, max_x - 1)
    stdscr.refresh()


def _init_colors() -> None:
    import curses

    if not curses.has_colors():
        return

    curses.start_color()
    curses.use_default_colors()
    palette = [
        curses.COLOR_WHITE,
        curses.COLOR_CYAN,
        curses.COLOR_GREEN,
        curses.COLOR_YELLOW,
        curses.COLOR_MAGENTA,
    ]
    for index, color in enumerate(palette, start=1):
        curses.init_pair(index, color, -1)
    curses.init_pair(6, curses.COLOR_RED, -1)
    curses.init_pair(7, curses.COLOR_BLUE, -1)


def _loop(
    stdscr: Any,
    cfg: MazeConfig,
    generator: GeneratorLike,
    regenerate: Callable[[], None] | None,
) -> None:
    import curses

    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    _init_colors()

    state = _UiState()
    max_color_index = 4

    while True:
        _draw_maze(stdscr, cfg, generator, state)
        key = stdscr.getch()
        if key in (ord("q"), ord("Q")):
            return
        if key in (ord("p"), ord("P")):
            state.show_path = not state.show_path
            state.status = (
                f"Path {'enabled' if state.show_path else 'disabled'}"
            )
            continue
        if key in (ord("c"), ord("C")):
            state.color_index = (state.color_index + 1) % (max_color_index + 1)
            state.status = f"Wall color index: {state.color_index + 1}"
            continue
        if key in (ord("r"), ord("R")):
            if regenerate is None:
                state.status = "Regenerate unavailable"
                continue
            try:
                regenerate()
                state.status = "Maze regenerated"
            except Exception as exc:  # pragma: no cover - runtime UI safeguard
                state.status = f"Regenerate failed: {exc}"


def run_curses_ui(
    cfg: MazeConfig,
    generator: GeneratorLike,
    regenerate: Callable[[], None] | None = None,
) -> None:
    """Run the curses UI, raising RenderError if initialization fails."""
    try:
        import curses
    except Exception as exc:  # pragma: no cover - platform/runtime safeguard
        raise RenderError("curses module is unavailable") from exc

    try:
        curses.wrapper(_loop, cfg, generator, regenerate)
    except curses.error as exc:
        raise RenderError(f"curses rendering failed: {exc}") from exc
