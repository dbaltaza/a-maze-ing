"""Tk helper for the AA-style visual renderer."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.writer import write_output
from mazegen import MazeGenerator

WHITE = "#ffffff"
GREEN = "#00ff00"
RED = "#ff0000"
BLUE = "#0000ff"
BLACK = "#000000"
CELL_SIZE = 20
INNER_SIZE = 18
INNER_OFFSET = 1


@dataclass(frozen=True)
class VisualConfig:
    width: int
    height: int
    entry: tuple[int, int]
    exit: tuple[int, int]
    output_file: str
    perfect: bool
    seed: int | None
    renderer: str
    algorithm: str
    density: int


class VisualizeMaze:
    """Render the maze with the AA look and interaction model."""

    def __init__(
        self,
        cfg: VisualConfig,
        grid: list[list[int]],
        solution: list[tuple[int, int]],
    ) -> None:
        self.cfg = cfg
        self.grid = grid
        self.solution = solution
        self.width = cfg.width
        self.height = cfg.height
        self.play = False
        self.player = cfg.entry
        self.red = 2
        self.green = 2
        self.blue = 2
        self.wall_color = WHITE
        self.show_sol = False

        self.root = tk.Tk()
        self.root.title("A-Maze-ing")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(
            self.root,
            width=self.width * CELL_SIZE,
            height=self.height * CELL_SIZE,
            bg=BLACK,
            highlightthickness=0,
        )
        self.canvas.pack()
        self.root.bind("<KeyPress>", self.key_hook)
        self.root.protocol("WM_DELETE_WINDOW", self.close_mlx)

    def draw_maze(self) -> None:
        self.canvas.delete("all")
        for y in range(self.height):
            for x in range(self.width):
                self._draw_tile(x, y, self.grid[y][x])

        self._draw_fill(self.cfg.entry, GREEN)
        self._draw_fill(self.cfg.exit, RED)

        if self.show_sol:
            self.draw_solution()
        if self.play:
            self._draw_fill(self.player, GREEN)

        self.root.update_idletasks()

    def _draw_tile(self, x: int, y: int, tile_type: int) -> None:
        x0 = x * CELL_SIZE
        y0 = y * CELL_SIZE
        x1 = x0 + CELL_SIZE
        y1 = y0 + CELL_SIZE
        if tile_type == 15:
            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=self.wall_color,
                outline=self.wall_color,
                width=0,
            )
            return

        self.canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill=BLACK,
            outline=BLACK,
            width=0,
        )
        if tile_type & 1:
            self.canvas.create_line(x0, y0, x1, y0, fill=self.wall_color)
        if tile_type & 2:
            self.canvas.create_line(x1 - 1, y0, x1 - 1, y1, fill=self.wall_color)
        if tile_type & 4:
            self.canvas.create_line(x0, y1 - 1, x1, y1 - 1, fill=self.wall_color)
        if tile_type & 8:
            self.canvas.create_line(x0, y0, x0, y1, fill=self.wall_color)

    def _draw_fill(self, coord: tuple[int, int], color: str) -> None:
        x, y = coord
        x0 = x * CELL_SIZE + INNER_OFFSET
        y0 = y * CELL_SIZE + INNER_OFFSET
        x1 = x0 + INNER_SIZE
        y1 = y0 + INNER_SIZE
        self.canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill=color,
            outline=color,
            width=0,
        )

    def key_hook(self, event: tk.Event[tk.Misc]) -> None:
        key = event.keysym.lower()
        if key == "escape":
            self.close_mlx()
        if key == "1":
            self.regenerate()
        if key == "2":
            self.play = False
            self.show_sol = not self.show_sol
            self.draw_maze()
        if key == "p":
            self.show_sol = False
            self.player = self.cfg.entry
            self.play = not self.play
            if not self.play:
                print("GAME MODE: OFF")
            else:
                print("GAME MODE: ON")
            self.draw_maze()
        if key in {"w", "up"} and self.play:
            self.move_player((0, -1))
        if key in {"a", "left"} and self.play:
            self.move_player((-1, 0))
        if key in {"s", "down"} and self.play:
            self.move_player((0, 1))
        if key in {"d", "right"} and self.play:
            self.move_player((1, 0))
        if key in {"r", "g", "b"}:
            self.play = False
            self.rotate_colors(key)

    def regenerate(self) -> None:
        generator = MazeGenerator(
            width=self.cfg.width,
            height=self.cfg.height,
            entry=self.cfg.entry,
            exit=self.cfg.exit,
            perfect=self.cfg.perfect,
            seed=self.cfg.seed,
        )
        generator.generate()
        self.grid = _decode_hex_lines(generator.to_hex_lines())
        self.solution = generator.solve_shortest()
        self.show_sol = False
        self.play = False
        self.player = self.cfg.entry
        write_output(self.cfg.output_file, self.cfg, generator)
        print(f"Maze successfully saved to {self.cfg.output_file}")
        self.draw_maze()

    def move_player(self, direction: tuple[int, int]) -> None:
        x, y = self.player
        walls = self.grid[y][x]
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        if walls & (1 << directions.index(direction)):
            return
        self.player = (x + direction[0], y + direction[1])
        if self.player == self.cfg.exit:
            self.play = False
            self.draw_maze()
            print("WINNER!")
            return
        self.draw_maze()

    def rotate_colors(self, key: str) -> None:
        if key == "r":
            self.red = (self.red - 1) % 3
        elif key == "g":
            self.green = (self.green - 1) % 3
        elif key == "b":
            self.blue = (self.blue - 1) % 3
        color = 127 * self.red * 2**16 + 127 * self.green * 2**8 + 127 * self.blue
        self.wall_color = f"#{color:06x}"
        self.draw_maze()

    def draw_solution(self) -> None:
        for coord in self.solution[1:-1]:
            self._draw_fill(coord, BLUE)

    def close_mlx(self) -> None:
        self.root.destroy()


def _decode_hex_lines(lines: list[str]) -> list[list[int]]:
    return [[int(cell, 16) for cell in row] for row in lines]


def _load_payload(path: str) -> tuple[VisualConfig, list[list[int]], list[tuple[int, int]]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg_data = payload["cfg"]
    cfg = VisualConfig(
        width=cfg_data["width"],
        height=cfg_data["height"],
        entry=tuple(cfg_data["entry"]),
        exit=tuple(cfg_data["exit"]),
        output_file=cfg_data["output_file"],
        perfect=cfg_data["perfect"],
        seed=cfg_data["seed"],
        renderer=cfg_data["renderer"],
        algorithm=cfg_data["algorithm"],
        density=cfg_data["density"],
    )
    grid = _decode_hex_lines(payload["maze"]["hex_lines"])
    solution = [tuple(cell) for cell in payload["maze"]["solution"]]
    return cfg, grid, solution


def main(argv: list[str] | None = None) -> int:
    args = sys.argv if argv is None else argv
    if len(args) != 2:
        print("Usage: python renderer_mlx_tk.py <payload.json>", file=sys.stderr)
        return 2
    cfg, grid, solution = _load_payload(args[1])
    vis = VisualizeMaze(cfg, grid, solution)
    vis.draw_maze()
    print("MLX KEY INSTRUCTIONS:")
    print(" - 1: generate new maze")
    print(" - 2: show / hide solution")
    print(" - p: activate / deactivate play mode")
    print(" - wasd / arrows: move (only in play mode)")
    print(" - rgb: change wall colours")
    print(" - esc: close window")
    vis.root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
