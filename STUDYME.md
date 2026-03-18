# STUDYME: A-Maze-ing Deep Project Study

## 1) Project Mission and Why This Code Exists

The objective of this project is not just to draw a maze, but to deliver a **complete maze system**:

- read strict configuration input
- generate valid mazes with deterministic behavior when requested
- enforce structural constraints (including subject-specific ones like the `42` mask and open-area limits)
- solve the maze with shortest-path guarantees
- export in a machine-checkable format
- visualize interactively in terminal, with graceful fallback

In practical terms:  
"We needed a reliable maze engine plus a user-facing app, so we split responsibilities into `mazegen/` (domain logic) and `app/` (I/O, rendering, orchestration)."

---

## 2) End-to-End Thought Process (How to Solve This Project From Zero)

If building this project from scratch, this is the correct engineering sequence:

1. Define the **maze model** (cell walls, directions, coordinate rules).
2. Implement **safe mutation primitives** (open wall, check bounds, neighbors).
3. Implement **generation algorithm** for guaranteed reachability (DFS backtracking).
4. Add **optional loops** for imperfect mode.
5. Implement **validators** to enforce all structural guarantees.
6. Implement **pathfinding** (BFS) to guarantee shortest path.
7. Wrap engine into a **facade API** (`MazeGenerator`) with generation/solve/export.
8. Build **config parser** with strict validation and clear errors.
9. Build **output writer** for required file format.
10. Build **renderers** (curses + ASCII fallback).
11. Create **entrypoint orchestration** (`a_maze_ing.py`) to glue everything.
12. Add **tests** for parser/generator regressions and edge cases.
13. Add **packaging/build backend** to make the engine reusable.

This repo follows exactly that order conceptually.

---

## 3) High-Level Architecture

### `mazegen/` (Domain Layer)
- Pure maze logic, reusable as library.
- No terminal/config concerns.
- Contains model, algorithms, validation, pathfinding, and generator facade.

### `app/` (Application Layer)
- Reads config.
- Renders maze.
- Writes output file.
- Exposes app-specific errors.

### `a_maze_ing.py` (Orchestration Layer)
- Creates objects in the right order.
- handles runtime errors.
- chooses renderer mode and fallback behavior.

Why this matters: each layer can evolve independently without breaking the entire app.

---

## 4) Core Data Model (`mazegen/maze.py`)

### Direction bit model

- `N=1`, `E=2`, `S=4`, `W=8`
- Each cell starts at `0xF` (all walls closed).
- Opening a passage clears bits with bitwise operations.

Why: wall-bit encoding is compact, deterministic, and directly exportable to hex.

### Constants

- `DIR_BITS`: maps `"N"|"E"|"S"|"W"` to bit flags.
- `DIR_DELTAS`: maps direction to coordinate delta.
- `OPPOSITE`: opposite direction lookup for mirrored opening.

Why: centralized direction metadata avoids duplicated logic and bugs.

### `Cell` dataclass

- Immutable coordinate holder (`@dataclass(frozen=True)`).
- Not heavily used, but documents intended coordinate semantics.

### `Maze` class methods and purpose

- `__init__(width, height)`: creates full-closed grid, validates positive dimensions.
- `in_bounds(x, y)`: boundary guard used everywhere.
- `get_cell_walls(x, y)`: safe wall access with bounds check.
- `has_wall(x, y, direction)`: semantic read helper.
- `neighbor(x, y, direction)`: directional coordinate transform.
- `open_wall(cell, direction)`: opens one wall and mirrored opposite neighbor wall.
- `neighbors(x, y)`: returns in-bounds directional neighbors.
- `stamp_42(forbidden)`: produces deterministic blocked-cell pattern centered in maze.

Why `stamp_42` exists: subject constraint requires fixed masked shape; generator then routes around it.

---

## 5) Generation Algorithms (`mazegen/algorithms.py`)

### `generate_perfect_dfs(...)`

What it does:
- iterative DFS with explicit stack
- carves only toward unvisited, unblocked cells
- creates spanning tree over all open cells

Why this algorithm:
- Perfect maze requirement = connected + acyclic graph
- DFS naturally produces a spanning tree with simple implementation

Safety:
- rejects blocked start
- validates visited count matches expected open-cell count

### `add_loops(...)`

What it does:
- scans closed internal walls (`E` and `S` directions only to avoid duplicates)
- randomly opens a ratio (~10% default) to create cycles

Why:
- Imperfect mode needs multiple routes/loops while preserving connectivity from DFS base.

---

## 6) Pathfinding (`mazegen/pathfinding.py`)

### `bfs_shortest_path(...)`

What it does:
- BFS from entry to goal using queue + predecessor map.
- traverses only open passages and non-blocked cells.
- reconstructs shortest path by backtracking `prev`.

Why BFS:
- Grid graph is unweighted.
- BFS guarantees shortest path length.

### `path_to_moves(path)`

What it does:
- converts coordinate list into `"NESW"` string.

Why:
- subject output requires compact move encoding.

---

## 7) Structural Validation (`mazegen/validate.py`)

Validation is crucial because generation randomness can violate constraints unless checked.

### Checks and why each exists

- `validate_symmetry`: both sides of shared wall must agree.
- `validate_borders`: external borders must remain closed.
- `validate_blocked_closed`: blocked cells must stay fully closed (`0xF`).
- `validate_open_areas_max2`: rejects fully open 3x3 windows.
- `validate_reachability`: all non-blocked cells must be connected from entry and include exit.
- `validate_tree_structure`: in perfect mode, edge count must equal `nodes-1` (tree property).
- `validate_all`: unified policy gate; perfect mode adds tree check.

Why this module exists:
- "Generate then verify" is safer than assuming generator always satisfies every rule.

---

## 8) Public Facade (`mazegen/generator.py`)

`MazeGenerator` is the domain API used by app layer and users.

### Constructor and invariants

- validates width/height types and positivity
- validates `entry`/`exit` tuple structure and bounds
- rejects identical entry/exit
- stores deterministic seed option

Why:
- fail fast before expensive generation.

### Internal helper methods

- `_validate_point(...)`: strict coordinate schema checker.
- `_ensure_generated()`: enforces call order (`generate()` before reads).

### Main workflow methods

- `generate()`: convenience wrapper.
- `generate_with_callback(on_step, step_stride)`:
  - seeds RNG
  - creates new maze per attempt
  - applies `stamp_42` unless maze too small
  - runs DFS and optional loop opening
  - runs full validation
  - retries up to 1000 attempts

Why retries:
- with blocked layouts and constraints, rare invalid random outcomes are possible.

### Output/query methods

- `solve_shortest()`: cached BFS result.
- `path_moves()`: shortest path in NESW format.
- `to_hex_lines()`: wall bitmasks encoded row-wise hex strings.
- `get_cell_walls(x,y)`: safe access with explicit bounds validation.
- `blocked_cells` property: copy of blocked set (encapsulation).

---

## 9) Application Parser (`app/parser.py`)

This module converts text config into immutable validated `MazeConfig`.

### `MazeConfig` dataclass

Holds all runtime options:
- required: width/height/entry/exit/output_file/perfect
- optional: seed/renderer/generate_delay_ms/solve_delay_ms

### Parsing helpers

- `_parse_int(...)`: strict regex integer parsing + 32-bit bounds.
- `_parse_bool(...)`: supports flexible boolean tokens.
- `_parse_coord(...)`: strict `x,y` format.

### `load_config(path)`

Responsibilities:
- verify file exists and is regular file
- parse non-empty non-comment `KEY=VALUE` lines
- reject unknown/duplicate keys
- ensure required keys exist
- validate cross-field constraints (bounds, entry!=exit, non-negative delays)
- normalize renderer (`auto|ascii|curses`)
- return immutable `MazeConfig`

Why strict parser:
- config is the external contract; strictness prevents undefined runtime behavior.

---

## 10) Output Writer (`app/writer.py`)

### `GeneratorLike` protocol

Declares required generator methods without hard coupling to concrete class.

Why:
- improves testability and loose coupling.

### `write_output(path, cfg, generator)`

What it enforces:
- hex row count equals maze height
- every row width equals maze width

Output format:
1. hex grid lines
2. blank line
3. entry `x,y`
4. exit `x,y`
5. path moves string

Why:
- strict compliance with subject/output spec and easy downstream parsing.

---

## 11) Rendering Layer

## 11.1 ASCII renderer (`app/renderer_ascii.py`)

Purpose:
- no curses dependency
- usable fallback
- still high-quality visual output (Unicode box drawing + legend)

Key functions:
- `_mode_label(...)`: status text.
- `_boxed_lines(...)`: reusable panel builder.
- `_junction_char(...)`: intersection glyph selection.
- `_path_cells(...)`, `_path_sequence(...)`, `_path_directions(...)`: convert move string into drawable path geometry.
- `build_ascii_lines(...)`: full maze canvas generation.
- `render_ascii(...)`: compose header/maze/legend, print and return string.

Design detail:
- blocked cells are merged visually by suppressing internal walls between adjacent blocked cells.

## 11.2 Curses renderer (`app/renderer_curses.py`)

Purpose:
- interactive live UI (regenerate, animate generation, animate solve, toggle path, cycle palette).

Key components:
- `_UiState` dataclass: mutable UI state bag.
- `_frame_char(...)`, `_draw_panel(...)`: frame/panel primitives.
- `_path_cells`, `_path_cell_sequence`, `_path_directions`: path geometry utilities.
- `_draw_maze(...)`: frame redraw pipeline.
- `_init_colors()`: color pair setup.
- `_loop(...)`: event loop + key handlers.
- `run_curses_ui(...)`: safe wrapper, maps curses failures to `RenderError`.

Why both renderers:
- best UX when curses available, reliable fallback when not.

---

## 12) Entrypoint Orchestration (`a_maze_ing.py`)

This file coordinates everything:

- `_build_generator(cfg)`: adapter from config to domain generator.
- `_generate_and_write(cfg, generator, on_step)`: generation + output write + error mapping.
- `_announce_renderer(...)`: stderr renderer status.
- `_run_renderer(...)`: renderer strategy:
  - forced ascii
  - forced curses
  - auto: try curses, fallback to ascii on `RenderError`
- `main(argv)`: full flow and top-level error handling.

Important behavior:
- if maze too small for visible `42`, warns and continues without stamp.

---

## 13) Error Model (`app/errors.py`)

- `AppError`: app-facing error base class.
- `ConfigError`: invalid configuration.
- `OutputError`: write/export failures.
- `RenderError`: renderer/curses failures.

Why this exists:
- keeps failures categorized and user-readable at entrypoint.

---

## 14) Tests (`tests/test_project.py`)

Two groups:

- `ParserTests`: unknown keys, duplicates, numeric parsing, bounds, boolean parsing, comments/blanks, renderer values, delays, entry/exit constraints.
- `GeneratorTests`: generation preconditions, constructor validation, deterministic seed behavior, small-maze no-42 behavior, path/hex outputs, bounds checks.

Custom runner:
- `FancyTestResult` + `FancyTestRunner` produce concise per-test timing output.

Why tests matter here:
- most project risk is in invalid input handling and generation invariants.

---

## 15) Packaging and Tooling

- `pyproject.toml`: PEP 517 build metadata with custom backend.
- `mazegen/build_backend.py`: offline-friendly wheel/sdist creation logic.
- `Makefile`: install/run/debug/lint/clean helpers.
- `.flake8`: lint exclusions.
- `config.txt`: default runtime config example.

Why custom backend:
- minimizes dependencies and supports controlled artifact creation for this package.

---

## 16) Python Syntax and Patterns Used (Project-Wide Study)

This project uses modern Python 3.10+ idioms intentionally:

- `from __future__ import annotations`: postpones annotation evaluation.
- `dataclass(frozen=True)`: immutable value objects (`Cell`, `MazeConfig`).
- type hints with unions (`int | None`) and generics (`list[str]`, `dict[...]`).
- `Protocol`: structural typing for decoupled interfaces (`GeneratorLike`).
- comprehensions and generator expressions for compact transformations.
- bitwise ops (`&`, `~`) for wall flags.
- exception chaining (`raise ... from exc`) for root-cause preservation.
- closure callbacks (`step_callback`) for progress reporting.
- BFS/DFS with `deque`, stacks, predecessor maps.
- `Pathlib` for safe path manipulation.
- guard clauses for fail-fast validation.

The syntax is chosen for readability, explicit contracts, and correctness.

---

## 17) "We Needed X, So We Built Y" Mapping

- Need reproducibility -> seeded `random.Random` in generator.
- Need strict correctness -> layered validation module + retries.
- Need shortest path guarantee -> BFS pathfinder.
- Need subject-specific blocked pattern -> `stamp_42`.
- Need perfect/non-perfect modes -> DFS tree + optional loop opener.
- Need output interoperability -> hex writer with strict dimensions.
- Need robust UX in mixed terminals -> curses + ASCII fallback.
- Need maintainable architecture -> domain/app/orchestrator separation.
- Need reusable library -> `mazegen` facade + packaging backend.

---

## 18) Practical Reading Order for New Contributors

1. `README.md` (conceptual overview)
2. `mazegen/maze.py` (core representation)
3. `mazegen/algorithms.py` + `pathfinding.py` (core logic)
4. `mazegen/validate.py` (constraints)
5. `mazegen/generator.py` (public engine API)
6. `app/parser.py` + `writer.py` (I/O contracts)
7. `app/renderer_ascii.py` then `app/renderer_curses.py` (presentation layer)
8. `a_maze_ing.py` (runtime orchestration)
9. `tests/test_project.py` (behavior guarantees)

---

## 19) Final Mental Model

Think of the project as a pipeline:

`Config -> Validated Settings -> Maze Model -> Generation -> Validation -> Solve -> Export -> Render`

Each module owns one step, and each step exists because the project demands both algorithmic correctness and user-facing usability.
