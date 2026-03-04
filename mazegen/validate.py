"""Validation helpers for structural maze constraints."""

from __future__ import annotations

from collections import deque

from .maze import DIR_BITS, OPPOSITE, Maze


def validate_symmetry(maze: Maze, blocked: set[tuple[int, int]]) -> bool:
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) in blocked:
                continue
            for direction, nx, ny in maze.neighbors(x, y):
                if (nx, ny) in blocked:
                    if not maze.has_wall(x, y, direction):
                        return False
                    continue
                this_has_wall = maze.has_wall(x, y, direction)
                other_has_wall = maze.has_wall(nx, ny, OPPOSITE[direction])
                if this_has_wall != other_has_wall:
                    return False
    return True


def validate_borders(maze: Maze, blocked: set[tuple[int, int]]) -> bool:
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) in blocked:
                continue
            walls = maze.get_cell_walls(x, y)
            if y == 0 and not (walls & DIR_BITS["N"]):
                return False
            if x == maze.width - 1 and not (walls & DIR_BITS["E"]):
                return False
            if y == maze.height - 1 and not (walls & DIR_BITS["S"]):
                return False
            if x == 0 and not (walls & DIR_BITS["W"]):
                return False
    return True


def validate_blocked_closed(maze: Maze, blocked: set[tuple[int, int]]) -> bool:
    return all(maze.get_cell_walls(x, y) == 0xF for (x, y) in blocked)


def _window_all_open(maze: Maze, ox: int, oy: int) -> bool:
    # Horizontal shared walls in a 3x3 window.
    for dy in range(3):
        y = oy + dy
        for dx in range(2):
            x = ox + dx
            if maze.has_wall(x, y, "E"):
                return False
    # Vertical shared walls in a 3x3 window.
    for dy in range(2):
        y = oy + dy
        for dx in range(3):
            x = ox + dx
            if maze.has_wall(x, y, "S"):
                return False
    return True


def validate_open_areas_max2(maze: Maze, blocked: set[tuple[int, int]]) -> bool:
    if maze.width < 3 or maze.height < 3:
        return True
    for oy in range(maze.height - 2):
        for ox in range(maze.width - 2):
            coords = {(ox + dx, oy + dy) for dy in range(3) for dx in range(3)}
            if coords & blocked:
                continue
            if _window_all_open(maze, ox, oy):
                return False
    return True


def _reachable_cells(
    maze: Maze, blocked: set[tuple[int, int]], start: tuple[int, int]
) -> set[tuple[int, int]]:
    q: deque[tuple[int, int]] = deque([start])
    seen: set[tuple[int, int]] = {start}
    while q:
        x, y = q.popleft()
        for direction, nx, ny in maze.neighbors(x, y):
            nxt = (nx, ny)
            if nxt in blocked or nxt in seen:
                continue
            if maze.has_wall(x, y, direction):
                continue
            seen.add(nxt)
            q.append(nxt)
    return seen


def validate_reachability(
    maze: Maze,
    blocked: set[tuple[int, int]],
    entry: tuple[int, int],
    exit: tuple[int, int],
) -> bool:
    if entry in blocked or exit in blocked:
        return False
    seen = _reachable_cells(maze, blocked, entry)
    expected = maze.width * maze.height - len(blocked)
    return len(seen) == expected and exit in seen


def validate_tree_structure(
    maze: Maze, blocked: set[tuple[int, int]], entry: tuple[int, int]
) -> bool:
    seen = _reachable_cells(maze, blocked, entry)
    if len(seen) != (maze.width * maze.height - len(blocked)):
        return False

    edges = 0
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) in blocked:
                continue
            if x + 1 < maze.width and (x + 1, y) not in blocked and not maze.has_wall(
                x, y, "E"
            ):
                edges += 1
            if y + 1 < maze.height and (x, y + 1) not in blocked and not maze.has_wall(
                x, y, "S"
            ):
                edges += 1
    return edges == len(seen) - 1


def validate_all(
    maze: Maze,
    blocked: set[tuple[int, int]],
    entry: tuple[int, int],
    exit: tuple[int, int],
    perfect: bool,
) -> bool:
    checks = [
        validate_symmetry(maze, blocked),
        validate_borders(maze, blocked),
        validate_blocked_closed(maze, blocked),
        validate_open_areas_max2(maze, blocked),
        validate_reachability(maze, blocked, entry, exit),
    ]
    if not all(checks):
        return False
    if perfect:
        return validate_tree_structure(maze, blocked, entry)
    return True
