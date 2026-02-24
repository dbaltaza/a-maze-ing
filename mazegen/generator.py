
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
    ): ...

    def generate(self) -> None: ...

    def solve_shortest(self) -> list[tuple[int, int]]: ...
    def path_moves(self) -> str: ...

    def to_hex_lines(self) -> list[str]: ...

    def get_cell_walls(self, x: int, y: int) -> int: ...

    @property
    def blocked_cells(self) -> set[tuple[int,int]]: ...