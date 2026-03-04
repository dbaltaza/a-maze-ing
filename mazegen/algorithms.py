"""Maze carving algorithms."""

from __future__ import annotations

import random

from .maze import Maze


def generate_perfect_dfs(
    maze: Maze,
    rng: random.Random,
    blocked: set[tuple[int, int]],
    start: tuple[int, int],
) -> None:
    """Generate a spanning tree over all non-blocked cells using DFS backtracking."""
    if start in blocked:
        raise ValueError("start cannot be blocked")

    visited: set[tuple[int, int]] = {start}
    stack: list[tuple[int, int]] = [start]

    while stack:
        x, y = stack[-1]
        candidates: list[tuple[str, int, int]] = []
        for direction, nx, ny in maze.neighbors(x, y):
            nxt = (nx, ny)
            if nxt in blocked or nxt in visited:
                continue
            candidates.append((direction, nx, ny))

        if not candidates:
            stack.pop()
            continue

        direction, nx, ny = rng.choice(candidates)
        maze.open_wall((x, y), direction)
        visited.add((nx, ny))
        stack.append((nx, ny))

    expected = maze.width * maze.height - len(blocked)
    if len(visited) != expected:
        raise RuntimeError("blocked layout disconnected the maze graph")


def add_loops(
    maze: Maze,
    rng: random.Random,
    blocked: set[tuple[int, int]],
    ratio: float = 0.10,
) -> None:
    """Open extra closed internal walls to create cycles."""
    candidates: list[tuple[tuple[int, int], str]] = []
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) in blocked:
                continue
            for direction in ("E", "S"):
                nx, ny = maze.neighbor(x, y, direction)
                if not maze.in_bounds(nx, ny):
                    continue
                if (nx, ny) in blocked:
                    continue
                if maze.has_wall(x, y, direction):
                    candidates.append(((x, y), direction))

    if not candidates:
        return

    rng.shuffle(candidates)
    open_count = max(1, int(len(candidates) * ratio))
    for (cell, direction) in candidates[:open_count]:
        maze.open_wall(cell, direction)
