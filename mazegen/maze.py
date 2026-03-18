"""Core maze data model and immutable directional definitions."""

from __future__ import annotations

from dataclasses import dataclass

N = 1
E = 2
S = 4
W = 8

DIR_BITS: dict[str, int] = {"N": N, "E": E, "S": S, "W": W}
DIR_DELTAS: dict[str, tuple[int, int]] = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}
OPPOSITE: dict[str, str] = {"N": "S", "E": "W", "S": "N", "W": "E"}


@dataclass(frozen=True)
class Cell:
    """Coordinate holder for one maze cell."""

    x: int
    y: int


class Maze:
    """Grid of per-cell wall bitmasks.

    Each cell starts fully closed (`0b1111`, hex `F`) and passages are carved
    by clearing wall bits in adjacent cells.
    """

    def __init__(self, width: int, height: int) -> None:
        """Create a fully closed maze grid."""
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be > 0")
        self.width = width
        self.height = height
        self.walls: list[list[int]] = [
            [0xF for _ in range(width)] for _ in range(height)
        ]

    def in_bounds(self, x: int, y: int) -> bool:
        """Return whether a coordinate lies inside the maze."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_cell_walls(self, x: int, y: int) -> int:
        """Return one cell wall bitmask."""
        if not self.in_bounds(x, y):
            raise IndexError(f"cell out of bounds: {(x, y)}")
        return self.walls[y][x]

    def has_wall(self, x: int, y: int, direction: str) -> bool:
        """Return whether one wall is still closed."""
        return bool(self.get_cell_walls(x, y) & DIR_BITS[direction])

    def neighbor(self, x: int, y: int, direction: str) -> tuple[int, int]:
        """Return the adjacent coordinate in one cardinal direction."""
        dx, dy = DIR_DELTAS[direction]
        return x + dx, y + dy

    def open_wall(self, cell: tuple[int, int], direction: str) -> None:
        """Open one wall and mirror the opening in the adjacent cell."""
        x, y = cell
        if direction not in DIR_BITS:
            raise ValueError(f"invalid direction: {direction}")
        if not self.in_bounds(x, y):
            raise IndexError(f"cell out of bounds: {(x, y)}")

        nx, ny = self.neighbor(x, y, direction)
        if not self.in_bounds(nx, ny):
            raise ValueError(
                f"cannot open border wall toward {direction} at {(x, y)}"
            )

        self.walls[y][x] &= ~DIR_BITS[direction]
        self.walls[ny][nx] &= ~DIR_BITS[OPPOSITE[direction]]

    def neighbors(self, x: int, y: int) -> list[tuple[str, int, int]]:
        """Return all in-bounds neighboring cells with directions."""
        items: list[tuple[str, int, int]] = []
        for direction, (dx, dy) in DIR_DELTAS.items():
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                items.append((direction, nx, ny))
        return items

    def stamp_42(
        self,
        forbidden: set[tuple[int, int]] | None = None,
    ) -> set[tuple[int, int]]:
        """Return deterministic blocked cells for a centered 42 glyph."""
        forbidden = forbidden or set()
        glyph = [
            "X...XXX",
            "X.....X",
            "XXX.XXX",
            "..X.X..",
            "..X.XXX",
        ]
        glyph_h = len(glyph)
        glyph_w = len(glyph[0])
        if self.width < glyph_w or self.height < glyph_h:
            raise ValueError(
                "maze too small for 42 stamp, "
                f"need at least {glyph_w}x{glyph_h}"
            )

        ox = (self.width - glyph_w) // 2
        oy = (self.height - glyph_h) // 2
        blocked: set[tuple[int, int]] = set()
        for gy, row in enumerate(glyph):
            for gx, marker in enumerate(row):
                if marker != "X":
                    continue
                coord = (ox + gx, oy + gy)
                if coord in forbidden:
                    raise ValueError(
                        "entry/exit intersects required 42 blocked cells"
                    )
                blocked.add(coord)
        return blocked
