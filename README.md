*This project has been created as part of the 42 curriculum by luispais.*

# A-Maze-ing

## Description
This project generates a maze from a config file, writes a required hexadecimal output format, and displays the maze in terminal.

The codebase is split into:
- `mazegen/`: reusable generator engine (Dev A scope)
- `app/` + `a_maze_ing.py`: application layer, parser, output writer, renderers, orchestration (Dev B scope)

The intent of this README is educational: understand the project in the same order the code was designed, then understand each function in line order.

## Thought Order (Problem -> Solution)

### 1) Problem definition
We need a program that:
1. Reads `KEY=VALUE` configuration.
2. Generates a valid maze with deterministic seed support.
3. Exports maze walls as hex rows.
4. Exports entry, exit, shortest path (`NESW`).
5. Displays maze interactively (`r`, `p`, `c`, `q`).
6. Never crashes with ugly tracebacks on expected user errors.

### 2) Constraints that shape the design
- Python 3.10+.
- Clear error handling.
- Generator must be reusable and treated as a black box by app layer.
- Wall model must remain coherent between neighboring cells.
- “42” blocked pattern is required when size allows.
- Perfect mode requires tree-like connectivity.

### 3) Core architecture decision
Split by responsibility:
- `mazegen/*`: all maze-domain logic (data model, algorithms, validation, pathfinding).
- `app/*`: all user-facing glue (config parsing, output file formatting, rendering).
- `a_maze_ing.py`: orchestrator only.

Why this split:
- Reusability: engine can be imported elsewhere.
- Testability: parser/writer/renderers are independent.
- Team parallelism: Dev A and Dev B can work safely in separate folders.

### 4) Runtime flow decision
Main flow chosen:
1. parse config
2. build generator
3. `generate()`
4. write output file
5. run curses UI
6. fallback to ASCII if curses fails

Reason:
- Output file exists even if UI cannot run.
- Interactive loop can regenerate and re-save repeatedly.

---

## Instructions
### Run
```bash
python3 a_maze_ing.py config.txt
```

### Makefile
```bash
make run
```

Available targets:
- `make install`
- `make run`
- `make debug`
- `make clean`
- `make lint`

---

## Project Map
- `a_maze_ing.py`: top-level orchestration and friendly errors.
- `app/errors.py`: app exception types.
- `app/parser.py`: config parsing + validation.
- `app/writer.py`: required output-file format.
- `app/renderer_ascii.py`: dependency-free fallback display.
- `app/renderer_curses.py`: interactive terminal UI.
- `mazegen/maze.py`: wall bitmask model + 42 stamp.
- `mazegen/algorithms.py`: DFS carving + loop injection.
- `mazegen/validate.py`: structural validators.
- `mazegen/pathfinding.py`: BFS shortest path + move conversion.
- `mazegen/generator.py`: public facade for app.
- `mazegen/build_backend.py`: packaging backend.

---

## Configuration Format
Required keys:
- `WIDTH`
- `HEIGHT`
- `ENTRY` (`x,y`)
- `EXIT` (`x,y`)
- `OUTPUT_FILE`
- `PERFECT`

Optional keys:
- `SEED`
- `ALGO`

Example:
```txt
WIDTH=20
HEIGHT=10
ENTRY=0,0
EXIT=19,9
OUTPUT_FILE=maze_output.txt
PERFECT=True
SEED=42
ALGO=dfs
```

---

## Output File Format
`app/writer.py` writes:
1. `height` lines of `width` hex chars (`to_hex_lines()`)
2. one blank line
3. entry `x,y`
4. exit `x,y`
5. shortest path string (`NESW...`)

All lines end with `\n`.

---

## Algorithm Choice
- Main generation algorithm: iterative DFS backtracker.
- Why this algorithm:
  - naturally builds perfect mazes (spanning tree).
  - deterministic with seed-driven `random.Random`.
  - simple to reason about and validate.
- Non-perfect mode:
  - starts from DFS result, then opens extra walls (`add_loops`) to create cycles.

---

## Code Walkthrough (Function by Function, Line Order)

## `a_maze_ing.py`

### `_build_generator(cfg)`
- Receives already-validated `MazeConfig`.
- Calls `MazeGenerator(...)` with explicit named arguments.
- Decision: keep mapping explicit (clear contract between app and engine).

### `_generate_and_write(cfg, generator)`
- Calls `generator.generate()` inside `try`.
- Catches generator errors and wraps them as user-facing runtime message.
- Special-case message for small mazes where 42 stamp cannot fit.
- Calls `write_output(...)`.
- Converts filesystem/data-shape errors into `OutputError`.
- Decision: centralize "generate + persist" because both startup and `r` key reuse it.

### `main(argv)`
- Reads config path from CLI (`argv[1]`) or default `config.txt`.
- Parses config with `load_config`.
- Builds generator, generates maze, writes output once.
- Defines inner callback `regenerate_and_save()` for curses `r` key.
- Tries curses UI; on render failure prints warning and falls back to ASCII.
- Catches all expected app-level exceptions and prints friendly error.
- Returns `0` on success, `1` on failure.

### `if __name__ == "__main__"`
- Standard Python entrypoint guard.
- Uses `SystemExit(main(...))` so shell gets correct exit code.

---

## `app/errors.py`

### `AppError`
- Base application exception type.
- Decision: enables future grouping of app-only failures.

### `ConfigError`
- Subclass of `ValueError` for parsing/validation issues.

### `OutputError`
- Raised for file writing and output-shape issues.

### `RenderError`
- Raised when curses renderer cannot run.

---

## `app/parser.py`

### Module constants
- `_REQUIRED_KEYS`, `_OPTIONAL_KEYS`, `_KNOWN_KEYS`:
  define allowed schema centrally.
- Decision: unknown keys fail fast (prevents silent typos).

### `MazeConfig` dataclass
Fields:
- `width`, `height`
- `entry`, `exit`
- `output_file`
- `perfect`
- optional `seed`
- `algo` default `dfs`

Decision:
- immutable (`frozen=True`) to avoid accidental mutation mid-run.

### `_parse_int(value, key, line_no)`
- Attempts `int(value)`.
- On failure raises `ConfigError` with optional line info.

### `_parse_bool(value, key, line_no)`
- Normalizes lowercase and trims.
- Accepts truthy: `1,true,yes,y,on`.
- Accepts falsy: `0,false,no,n,off`.
- Otherwise raises `ConfigError`.

### `_parse_coord(value, key, line_no)`
- Splits by comma.
- Requires exactly two non-empty parts.
- Parses each part with `_parse_int`.
- Returns `(x, y)` tuple.

### `load_config(path)`
Line-order logic:
1. Convert to `Path`.
2. Validate path exists and is a file.
3. Read file UTF-8.
4. Enumerate lines with `line_no` starting at 1.
5. Ignore empty/comment lines.
6. Require `=` syntax.
7. Normalize key to uppercase.
8. Reject missing key / unknown key / duplicate key.
9. Store `(value, line_no)` in dict.
10. After parse, check missing required keys.
11. Parse width/height and enforce `>0`.
12. Parse entry/exit and enforce bounds + inequality.
13. Parse boolean `PERFECT`.
14. Validate non-empty `OUTPUT_FILE`.
15. Parse optional `SEED` only if non-empty.
16. Parse optional `ALGO` else default `dfs`.
17. Return `MazeConfig`.

Design decisions:
- parser reports precise line numbers when possible.
- validation is strict before generation starts.

---

## `app/writer.py`

### `GeneratorLike` protocol
- Declares only methods writer needs:
  `to_hex_lines`, `path_moves`.
- Decision: loose coupling from concrete `MazeGenerator` class.

### `write_output(path, cfg, generator)`
Line-order logic:
1. Normalize output path.
2. Pull hex lines from generator.
3. Validate row count equals `cfg.height`.
4. Validate each row length equals `cfg.width`.
5. Build payload with exact required ordering.
6. Ensure parent directory exists (`mkdir(parents=True, exist_ok=True)`).
7. Open file with newline `\n` and UTF-8.
8. Write payload and a final newline.

Decision:
- perform shape checks here to fail early if generator contract breaks.

---

## `app/renderer_ascii.py`

### Bit constants
- `N=1, E=2, S=4, W=8` (same wall encoding as engine).

### `GeneratorLike` protocol
- Requires `blocked_cells`, `get_cell_walls`, `path_moves`.

### `_path_cells(entry, moves)`
- Converts move string into set of visited coordinates.
- Ignores unexpected chars defensively.

### `build_ascii_lines(cfg, generator, show_path=False)`
Line-order logic:
1. Compute canvas size: `(2h+1) x (2w+1)`.
2. Fill with spaces.
3. Place `+` at all intersection coordinates.
4. Get blocked set.
5. Optionally compute path overlay set.
6. For each maze cell:
   - compute canvas center `(cx, cy)`
   - get wall bitmask
   - choose center char: `#` blocked, `.` path, `E` entry, `X` exit
   - draw wall chars around center based on bitmask (`-` or `|`)
7. Return list of strings.

### `render_ascii(...)`
- Calls `build_ascii_lines`.
- Joins with newline.
- Prints and returns string.

Decision:
- keep pure builder + printing wrapper for reuse and testing.

---

## `app/renderer_curses.py`

### `_UiState` dataclass
- Holds UI-only state:
  - `show_path`
  - `color_index`
  - `status` line text

Decision:
- clean separation between UI state and maze engine state.

### `_path_cells(entry, moves)`
- Same behavior as ASCII version for path overlay coordinates.

### `_draw_maze(stdscr, cfg, generator, state)`
Line-order logic:
1. Clear screen.
2. Read terminal dimensions.
3. Compute minimum required rows/cols.
4. If too small: show resize message and return safely.
5. Resolve wall/path/blocked color pairs.
6. Pull blocked/path data.
7. Draw `+` intersections.
8. Iterate each maze cell and draw:
   - center char (` `, `#`, `.`, `E`, `X`)
   - surrounding walls from bitmask
9. Draw status/help line.
10. Refresh screen.

### `_init_colors()`
- Initializes curses colors if supported.
- Wall palette in pairs `1..5`.
- Pair `6` for blocked, `7` for path.

### `_loop(stdscr, cfg, generator, regenerate)`
Line-order logic:
1. Hide cursor.
2. Enable keypad and blocking input.
3. Init colors.
4. Start loop:
   - redraw maze
   - read key
   - `q`: quit
   - `p`: toggle path and status
   - `c`: cycle wall color and status
   - `r`: call callback; update status success/failure

### `run_curses_ui(cfg, generator, regenerate=None)`
- Imports curses safely.
- Calls `curses.wrapper(_loop, ...)`.
- Converts `curses.error` into `RenderError` for fallback path.

Decision:
- wrapper handles init/restore automatically.
- outer app can fallback to ASCII without crashing.

---

## `mazegen/__init__.py`
- Re-exports `MazeGenerator`.
- `__all__` defines intended public import surface.

---

## `mazegen/maze.py`

### Direction constants + maps
- `N,E,S,W` as bit values.
- `DIR_BITS`, `DIR_DELTAS`, `OPPOSITE` are lookup tables used everywhere.

Decision:
- single source of truth for wall encoding and movement vectors.

### `Cell` dataclass
- Immutable coordinate struct (currently optional utility type).

### `Maze.__init__(width,height)`
- Validates positive sizes.
- Creates `walls[y][x]` all initialized to `0xF` (all walls closed).

### `in_bounds(x,y)`
- Boundary check helper.

### `get_cell_walls(x,y)`
- Validates bounds, returns bitmask for cell.

### `has_wall(x,y,direction)`
- Tests direction bit in mask.

### `neighbor(x,y,direction)`
- Computes adjacent coordinate from delta lookup.

### `open_wall(cell,direction)`
Line-order logic:
1. Validate direction and source bounds.
2. Compute neighbor.
3. Reject opening outside border.
4. Clear wall bit on current cell.
5. Clear opposite wall bit on neighbor.

Key decision:
- always mirror change in both cells -> coherence guarantee.

### `neighbors(x,y)`
- Returns list of valid neighbor triples `(direction, nx, ny)`.

### `stamp_42(forbidden=None)`
Line-order logic:
1. Define fixed glyph pattern with `X` marks.
2. Compute glyph dimensions.
3. Reject if maze too small.
4. Center glyph offsets `(ox, oy)`.
5. Build blocked set from `X` positions.
6. Reject if entry/exit intersects blocked glyph.
7. Return blocked cells.

Decision:
- deterministic centered glyph, not random.

---

## `mazegen/algorithms.py`

### `generate_perfect_dfs(maze, rng, blocked, start)`
Line-order logic:
1. Reject blocked start.
2. Init `visited` with start and stack `[start]`.
3. While stack not empty:
   - inspect top cell
   - gather unvisited + non-blocked neighbors
   - if none: backtrack (`pop`)
   - else: random neighbor, open wall, mark visited, push
4. Verify visited count equals all non-blocked cells.

Decision:
- iterative DFS avoids recursion-depth issues.
- forms spanning tree on reachable non-blocked graph.

### `add_loops(maze, rng, blocked, ratio=0.10)`
Line-order logic:
1. Gather candidate closed internal walls (only E/S to avoid duplicates).
2. Shuffle candidates.
3. Open first `max(1, int(len*candidate_ratio))`.

Decision:
- controlled cycle injection for non-perfect mazes.

---

## `mazegen/pathfinding.py`

### `bfs_shortest_path(maze, blocked, start, goal)`
Line-order logic:
1. If start/goal blocked -> empty.
2. BFS queue initialized with start.
3. `prev` map tracks parent pointers.
4. Process queue:
   - stop early if goal reached
   - for each neighbor: skip blocked/seen/walled paths
   - record parent and enqueue
5. If goal unseen -> empty.
6. Reconstruct path by walking `prev` backward goal -> start.
7. Reverse and return.

Decision:
- BFS guarantees shortest path in unweighted grid graph.

### `path_to_moves(path)`
Line-order logic:
1. Short path (<2 points) -> empty string.
2. Build delta->letter lookup from directional deltas.
3. For each consecutive pair, compute delta.
4. Validate delta is cardinal.
5. Append letter and join.

Decision:
- keeps output format independent from coordinate list.

---

## `mazegen/validate.py`

### `validate_symmetry`
- For each non-blocked cell and neighbor:
  wall state must match opposite neighbor wall.
- If neighbor blocked, boundary between them must remain closed.

### `validate_borders`
- Ensures outer border walls remain closed on all outer edges.

### `validate_blocked_closed`
- Every blocked cell must remain `0xF` (fully closed).

### `_window_all_open`
- Checks whether a 3x3 window has all shared internal walls open.

### `validate_open_areas_max2`
- Scans every 3x3 window (ignores windows touching blocked cells).
- Fails if any completely open 3x3 area exists.

### `_reachable_cells`
- BFS traversal over open passages from `start`.

### `validate_reachability`
- Confirms entry/exit not blocked.
- Confirms all non-blocked cells are reachable from entry.
- Confirms exit reachable.

### `validate_tree_structure`
- For perfect mode:
  - connectivity must hold
  - count open edges (E and S once each)
  - tree property `edges == nodes - 1`

### `validate_all`
- Runs structural checks list.
- If `perfect=True`, also enforce tree structure.

Decision:
- validation separated from generation for clarity and regeneration loops.

---

## `mazegen/generator.py`

### `MazeGenerator.__init__(...)`
- Validates width/height types and positivity.
- Validates entry/exit coordinates and bounds.
- Ensures entry != exit.
- Restricts current algo implementation to `dfs`.
- Stores config and internal caches (`_maze`, `_blocked`, `_shortest_path`).

### `_validate_point(...)`
- Shared coordinate validation helper.

### `_ensure_generated()`
- Guard to prevent access before `generate()`.

### `generate()`
Line-order logic:
1. Validate algorithm.
2. Seed local RNG from `self._seed`.
3. Reset shortest-path cache.
4. Retry loop up to `max_attempts`:
   - create fresh `Maze`
   - stamp 42 blocked cells
   - carve perfect DFS
   - optional `add_loops` if non-perfect
   - run `validate_all`
   - if valid, store maze/blocked and return
5. If never valid, raise runtime error.

Decision:
- regeneration loop handles stochastic invalid attempts cleanly.

### `solve_shortest()`
- Uses cached BFS result if available.
- Returns copy to protect internal cache list.

### `path_moves()`
- Converts shortest path coordinates into `NESW` string.

### `to_hex_lines()`
- For each row, convert each cell wall bitmask to uppercase hex digit.

### `get_cell_walls(x,y)`
- Bounds checks against configured dimensions.
- Returns raw wall bitmask.

### `blocked_cells` property
- Returns copy of blocked set to avoid external mutation.

---

## `mazegen/build_backend.py`
This file is for packaging (`wheel`/`sdist`) and not maze logic.

High-level roles:
- Read project metadata from `pyproject.toml`.
- Build normalized dist-info names.
- Package `mazegen/` files while skipping `__pycache__`.
- Compute wheel RECORD hashes.
- Build wheel and sdist archives.

Reason this exists:
- project can be built offline with a minimal PEP517 backend.

---

## Makefile Decisions
- `install`: pip upgrade + package install + lint tools.
- `run`: canonical command.
- `debug`: launch with `pdb`.
- `clean`: remove caches/build artifacts.
- `lint`: required flake8 + mypy flags from subject.

---

## Why These Code Decisions
- `Protocol` interfaces in app layer reduce coupling.
- fallback rendering prevents hard failure on unsupported terminals.
- immutable config object reduces accidental side effects.
- validation-first strategy avoids writing invalid output files.
- small pure helper functions (`_parse_*`, `_path_cells`) improve readability and testability.

---

## AI Usage (Project transparency)
AI was used to:
- structure parser and renderer modules,
- enforce error-handling and type-hint consistency,
- draft documentation and line-order reasoning.

All produced code and explanations were reviewed and adapted to this codebase and assignment constraints.

---

## Team And Project Management
- Roles:
  - Dev A: `mazegen/*` reusable engine and packaging backend.
  - Dev B: `app/*`, `a_maze_ing.py`, config handling, output writer, renderers, Makefile, README.
- Planned workflow:
  - first lock public generator API contract,
  - then implement parser/writer/UI against that contract,
  - then integrate and validate.
- What worked well:
  - strict scope split avoided merge conflicts.
  - protocol-based app interfaces kept modules decoupled.
- What could be improved:
  - full-repo lint/style harmonization across both scopes.
  - earlier integration tests for small-maze edge cases.
- Tools used:
  - Python 3.10+
  - flake8
  - mypy
  - Makefile automation
  - Git

---

## Resources
- Python docs: [pathlib](https://docs.python.org/3/library/pathlib.html), [dataclasses](https://docs.python.org/3/library/dataclasses.html), [curses](https://docs.python.org/3/library/curses.html)
- Packaging docs: [PEP 517](https://peps.python.org/pep-0517/), [PyPA packaging guide](https://packaging.python.org/)
- Graph/maze references: DFS backtracker and BFS shortest-path tutorials from standard algorithm references.
- Subject PDF in this repository: `subject.pdf`

---

## Quick Self-Check List
1. `python3 a_maze_ing.py config.txt` runs.
2. Output file has exact required structure.
3. Curses keys: `r`, `p`, `c`, `q`.
4. Curses failure falls back to ASCII.
5. Invalid config returns friendly `Error: ...` and exit code `1`.
