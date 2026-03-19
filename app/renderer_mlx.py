"""Legacy MLX renderer ported from the AA implementation."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

try:
    from mlx import Mlx
except ImportError:
    mlx_src = (
        Path(__file__).resolve().parents[1]
        / "AA"
        / "mlx_CLXV"
        / "python"
        / "src"
    )
    if mlx_src.exists() and str(mlx_src) not in sys.path:
        sys.path.insert(0, str(mlx_src))
    try:
        from mlx import Mlx
    except ImportError as exc:
        raise RuntimeError(
            "MLX renderer requested but Python module 'mlx' is not available. "
            "Install the MLX Python bindings or set RENDERER=ascii."
        ) from exc

from app.parser import MazeConfig
from app.writer import write_output
from mazegen import MazeGenerator

WHITE = 0xFFFFFF
GREEN = 0x00FF00
RED = 0xFF0000
BLUE = 0x0000FF
BLACK = 0x000000
KESC = 65307
KUP = 65362
KDOWN = 65364
KRIGHT = 65363
KLEFT = 65361
KA = 97
KB = 98
KD = 100
KG = 103
KP = 112
KR = 114
KS = 115
KW = 119
K1 = 49
K2 = 50


class VisualizeMaze:
    """Render the maze and handle keyboard interaction through MLX."""

    def __init__(self, maze: MazeGenerator, cfg: MazeConfig) -> None:
        self.motor = Mlx()
        self.ptr = self.motor.mlx_init()
        self.window = self.motor.mlx_new_window(
            self.ptr,
            maze.width * 20,
            maze.height * 20,
            "A-Maze-ing",
        )
        self.color = WHITE
        self.width = maze.width
        self.height = maze.height
        self.play = False
        self.maze = maze
        self.cfg = cfg
        self.player = maze.entry
        self.red = 2
        self.green = 2
        self.blue = 2
        self.show_sol = False
        self.error = False
        self.create_images()

    def create_images(self) -> None:
        """Generate the cached tile sprites."""
        self.images = [self.new_image(i) for i in range(16)]
        self.images.append(self.full_square(GREEN))
        self.images.append(self.full_square(RED))
        self.images.append(self.full_square(BLACK))
        self.images.append(self.full_square(BLUE))

    def full_square(self, color: int) -> Any:
        """Create one solid 18x18 cell fill image."""
        image = self.motor.mlx_new_image(self.ptr, 18, 18)
        img_mem, _bpp, size_line, _fmt = self.motor.mlx_get_data_addr(image)
        for x in range(18):
            for y in range(18):
                self.put_pixel(img_mem, x, y, color, size_line)
        return image

    def new_image(self, tile_type: int) -> Any:
        """Create one wall tile matching the AA visuals."""
        image = self.motor.mlx_new_image(self.ptr, 20, 20)
        img_mem, _bpp, size_line, _fmt = self.motor.mlx_get_data_addr(image)
        if tile_type == 15:
            for x in range(20):
                for y in range(20):
                    self.put_pixel(img_mem, x, y, self.color, size_line)
            return image
        for x in range(20):
            for y in range(20):
                self.put_pixel(img_mem, x, y, BLACK, size_line)
        if tile_type & 1:
            for x in range(20):
                self.put_pixel(img_mem, x, 0, self.color, size_line)
        if tile_type & 2:
            for y in range(20):
                self.put_pixel(img_mem, 19, y, self.color, size_line)
        if tile_type & 4:
            for x in range(20):
                self.put_pixel(img_mem, x, 19, self.color, size_line)
        if tile_type & 8:
            for y in range(20):
                self.put_pixel(img_mem, 0, y, self.color, size_line)
        return image

    @staticmethod
    def put_pixel(
        addr: memoryview,
        x: int,
        y: int,
        color: int,
        size_line: int,
    ) -> None:
        """Write one pixel into the MLX image buffer."""
        offset = y * size_line + x * 4
        addr[offset + 0] = color & 0xFF
        addr[offset + 1] = (color >> 8) & 0xFF
        addr[offset + 2] = (color >> 16) & 0xFF
        addr[offset + 3] = 0xFF

    def draw_maze(self) -> None:
        """Render the full maze, entry, exit, and optional solution path."""
        self.motor.mlx_clear_window(self.ptr, self.window)
        for y in range(self.height):
            for x in range(self.width):
                self.motor.mlx_put_image_to_window(
                    self.ptr,
                    self.window,
                    self.images[self.maze.get_cell_walls(x, y)],
                    20 * x,
                    20 * y,
                )
        self.motor.mlx_put_image_to_window(
            self.ptr,
            self.window,
            self.images[16],
            20 * self.maze.entry[0] + 1,
            20 * self.maze.entry[1] + 1,
        )
        self.motor.mlx_put_image_to_window(
            self.ptr,
            self.window,
            self.images[17],
            20 * self.maze.exit[0] + 1,
            20 * self.maze.exit[1] + 1,
        )
        if self.show_sol:
            self.draw_solution()
        self.motor.mlx_do_sync(self.ptr)

    def key_hook(self, key: int, _param: None) -> None:
        """Apply the legacy control scheme."""
        if key == KESC:
            self.close_mlx()
        if key == K1:
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
        if key == K2:
            self.play = False
            self.show_sol = not self.show_sol
            self.draw_maze()
        if key == KP:
            self.show_sol = False
            self.player = self.maze.entry
            self.play = not self.play
            if not self.play:
                print("GAME MODE: OFF")
                self.draw_maze()
            else:
                print("GAME MODE: ON")
        if (key == KW or key == KUP) and self.play:
            self.move_player((0, -1))
        if (key == KA or key == KLEFT) and self.play:
            self.move_player((-1, 0))
        if (key == KS or key == KDOWN) and self.play:
            self.move_player((0, 1))
        if (key == KD or key == KRIGHT) and self.play:
            self.move_player((1, 0))
        if key == KR or key == KG or key == KB:
            self.play = False
            self.rotate_colors(key)

    def move_player(self, direction: tuple[int, int]) -> None:
        """Move the player if the target wall is open."""
        x, y = self.player
        walls = self.maze.get_cell_walls(x, y)
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        if walls & (1 << directions.index(direction)):
            return
        self.motor.mlx_put_image_to_window(
            self.ptr,
            self.window,
            self.images[18],
            20 * x + 1,
            20 * y + 1,
        )
        self.player = (x + direction[0], y + direction[1])
        if self.player == self.maze.exit:
            self.play = False
            self.draw_maze()
            print("WINNER!")
            return
        self.motor.mlx_put_image_to_window(
            self.ptr,
            self.window,
            self.images[16],
            20 * self.player[0] + 1,
            20 * self.player[1] + 1,
        )
        self.motor.mlx_do_sync(self.ptr)

    def rotate_colors(self, key: int) -> None:
        """Cycle wall colors exactly like the AA renderer."""
        if key == KR:
            self.red = (self.red - 1) % 3
        elif key == KG:
            self.green = (self.green - 1) % 3
        elif key == KB:
            self.blue = (self.blue - 1) % 3
        self.color = (
            127 * self.red * 2**16 + 127 * self.green * 2**8 + 127 * self.blue
        )
        self.create_images()
        self.draw_maze()

    def draw_solution(self) -> None:
        """Overlay the solution path using blue interior blocks."""
        for x, y in self.maze.solve_shortest()[1:-1]:
            self.motor.mlx_put_image_to_window(
                self.ptr,
                self.window,
                self.images[19],
                20 * x + 1,
                20 * y + 1,
            )

    def close_mlx(self, *_args: object) -> None:
        """Release the MLX window and display context."""
        self.motor.mlx_destroy_window(self.ptr, self.window)
        self.motor.mlx_release(self.ptr)

    def save_maze_to_file_mlx(self) -> None:
        """Persist the current maze after an in-window regeneration."""
        try:
            write_output(self.cfg.output_file, self.cfg, self.maze)
            print(f"Maze successfully saved to {self.cfg.output_file}")
        except (OSError, ValueError) as exc:
            print(f"Error writing output file: {exc}", file=sys.stderr)
            self.error = True
            self.close_mlx()


def draw_mlx_maze(maze: MazeGenerator, cfg: MazeConfig) -> None:
    """Start the MLX window with the AA key bindings and visuals."""
    vis = VisualizeMaze(maze, cfg)
    vis.draw_maze()
    print("MLX KEY INSTRUCTIONS:")
    print(" - 1: generate new maze")
    print(" - 2: show / hide solution")
    print(" - p: activate / deactivate play mode")
    print(" - wasd / arrows: move (only in play mode)")
    print(" - rgb: change wall colours")
    print(" - esc: close window")
    vis.motor.mlx_hook(vis.window, 33, 0, VisualizeMaze.close_mlx, vis)
    vis.motor.mlx_key_hook(vis.window, vis.key_hook, None)
    vis.motor.mlx_loop(vis.ptr)
    if vis.error:
        raise SystemExit(1)
