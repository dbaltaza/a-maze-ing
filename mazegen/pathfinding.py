"""Shortest path utilities."""

from __future__ import annotations

from collections import deque

from .maze import DIR_DELTAS, Maze


def bfs_shortest_path(
    maze: Maze,
    blocked: set[tuple[int, int]],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """Return the shortest valid path from start to goal with BFS."""
    if start in blocked or goal in blocked:
        return []

    q: deque[tuple[int, int]] = deque([start])
    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    while q:
        x, y = q.popleft()
        if (x, y) == goal:
            break
        for direction, nx, ny in maze.neighbors(x, y):
            nxt = (nx, ny)
            if nxt in blocked or nxt in prev:
                continue
            if maze.has_wall(x, y, direction):
                continue
            prev[nxt] = (x, y)
            q.append(nxt)

    if goal not in prev:
        return []

    path: list[tuple[int, int]] = []
    cur: tuple[int, int] | None = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def bfs_discovery_path(
    maze: Maze,
    blocked: set[tuple[int, int]],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Return BFS discovery order together with the final shortest path."""
    if start in blocked or goal in blocked:
        return ([], [])

    q: deque[tuple[int, int]] = deque([start])
    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    order: list[tuple[int, int]] = []

    while q:
        x, y = q.popleft()
        current = (x, y)
        order.append(current)
        if current == goal:
            break
        for direction, nx, ny in maze.neighbors(x, y):
            nxt = (nx, ny)
            if nxt in blocked or nxt in prev:
                continue
            if maze.has_wall(x, y, direction):
                continue
            prev[nxt] = current
            q.append(nxt)

    if goal not in prev:
        return (order, [])

    path: list[tuple[int, int]] = []
    cur: tuple[int, int] | None = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return (order, path)


def path_to_moves(path: list[tuple[int, int]]) -> str:
    """Convert a coordinate path into NESW letters."""
    if len(path) < 2:
        return ""

    move_lookup = {
        DIR_DELTAS["N"]: "N",
        DIR_DELTAS["E"]: "E",
        DIR_DELTAS["S"]: "S",
        DIR_DELTAS["W"]: "W",
    }
    moves: list[str] = []
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        delta = (x2 - x1, y2 - y1)
        if delta not in move_lookup:
            raise ValueError(
                f"invalid path step from {(x1, y1)} to {(x2, y2)}"
            )
        moves.append(move_lookup[delta])
    return "".join(moves)
