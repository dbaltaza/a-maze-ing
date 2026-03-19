"""AA-style visual renderer with the same config contract and controls."""

from __future__ import annotations

import tkinter as tk

from app.parser import MazeConfig
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


class VisualizeMaze:
    """Render the maze with the AA look and interaction model."""

    def __init__(self, maze: MazeGenerator, cfg: MazeConfig) -> None:
        self.maze = maze
        self.cfg = cfg
        self.width = maze.width
        self.height = maze.height
        self.play = False
        self.player = maze.entry
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
        """Redraw the full maze using the AA tile geometry."""
        self.canvas.delete("all")
        for y in range(self.height):
            for x in range(self.width):
                self._draw_tile(x, y, self.maze.get_cell_walls(x, y))

        self._draw_fill(self.maze.entry, GREEN)
        self._draw_fill(self.maze.exit, RED)

        if self.show_sol:
            self.draw_solution()
        if self.play:
            self._draw_fill(self.player, GREEN)

        self.root.update_idletasks()

    def _draw_tile(self, x: int, y: int, tile_type: int) -> None:
        """Draw one cell in the same visual style as AA."""
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
        """Draw one 18x18 interior block."""
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
        """Handle the AA key bindings."""
        key = event.keysym.lower()
        if key == "escape":
            self.close_mlx()
        if key == "1":
            maze = MazeGenerator(
                width=self.cfg.width,
                height=self.cfg.height,
                entry=self.cfg.entry,
                exit=self.cfg.exit,
                perfect=self.cfg.perfect,
                seed=self.cfg.seed,
            )
            maze.generate()
            self.maze = maze
            self.show_sol = False
            self.play = False
            self.player = maze.entry
            self.draw_maze()
            self.save_maze_to_file_mlx()
        if key == "2":
            self.play = False
            self.show_sol = not self.show_sol
            self.draw_maze()
        if key == "p":
            self.show_sol = False
            self.player = self.maze.entry
            self.play = not self.play
            if not self.play:
                print("GAME MODE: OFF")
                self.draw_maze()
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

    def move_player(self, direction: tuple[int, int]) -> None:
        """Move the player when the corresponding wall bit is open."""
        x, y = self.player
        walls = self.maze.get_cell_walls(x, y)
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        if walls & (1 << directions.index(direction)):
            return
        self.player = (x + direction[0], y + direction[1])
        if self.player == self.maze.exit:
            self.play = False
            self.draw_maze()
            print("WINNER!")
            return
        self.draw_maze()

    def rotate_colors(self, key: str) -> None:
        """Cycle wall colors exactly like the AA renderer."""
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
        """Overlay the path in blue blocks, excluding entry and exit."""
        for coord in self.maze.solve_shortest()[1:-1]:
            self._draw_fill(coord, BLUE)

    def close_mlx(self) -> None:
        """Close the window."""
        self.root.destroy()

    def save_maze_to_file_mlx(self) -> None:
        """Persist the current maze after in-window regeneration."""
        write_output(self.cfg.output_file, self.cfg, self.maze)
        print(f"Maze successfully saved to {self.cfg.output_file}")


def draw_mlx_maze(maze: MazeGenerator, cfg: MazeConfig) -> None:
    """Launch the AA-style visual renderer."""
    vis = VisualizeMaze(maze, cfg)
    vis.draw_maze()
    print("MLX KEY INSTRUCTIONS:")
    print(" - 1: generate new maze")
    print(" - 2: show / hide solution")
    print(" - p: activate / deactivate play mode")
    print(" - wasd / arrows: move (only in play mode)")
    print(" - rgb: change wall colours")
    print(" - esc: close window")
    vis.root.mainloop()
