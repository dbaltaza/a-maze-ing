# Dev A — Core Engine & Packaging (mazegen-*)

You own the **reusable generator module** that must be installable as a `mazegen-*` wheel/tarball, deterministic, and correct.

---

## Your scope (you own these files)
- `mazegen/**`
- `pyproject.toml` (packaging metadata)
- Any core-domain docs inside `mazegen/` (docstrings)

**Avoid editing**: `app/**`, UI renderers, `a_maze_ing.py` (unless coordinating).

---

## Interface contract (MUST MATCH)
Dev B will build UI + writer assuming this public API exists.

### `mazegen/generator.py`
Expose:

```python
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
```

**Wall encoding:** per cell bitmask:
- N = 1, E = 2, S = 4, W = 8  
Hex digit per cell = 0..15 (`0`..`F`).

---

## Core requirements you must satisfy
1. **Walls are coherent**: opening a wall updates both adjacent cells.
2. **Borders have walls** (no “holes” to outside).
3. **42 pattern**: a deterministic set of cells are **fully closed** and visible in rendering.
4. **Perfect mode**: exactly one path between any two reachable cells (use DFS backtracker spanning tree).
5. **Non-perfect mode**: add loops (open extra walls) without breaking constraints.
6. **No open areas wider than 2 cells**:
   - Use a validator (e.g., scan 3×3 windows)
   - For `perfect=True`, prefer **regenerate loop** if invalid.
7. **Shortest path** from entry to exit using BFS.
8. **Determinism**: same seed/config => same maze.

---

## Suggested internal architecture (inside `mazegen/`)
- `maze.py`: `Maze` model + wall ops + 42 stamping
- `algorithms.py`: DFS carve + loop injection
- `validate.py`: symmetry + border + open-area checks
- `pathfinding.py`: BFS + move string
- `io.py`: hex serialization (optional; can be in generator)

Keep UI concerns OUT of here.

---

## Step-by-step work order (recommended)
1. **Maze model**
   - grid: `walls[y][x]` integer bitmask
   - `open_wall((x,y), dir)` and `neighbor_dir` helpers
2. **42 stamp**
   - center placement if fits; else raise/flag “too small”
3. **Perfect generator**
   - iterative DFS with stack
   - skip blocked cells
4. **Validator suite**
   - neighbor symmetry
   - border walls
   - open-area (3×3 test)
5. **Generate loop**
   - `while True: carve; if validate: break`
6. **Non-perfect**
   - open random walls to add cycles
7. **BFS shortest + path_moves**
8. **`to_hex_lines()`**
9. **Packaging**
   - `pyproject.toml` defines package name `mazegen-*`
   - `__init__.py` exports `MazeGenerator`

---

## Local verification commands
From repo root:
- `python3 -c "from mazegen import MazeGenerator; g=MazeGenerator(20,10,(0,0),(19,9),seed=1); g.generate(); print('\n'.join(g.to_hex_lines())); print(g.path_moves())"`
- `python3 -m pip wheel . -w dist`
- `python3 -m pip install dist/mazegen-*.whl --force-reinstall`

---

## Handoff checklist to Dev B
Before merging:
- [ ] API signatures match contract
- [ ] `to_hex_lines()` outputs exactly `height` lines, each `width` hex chars
- [ ] `blocked_cells` contains 42 pattern coords
- [ ] BFS path exists (unless impossible, but entry/exit should be reachable in valid configs)
- [ ] Validation prevents open areas > 2
- [ ] Packaging builds

---

## Notes to avoid merge pain
- Keep all new code under `mazegen/`
- If you need a new API method, **tell Dev B first** and update contract together.
