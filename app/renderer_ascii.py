"""Dependency-free ASCII maze renderer."""

from __future__ import annotations

import os
import sys
import time
from collections import deque
from typing import Callable, Protocol

from .parser import MazeConfig

N = 1
E = 2
S = 4
W = 8
CELL_W = 2
_H_WALL = "-"
_V_WALL = "|"
_CORNER = "+"
_BLOCKED = "#"
_DISCOVERED = "o"
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
_DISCOVERED_COLOR = "\033[36m"
_START_COLOR = "\033[95m"
_GOAL_COLOR = "\033[91m"
_TEXT_COLOR = "\033[97m"
_MUTED_COLOR = "\033[90m"
_PANEL_COLOR = "\033[38;5;250m"
_ACCENT_COLOR = "\033[38;5;159m"
_STATUS_COLOR = "\033[38;5;222m"


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


def _cell_bounds(x: int, y: int) -> tuple[int, int, int, int, int, int]:
    """Return canvas bounds and center for one logical cell."""
    step = CELL_W + 1
    left = x * step
    top = y * 2
    return (left, left + step, top, top + 2, top + 1, left + 2)


def _fill_span(
    canvas: list[list[str]],
    row: int,
    start: int,
    char: str,
) -> None:
    """Fill a horizontal cell interior span with one character."""
    for offset in range(1, CELL_W + 1):
        canvas[row][start + offset] = char


def _resolve_path_sequence(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool,
    path_sequence: list[tuple[int, int]] | None,
) -> list[tuple[int, int]]:
    """Return the path sequence that should be drawn for this frame."""
    if path_sequence is not None:
        return list(path_sequence)
    if show_path:
        return _path_sequence(cfg.entry, generator.path_moves())
    return []


def _draw_path_segment(
    canvas: list[list[str]],
    current: tuple[int, int],
    nxt: tuple[int, int],
) -> None:
    """Draw one path segment between two adjacent cells."""
    cur_row, cur_col = _interior_center(*current)
    next_row, next_col = _interior_center(*nxt)
    canvas[cur_row][cur_col] = _PATH
    canvas[next_row][next_col] = _PATH
    if cur_row == next_row:
        start = min(cur_col, next_col)
        end = max(cur_col, next_col)
        for col in range(start + 1, end):
            canvas[cur_row][col] = _PATH
        return

    start = min(cur_row, next_row)
    end = max(cur_row, next_row)
    for row in range(start + 1, end):
        canvas[row][cur_col] = _PATH


def _bfs_discovery(
    cfg: MazeConfig,
    generator: GeneratorLike,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Return BFS visit order and the shortest path to the goal."""
    blocked = generator.blocked_cells
    start = cfg.entry
    goal = cfg.exit
    if start in blocked or goal in blocked:
        return ([], [])

    queue: deque[tuple[int, int]] = deque([start])
    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    order: list[tuple[int, int]] = []
    deltas = {
        N: (0, -1),
        E: (1, 0),
        S: (0, 1),
        W: (-1, 0),
    }

    while queue:
        x, y = queue.popleft()
        current = (x, y)
        order.append(current)
        if current == goal:
            break

        walls = generator.get_cell_walls(x, y)
        for bit, (dx, dy) in deltas.items():
            if walls & bit:
                continue
            nxt = (x + dx, y + dy)
            nx, ny = nxt
            if not (0 <= nx < cfg.width and 0 <= ny < cfg.height):
                continue
            if nxt in blocked or nxt in prev:
                continue
            prev[nxt] = current
            queue.append(nxt)

    if goal not in prev:
        return (order, [])

    path: list[tuple[int, int]] = []
    cur: tuple[int, int] | None = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return (order, path)


def build_ascii_lines(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool = False,
    path_sequence: list[tuple[int, int]] | None = None,
    discovered_cells: set[tuple[int, int]] | None = None,
) -> list[str]:
    """Build plain ASCII lines representing the maze."""
    rows = cfg.height * 2 + 1
    cols = cfg.width * (CELL_W + 1) + 1
    canvas: list[list[str]] = [[" " for _ in range(cols)] for _ in range(rows)]

    for y in range(0, rows, 2):
        for x in range(0, cols, CELL_W + 1):
            canvas[y][x] = _CORNER

    blocked = generator.blocked_cells
    active_discovered = discovered_cells or set()
    active_path_sequence = _resolve_path_sequence(
        cfg,
        generator,
        show_path=show_path,
        path_sequence=path_sequence,
    )

    for y in range(cfg.height):
        for x in range(cfg.width):
            walls = generator.get_cell_walls(x, y)
            left, right, top, bottom, center_row, _center_col = _cell_bounds(
                x, y
            )

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
                _fill_span(canvas, top, left, _H_WALL)
            if draw_south:
                _fill_span(canvas, bottom, left, _H_WALL)
            if draw_west:
                canvas[center_row][left] = _V_WALL
            if draw_east:
                canvas[center_row][right] = _V_WALL

            if (x, y) in blocked:
                _fill_span(canvas, center_row, left, _BLOCKED)
            elif (x, y) in active_discovered:
                _fill_span(canvas, center_row, left, _DISCOVERED)

    # Merge adjacent blocked cells into one solid filled 42 shape.
    for x, y in blocked:
        left, right, top, bottom, _center_row, _center_col = _cell_bounds(x, y)
        if (x + 1, y) in blocked:
            canvas[top + 1][right] = _BLOCKED
        if (x, y + 1) in blocked:
            _fill_span(canvas, bottom, left, _BLOCKED)
        if (
            (x + 1, y) in blocked
            and (x, y + 1) in blocked
            and (x + 1, y + 1) in blocked
        ):
            canvas[bottom][right] = _BLOCKED

    if active_path_sequence:
        for current, nxt in zip(
            active_path_sequence,
            active_path_sequence[1:],
        ):
            _draw_path_segment(canvas, current, nxt)

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
        elif ch == _DISCOVERED:
            parts.append(f"{_DISCOVERED_COLOR}{ch}{_ANSI_RESET}")
        elif ch == "S":
            parts.append(f"{_START_COLOR}{ch}{_ANSI_RESET}")
        elif ch == "G":
            parts.append(f"{_GOAL_COLOR}{ch}{_ANSI_RESET}")
        elif ch == _PATH and show_path:
            parts.append(f"{_PATH_COLOR}{ch}{_ANSI_RESET}")
        else:
            parts.append(ch)
    return "".join(parts)


def _panel(
    lines: list[str],
    *,
    use_color: bool,
    title: str | None = None,
) -> list[str]:
    """Wrap lines in a light terminal panel."""
    width = max(len(line) for line in lines)
    top = f"┌{'─' * (width + 2)}┐"
    bottom = f"└{'─' * (width + 2)}┘"
    body = [f"│ {line.ljust(width)} │" for line in lines]
    if title:
        title_text = f" {title} "
        top = (
            f"┌{title_text}"
            f"{'─' * max(0, width + 2 - len(title_text))}┐"
        )
    panel_lines = [top, *body, bottom]
    if not use_color:
        return panel_lines
    return [f"{_PANEL_COLOR}{line}{_ANSI_RESET}" for line in panel_lines]


def _render_interactive_maze_lines(
    maze_lines: list[str],
    *,
    palette_index: int,
    use_color: bool,
) -> list[str]:
    """Convert the logical maze into a cleaner single-width terminal view."""
    wall_color = _WALL_COLORS[palette_index % len(_WALL_COLORS)]
    grid = [list(line) for line in maze_lines]

    def junction_glyph(row: int, col: int) -> str:
        """Pick a box-drawing junction from neighboring wall strokes."""
        up = row > 0 and grid[row - 1][col] == _V_WALL
        down = row + 1 < len(grid) and grid[row + 1][col] == _V_WALL
        left = col > 0 and grid[row][col - 1] == _H_WALL
        right = col + 1 < len(grid[row]) and grid[row][col + 1] == _H_WALL
        mapping = {
            (False, True, False, True): "┌",
            (False, True, True, False): "┐",
            (True, False, False, True): "└",
            (True, False, True, False): "┘",
            (True, True, False, False): "│",
            (False, False, True, True): "─",
            (True, True, False, True): "├",
            (True, True, True, False): "┤",
            (False, True, True, True): "┬",
            (True, False, True, True): "┴",
            (True, True, True, True): "┼",
        }
        return mapping.get((up, down, left, right), "·")

    rendered: list[str] = []
    for row_index, line in enumerate(maze_lines):
        parts: list[str] = []
        for col_index, ch in enumerate(line):
            if ch in {_CORNER, _H_WALL, _V_WALL}:
                glyph = (
                    junction_glyph(row_index, col_index)
                    if ch == _CORNER
                    else (
                        "─"
                        if ch == _H_WALL
                        else "│"
                    )
                )
                color = wall_color
            elif ch == _BLOCKED:
                glyph = "▓"
                color = _BLOCKED_COLOR
            elif ch == _DISCOVERED:
                glyph = "·"
                color = _DISCOVERED_COLOR
            elif ch == _PATH:
                glyph = "•"
                color = _PATH_COLOR
            elif ch == "S":
                glyph = "S"
                color = _START_COLOR
            elif ch == "G":
                glyph = "G"
                color = _GOAL_COLOR
            else:
                glyph = ch
                color = ""

            if use_color and color:
                parts.append(f"{color}{glyph}{_ANSI_RESET}")
            else:
                parts.append(glyph)
        rendered.append("".join(parts))
    return rendered


def _interactive_screen(
    cfg: MazeConfig,
    generator: GeneratorLike,
    *,
    show_path: bool,
    path_sequence: list[tuple[int, int]] | None,
    discovered_cells: set[tuple[int, int]] | None,
    palette_index: int,
    status: str,
    use_color: bool,
) -> str:
    """Build the full interactive ASCII screen."""
    maze_lines = build_ascii_lines(
        cfg,
        generator,
        show_path=show_path,
        path_sequence=path_sequence,
        discovered_cells=discovered_cells,
    )
    styled_maze = _render_interactive_maze_lines(
        maze_lines,
        palette_index=palette_index,
        use_color=use_color,
    )

    seed_text = cfg.seed if cfg.seed is not None else "random"
    state_line = (
        f"{cfg.width}x{cfg.height}   {_mode_label(cfg.perfect)}"
        f"   seed {seed_text}"
    )
    progress_mode = "path visible" if show_path else "path hidden"
    progress_mode = "discovering" if discovered_cells else progress_mode
    progress_mode = (
        "tracing route"
        if path_sequence and not show_path
        else progress_mode
    )
    summary_lines = [
        "A-Maze-ing terminal view",
        state_line,
        (
            f"mode {progress_mode}   palette "
            f"{palette_index + 1}/{len(_WALL_COLORS)}"
        ),
    ]
    if use_color:
        summary_lines = [
            f"{_ACCENT_COLOR}{summary_lines[0]}{_ANSI_RESET}",
            f"{_TEXT_COLOR}{summary_lines[1]}{_ANSI_RESET}",
            f"{_MUTED_COLOR}{summary_lines[2]}{_ANSI_RESET}",
        ]

    menu_lines = [
        f"1. {'Hide' if show_path else 'Show'} full path",
        "2. Animate path discovery",
        "3. Re-generate a new maze",
        "4. Animate maze generation",
        "5. Rotate maze colors",
        "6. Quit",
        f"Status: {status}",
        "Choice (1-6): ",
    ]
    if use_color:
        menu_lines = [
            f"{_STATUS_COLOR}{line}{_ANSI_RESET}"
            if line.startswith("Status:")
            else (
                f"{_MUTED_COLOR}{line}{_ANSI_RESET}"
                if line != "Choice (1-6): "
                else f"{_TEXT_COLOR}{line}{_ANSI_RESET}"
            )
            for line in menu_lines
        ]
    summary_panel = _panel(summary_lines, use_color=use_color, title=" MAZE ")
    controls_panel = _panel(
        menu_lines,
        use_color=use_color,
        title=" CONTROLS ",
    )
    return "\n".join([*summary_panel, "", *styled_maze, "", *controls_panel])


def run_ascii_ui(
    cfg: MazeConfig,
    generator: GeneratorLike,
    regenerate: Callable[[Callable[[], None] | None], None] | None = None,
    *,
    generate_delay_ms: int = 8,
    solve_delay_ms: int = 25,
) -> None:
    """Run a simple interactive terminal UI for the ASCII fallback."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        render_ascii(cfg, generator, show_path=False)
        return

    show_path = False
    animated_path: list[tuple[int, int]] | None = None
    discovered_cells: set[tuple[int, int]] | None = None
    palette_index = 0
    status = "Ready"
    use_color = _supports_ansi()

    def _draw(status_text: str) -> None:
        """Render the current screen state."""
        screen = _interactive_screen(
            cfg,
            generator,
            show_path=show_path,
            path_sequence=animated_path,
            discovered_cells=discovered_cells,
            palette_index=palette_index,
            status=status_text,
            use_color=use_color,
        )
        print(f"{_ANSI_CLEAR}{screen}", end="", flush=True)

    def _animate_solve() -> str:
        """Animate the shortest path one cell at a time."""
        nonlocal animated_path, discovered_cells, show_path
        show_path = False
        animated_path = []
        discovered_cells = set()
        try:
            order, sequence = _bfs_discovery(cfg, generator)
            for index in range(1, len(order) + 1):
                discovered_cells = set(order[:index])
                _draw("Discovering reachable paths...")
                time.sleep(solve_delay_ms / 1000)
            for index in range(1, len(sequence) + 1):
                animated_path = sequence[:index]
                _draw("Tracing shortest path...")
                time.sleep(solve_delay_ms / 1000)
        except Exception as exc:  # pragma: no cover - runtime safeguard
            animated_path = None
            discovered_cells = None
            return f"Path animation failed: {exc}"
        animated_path = None
        discovered_cells = None
        show_path = True
        return "Path animation complete"

    def _animate_generation() -> str:
        """Animate maze regeneration by redrawing on generation callbacks."""
        nonlocal animated_path, discovered_cells, show_path
        if regenerate is None:
            return "Regenerate unavailable"
        animated_path = None
        discovered_cells = None
        show_path = False
        frame_counter = 0

        def on_step() -> None:
            """Throttle redraws during maze carving."""
            nonlocal frame_counter
            frame_counter += 1
            if frame_counter % 2 == 0:
                _draw("Animating maze generation...")
                time.sleep(generate_delay_ms / 1000)

        try:
            regenerate(on_step)
        except Exception as exc:  # pragma: no cover - runtime safeguard
            return f"Generation animation failed: {exc}"
        return "Generation animation complete"

    while True:
        _draw(status)

        try:
            choice = input().strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "1":
            animated_path = None
            discovered_cells = None
            show_path = not show_path
            status = f"Path {'enabled' if show_path else 'hidden'}"
            continue
        if choice == "2":
            status = _animate_solve()
            continue
        if choice == "3":
            if regenerate is None:
                status = "Regenerate unavailable"
                continue
            try:
                animated_path = None
                discovered_cells = None
                regenerate(None)
                show_path = False
                status = "Maze regenerated"
            except Exception as exc:  # pragma: no cover - runtime safeguard
                status = f"Regenerate failed: {exc}"
            continue
        if choice == "4":
            status = _animate_generation()
            continue
        if choice == "5":
            animated_path = None
            discovered_cells = None
            palette_index = (palette_index + 1) % len(_WALL_COLORS)
            status = f"Palette {palette_index + 1}/{len(_WALL_COLORS)}"
            continue
        if choice == "6":
            print(_ANSI_CLEAR, end="", flush=True)
            return
        status = "Invalid choice"
