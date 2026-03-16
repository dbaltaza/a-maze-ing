"""Interactive curses-based maze renderer."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .errors import RenderError
from .parser import MazeConfig

N = 1
E = 2
S = 4
W = 8
CELL_W = 3
CELL_H = 2
HEADER_H = 4


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
    animated_path: set[tuple[int, int]] | None = None
    generation_in_progress: bool = False
    status: str = "Ready"


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


def _frame_char(
    row_index: int,
    col_index: int,
    row_count: int,
    col_count: int,
    curses_mod: Any,
) -> int:
    top = row_index == 0
    bottom = row_index == row_count - 1
    left = col_index == 0
    right = col_index == col_count - 1
    if top and left:
        return curses_mod.ACS_ULCORNER
    if top and right:
        return curses_mod.ACS_URCORNER
    if bottom and left:
        return curses_mod.ACS_LLCORNER
    if bottom and right:
        return curses_mod.ACS_LRCORNER
    if top:
        return curses_mod.ACS_TTEE
    if bottom:
        return curses_mod.ACS_BTEE
    if left:
        return curses_mod.ACS_LTEE
    if right:
        return curses_mod.ACS_RTEE
    return curses_mod.ACS_PLUS


def _draw_panel(
    stdscr: Any,
    top: int,
    left: int,
    width: int,
    lines: list[str],
    border_attr: int,
    text_attr: int,
) -> None:
    import curses

    height = len(lines) + 2
    stdscr.addch(top, left, curses.ACS_ULCORNER, border_attr)
    stdscr.addch(top, left + width - 1, curses.ACS_URCORNER, border_attr)
    stdscr.addch(top + height - 1, left, curses.ACS_LLCORNER, border_attr)
    stdscr.addch(top + height - 1, left + width - 1, curses.ACS_LRCORNER, border_attr)
    for x in range(left + 1, left + width - 1):
        stdscr.addch(top, x, curses.ACS_HLINE, border_attr)
        stdscr.addch(top + height - 1, x, curses.ACS_HLINE, border_attr)
    for y in range(top + 1, top + height - 1):
        stdscr.addch(y, left, curses.ACS_VLINE, border_attr)
        stdscr.addch(y, left + width - 1, curses.ACS_VLINE, border_attr)
    inner_w = width - 2
    for index, line in enumerate(lines, start=1):
        stdscr.addnstr(top + index, left + 1, line.ljust(inner_w), inner_w, text_attr)


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


def _path_cell_sequence(entry: tuple[int, int], moves: str) -> list[tuple[int, int]]:
    x, y = entry
    cells: list[tuple[int, int]] = [(x, y)]
    deltas = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
    for step in moves:
        delta = deltas.get(step)
        if delta is None:
            continue
        dx, dy = delta
        x += dx
        y += dy
        cells.append((x, y))
    return cells


def _path_directions(sequence: list[tuple[int, int]]) -> dict[tuple[int, int], set[str]]:
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


def _draw_maze(
    stdscr: Any,
    cfg: MazeConfig,
    generator: GeneratorLike,
    state: _UiState,
) -> None:
    import curses

    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    maze_top = HEADER_H + 1
    needed_rows = maze_top + cfg.height * (CELL_H + 1) + 4
    needed_cols = cfg.width * (CELL_W + 1) + 1

    if max_y < needed_rows or max_x < needed_cols:
        msg = (
            f"Terminal too small ({max_x}x{max_y}), "
            f"need at least {needed_cols}x{needed_rows}"
        )
        stdscr.addnstr(0, 0, msg, max_x - 1)
        stdscr.addnstr(1, 0, "Resize terminal or press q to quit.", max_x - 1)
        stdscr.refresh()
        return

    wall_pair = curses.color_pair(state.color_index + 1) if curses.has_colors() else 0
    blocked_pair = curses.color_pair(6) if curses.has_colors() else 0
    path_pair = curses.color_pair(7) if curses.has_colors() else 0
    text_pair = curses.color_pair(8) if curses.has_colors() else 0
    accent_pair = curses.color_pair(9) if curses.has_colors() else curses.A_BOLD

    blocked = generator.blocked_cells
    path_moves = ""
    if not state.generation_in_progress:
        path_moves = generator.path_moves()

    if state.animated_path is not None and not state.generation_in_progress:
        full_sequence = _path_cell_sequence(cfg.entry, path_moves)
        path_sequence = [cell for cell in full_sequence if cell in state.animated_path]
        path = state.animated_path
    elif state.show_path and not state.generation_in_progress:
        path_sequence = _path_cell_sequence(cfg.entry, path_moves)
        path = set(path_sequence)
    else:
        path_sequence = []
        path = set()
    path_dirs = _path_directions(path_sequence) if path_sequence else {}

    header_lines = [
        "A-Maze-ing  terminal interface",
        (
            f"size {cfg.width}x{cfg.height}   mode {'perfect' if cfg.perfect else 'loopy'}   "
            f"seed {cfg.seed if cfg.seed is not None else 'random'}   path "
            f"{'...' if state.generation_in_progress else len(path_moves)}"
        ),
    ]
    controls_lines = [
        "r regenerate   g animate-gen   s animate-solve   p path   c palette   q quit",
        f"renderer curses   generate {state.color_index + 1}/5 palette   status {state.status}",
    ]
    panel_width = max(
        needed_cols,
        max(len(line) for line in header_lines + controls_lines) + 2,
    )
    _draw_panel(stdscr, 0, 0, panel_width, header_lines, accent_pair, text_pair | curses.A_BOLD)
    _draw_panel(stdscr, 0, min(panel_width + 2, max_x - (len(controls_lines[0]) + 4)), len(controls_lines[0]) + 4, controls_lines, wall_pair, text_pair)

    for row_index, y in enumerate(range(0, cfg.height * (CELL_H + 1) + 1, CELL_H + 1)):
        for col_index, x in enumerate(range(0, needed_cols, CELL_W + 1)):
            stdscr.addch(
                maze_top + y,
                x,
                _frame_char(row_index, col_index, cfg.height + 1, cfg.width + 1, curses),
                wall_pair,
            )

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

            attr = 0
            char = " "
            if (x, y) in blocked:
                char = " "
                attr = blocked_pair
            elif (x, y) in path:
                dirs = path_dirs.get((x, y), set())
                char = _PATH_SEGMENTS.get(frozenset(dirs), "•")
                attr = path_pair

            if (x, y) == cfg.entry:
                char = "S"
                attr = accent_pair | curses.A_BOLD
            elif (x, y) == cfg.exit:
                char = "G"
                attr = blocked_pair | curses.A_BOLD

            for fill_y in range(1, CELL_H + 1):
                for fill_x in range(1, CELL_W + 1):
                    stdscr.addch(
                        maze_top + cell_top + fill_y,
                        cell_left + fill_x,
                        "█" if (x, y) in blocked else " ",
                        attr if (x, y) in blocked else 0,
                    )

            if (x, y) in path and (x, y) not in blocked:
                dirs = path_dirs.get((x, y), set())
                if char == "│":
                    for fill_y in range(1, CELL_H + 1):
                        stdscr.addch(maze_top + cell_top + fill_y, cx, "│", path_pair)
                elif char == "─":
                    for fill_x in range(1, CELL_W + 1):
                        stdscr.addch(maze_top + cy, cell_left + fill_x, "─", path_pair)
                else:
                    if "N" in dirs:
                        stdscr.addch(maze_top + cell_top + 1, cx, "│", path_pair)
                    if "S" in dirs:
                        stdscr.addch(maze_top + cell_top + CELL_H, cx, "│", path_pair)
                    if "W" in dirs:
                        stdscr.addch(maze_top + cy, cell_left + 1, "─", path_pair)
                    if "E" in dirs:
                        stdscr.addch(maze_top + cy, cell_left + CELL_W, "─", path_pair)

            stdscr.addch(maze_top + cy, cx, char, attr)
            if draw_north:
                for offset in range(1, CELL_W + 1):
                    stdscr.addch(maze_top + cell_top, cell_left + offset, curses.ACS_HLINE, wall_pair)
            if draw_south:
                bottom = cell_top + CELL_H + 1
                for offset in range(1, CELL_W + 1):
                    stdscr.addch(maze_top + bottom, cell_left + offset, curses.ACS_HLINE, wall_pair)
            if draw_west:
                for offset in range(1, CELL_H + 1):
                    stdscr.addch(maze_top + cell_top + offset, cell_left, curses.ACS_VLINE, wall_pair)
            if draw_east:
                right = cell_left + CELL_W + 1
                for offset in range(1, CELL_H + 1):
                    stdscr.addch(maze_top + cell_top + offset, right, curses.ACS_VLINE, wall_pair)

    footer = f"status  {state.status}"
    stdscr.addnstr(maze_top + cfg.height * (CELL_H + 1) + 2, 0, footer, max_x - 1, text_pair)
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
    curses.init_pair(8, curses.COLOR_WHITE, -1)
    curses.init_pair(9, curses.COLOR_CYAN, -1)


def _loop(
    stdscr: Any,
    cfg: MazeConfig,
    generator: GeneratorLike,
    regenerate: Callable[[Callable[[], None] | None], None] | None,
    generate_delay_ms: int,
    solve_delay_ms: int,
) -> None:
    import curses

    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    _init_colors()

    state = _UiState()
    max_color_index = 4

    def _animate_generation() -> None:
        if regenerate is None:
            state.status = "Regenerate unavailable"
            return

        state.animated_path = None
        state.show_path = False
        state.generation_in_progress = True
        state.status = "Animating generation..."
        frame_counter = 0

        def on_step() -> None:
            nonlocal frame_counter
            frame_counter += 1
            if frame_counter % 2 == 0:
                _draw_maze(stdscr, cfg, generator, state)
                time.sleep(generate_delay_ms / 1000)

        try:
            regenerate(on_step)
            _draw_maze(stdscr, cfg, generator, state)
            state.status = "Generation animation complete"
        except Exception as exc:  # pragma: no cover - runtime UI safeguard
            state.status = f"Animated generate failed: {exc}"
        finally:
            state.generation_in_progress = False

    def _animate_solve() -> None:
        state.show_path = False
        state.animated_path = set()
        state.status = "Animating solve path..."
        try:
            sequence = _path_cell_sequence(cfg.entry, generator.path_moves())
            for cell in sequence:
                state.animated_path.add(cell)
                _draw_maze(stdscr, cfg, generator, state)
                time.sleep(solve_delay_ms / 1000)
            state.status = "Solve animation complete"
        except Exception as exc:  # pragma: no cover - runtime UI safeguard
            state.status = f"Solve animation failed: {exc}"

    while True:
        _draw_maze(stdscr, cfg, generator, state)
        key = stdscr.getch()
        if key in (ord("q"), ord("Q")):
            return
        if key in (ord("p"), ord("P")):
            state.animated_path = None
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
                state.animated_path = None
                regenerate(None)
                state.status = "Maze regenerated"
            except Exception as exc:  # pragma: no cover - runtime UI safeguard
                state.status = f"Regenerate failed: {exc}"
            continue
        if key in (ord("g"), ord("G")):
            _animate_generation()
            continue
        if key in (ord("s"), ord("S")):
            _animate_solve()


def run_curses_ui(
    cfg: MazeConfig,
    generator: GeneratorLike,
    regenerate: Callable[[Callable[[], None] | None], None] | None = None,
    *,
    generate_delay_ms: int = 8,
    solve_delay_ms: int = 25,
) -> None:
    """Run the curses UI, raising RenderError if initialization fails."""
    try:
        import curses
    except Exception as exc:  # pragma: no cover - platform/runtime safeguard
        raise RenderError("curses module is unavailable") from exc

    try:
        curses.wrapper(
            _loop,
            cfg,
            generator,
            regenerate,
            generate_delay_ms,
            solve_delay_ms,
        )
    except curses.error as exc:
        raise RenderError(f"curses rendering failed: {exc}") from exc
