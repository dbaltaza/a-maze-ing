"""Public generator facade used by the app layer."""

from __future__ import annotations

import random
from typing import Callable

from .algorithms import add_loops, generate_perfect_dfs
from .maze import Maze
from .pathfinding import bfs_shortest_path, path_to_moves
from .validate import validate_all


class MazeGenerator:
    def __init__(
        self,
        width: int,
        height: int,
        entry: tuple[int, int],
        exit: tuple[int, int],
        perfect: bool = True,
        seed: int | None = None,
        algo: str = "dfs",
    ) -> None:
        if not isinstance(width, int) or not isinstance(height, int):
            raise TypeError("width and height must be integers")
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be > 0")

        self._validate_point("entry", entry, width, height)
        self._validate_point("exit", exit, width, height)
        if entry == exit:
            raise ValueError("entry and exit must be different")
        if algo.lower() != "dfs":
            raise ValueError("only 'dfs' is supported")

        self._width = width
        self._height = height
        self._entry = entry
        self._exit = exit
        self._perfect = perfect
        self._seed = seed
        self._algo = algo.lower()
        self._maze: Maze | None = None
        self._blocked: set[tuple[int, int]] = set()
        self._shortest_path: list[tuple[int, int]] | None = None

    @staticmethod
    def _validate_point(name: str, p: tuple[int, int], width: int, height: int) -> None:
        if not isinstance(p, tuple) or len(p) != 2:
            raise TypeError(f"{name} must be a tuple like (x, y)")
        x, y = p
        if not isinstance(x, int) or not isinstance(y, int):
            raise TypeError(f"{name} coordinates must be integers")
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"{name} out of bounds: {p} for maze {width}x{height}")

    def _ensure_generated(self) -> Maze:
        if self._maze is None:
            raise RuntimeError("maze not generated yet; call generate() first")
        return self._maze

    def generate(self) -> None:
        self.generate_with_callback()

    def generate_with_callback(
        self,
        on_step: Callable[[], None] | None = None,
        *,
        step_stride: int = 1,
    ) -> None:
        if self._algo != "dfs":
            raise ValueError(f"unsupported algo: {self._algo}")
        if step_stride <= 0:
            raise ValueError("step_stride must be > 0")

        rng = random.Random(self._seed)
        self._shortest_path = None

        max_attempts = 1000
        for _ in range(max_attempts):
            maze = Maze(self._width, self._height)
            try:
                blocked = maze.stamp_42(forbidden={self._entry, self._exit})
            except ValueError as exc:
                if "too small for 42 stamp" in str(exc):
                    blocked = set()
                else:
                    raise

            self._maze = maze
            self._blocked = blocked

            step_count = 0

            def step_callback() -> None:
                nonlocal step_count
                step_count += 1
                if on_step is None:
                    return
                if step_count % step_stride == 0:
                    on_step()

            generate_perfect_dfs(
                maze,
                rng,
                blocked,
                start=self._entry,
                on_carve=step_callback,
            )
            if not self._perfect:
                add_loops(maze, rng, blocked, on_open=step_callback)

            if on_step is not None:
                on_step()

            if validate_all(
                maze=maze,
                blocked=blocked,
                entry=self._entry,
                exit=self._exit,
                perfect=self._perfect,
            ):
                self._maze = maze
                self._blocked = blocked
                return

        raise RuntimeError("could not generate a valid maze after retries")

    def solve_shortest(self) -> list[tuple[int, int]]:
        maze = self._ensure_generated()
        if self._shortest_path is None:
            self._shortest_path = bfs_shortest_path(
                maze, self._blocked, self._entry, self._exit
            )
        return list(self._shortest_path)

    def path_moves(self) -> str:
        return path_to_moves(self.solve_shortest())

    def to_hex_lines(self) -> list[str]:
        maze = self._ensure_generated()
        lines: list[str] = []
        for y in range(self._height):
            line = "".join(f"{maze.get_cell_walls(x, y):X}" for x in range(self._width))
            lines.append(line)
        return lines

    def get_cell_walls(self, x: int, y: int) -> int:
        maze = self._ensure_generated()
        if not (0 <= x < self._width and 0 <= y < self._height):
            raise ValueError(f"cell out of bounds: {(x, y)}")
        return maze.get_cell_walls(x, y)

    @property
    def blocked_cells(self) -> set[tuple[int, int]]:
        self._ensure_generated()
        return set(self._blocked)
