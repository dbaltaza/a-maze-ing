*This project has been created as part of the 42 curriculum by luispais, dbaltaza*

# A-Maze-ing

## Description

A-Maze-ing is a Python maze generator that reads a text configuration file, builds a valid maze, writes the result in the required hexadecimal wall format, and displays the maze in the terminal.

The project is split into two parts:

- `mazegen/`: reusable maze generation and solving logic
- `app/`: configuration parsing, rendering, and application-level error handling

The main program is `a_maze_ing.py`. It validates the input configuration, generates the maze, exports it to the configured output file, and launches the terminal renderer.

## Instructions

### Requirements

- Python 3.10 or later
- A virtual environment is recommended

### Installation

Using the provided Makefile:

```bash
make install
```

Manual installation:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install .
python3 -m pip install build flake8 mypy
```

### Execution

The program must be run with one configuration file:

```bash
python3 a_maze_ing.py config.txt
```

Useful Makefile targets:

```bash
make run
make debug
make lint
make lint-strict
make clean
make package
```

`make package` builds the reusable package artifacts at the root of the repository:

- `mazegen-<version>.tar.gz`
- `mazegen-<version>-py3-none-any.whl`

### Validation and quality

The project is intended to follow the subject requirements:

- `flake8` for style checks
- `mypy` for static type checking
- graceful error messages for invalid config files, impossible coordinates, generation failures, and output failures

## Configuration File Structure

The configuration file uses one `KEY=VALUE` pair per line.

- Empty lines are ignored.
- Lines starting with `#` are comments.
- Unknown keys are rejected.
- Duplicate keys are rejected.

Mandatory keys:

```ini
WIDTH=25
HEIGHT=15
ENTRY=0,0
EXIT=24,14
OUTPUT_FILE=maze_output.txt
PERFECT=False
```

Optional keys supported by this implementation:

```ini
SEED=42
RENDERER=auto
GENERATE_DELAY_MS=120
SOLVE_DELAY_MS=100
```

Full example:

```ini
# Maze dimensions
WIDTH=25
HEIGHT=15

# Start and end cells
ENTRY=0,0
EXIT=24,14

# Export target
OUTPUT_FILE=maze_output.txt

# Perfect maze or maze with extra loops
PERFECT=False

# Optional settings
SEED=42
RENDERER=ascii
GENERATE_DELAY_MS=120
SOLVE_DELAY_MS=100
```

Field meaning:

- `WIDTH`, `HEIGHT`: maze size in cells
- `ENTRY`, `EXIT`: coordinates in `x,y` format
- `OUTPUT_FILE`: destination file for the hexadecimal export
- `PERFECT`: `True` for a perfect maze, `False` to add loops
- `SEED`: optional deterministic seed
- `RENDERER`: `auto`, `ascii`, or `curses`
- `GENERATE_DELAY_MS`: generation animation delay in milliseconds
- `SOLVE_DELAY_MS`: solve animation delay in milliseconds

## Output Format

The output file is written row by row using one hexadecimal digit per cell.

Wall bits:

- bit `0`: North
- bit `1`: East
- bit `2`: South
- bit `3`: West

After the maze grid, the file contains:

1. an empty line
2. the entry coordinates
3. the exit coordinates
4. the shortest valid path as a string made of `N`, `E`, `S`, `W`

All lines end with `\n`.

## Maze Generation Algorithm

The chosen generation algorithm is recursive backtracking implemented with an explicit stack, which is a depth-first search approach.

High-level steps:

1. Start from the entry cell.
2. Mark the current cell as visited.
3. Randomly choose an unvisited neighbor.
4. Open the wall between the current cell and that neighbor.
5. Continue until there are no unvisited neighbors.
6. Backtrack and repeat until all non-blocked cells are connected.

For non-perfect mazes, the project first generates a perfect maze and then opens a small number of additional internal walls to create loops.

The shortest path is computed with breadth-first search.

## Why This Algorithm

This algorithm was chosen because it fits the subject well:

- it naturally produces a connected spanning tree for perfect mazes
- it is simple to implement and reason about
- it works well with seeded randomness
- it is easy to validate against the subject constraints
- it integrates cleanly with the reusable `MazeGenerator` class

Breadth-first search was chosen for solving because the maze graph is unweighted and BFS guarantees a shortest path.

## Reusable Code

The reusable part of the project is the `mazegen` package.

Main public API:

- `MazeGenerator`
- `write_output`

Example:

```python
from mazegen import MazeGenerator

generator = MazeGenerator(
    width=25,
    height=15,
    entry=(0, 0),
    exit=(24, 14),
    perfect=True,
    seed=42,
)

generator.generate()

hex_lines = generator.to_hex_lines()
path = generator.solve_shortest()
moves = generator.path_moves()
blocked = generator.blocked_cells
```

What can be reused:

- maze structure and wall encoding
- maze generation
- structural validation
- shortest path solving
- output export helpers

How it is reused:

- import `MazeGenerator` from `mazegen`
- build the package with `python3 -m build --outdir .`
- install the generated `mazegen-*.whl` or `mazegen-*.tar.gz`

## Advanced Features

This implementation includes several features beyond the minimum generation/export flow:

- deterministic generation with `SEED`
- perfect and non-perfect modes
- terminal ASCII rendering
- curses terminal rendering when available
- show/hide shortest path
- maze regeneration from the UI
- wall color cycling in the terminal UI
- generation and solve animations
- centered blocked-cell `42` pattern when the maze is large enough

## Team And Project Management

### Roles

- `dbaltaza`: maze engine, generation logic, pathfinding, validation
- `luispais`: application layer, configuration parsing, terminal rendering, user interaction

### Anticipated planning and evolution

The work can be described in the following phases:

1. define the maze model and wall encoding
2. parse and validate the configuration file
3. implement maze generation
4. implement pathfinding and output export
5. add renderers and user interaction
6. package the reusable code and finalize documentation

As the project evolved, validation became a larger part of the work than the initial generation logic alone. The subject combines multiple constraints at once: coherent walls, closed borders, connectivity, a visible `42` pattern, shortest-path export, and optional perfect-maze behavior. Because of that, the codebase ended up with a clear validation layer and a stricter parser than a simpler prototype would need.

### What worked well

- separating `mazegen` from `app`
- using a dedicated validation module
- keeping the generator reusable instead of coupling it to terminal rendering
- using type hints and docstrings throughout the project

### What could be improved

- the README and packaging requirements needed a final compliance pass
- more automated end-to-end tests for exported files would improve confidence
- the development workflow would be simpler if the environment used by the Makefile was always explicit

### Tools used

- Python 3
- `pydantic` for configuration validation
- `flake8` for style checks
- `mypy` for static type checking
- `unittest` for test coverage
- `build` and `setuptools` for packaging
- `make` for common project commands
- `git` for version control

## Resources

Classic references used for the project:

- Python documentation: https://docs.python.org/3/
- `dataclasses`: https://docs.python.org/3/library/dataclasses.html
- `typing`: https://docs.python.org/3/library/typing.html
- `pathlib`: https://docs.python.org/3/library/pathlib.html
- `curses`: https://docs.python.org/3/library/curses.html
- `setuptools` packaging guide: https://setuptools.pypa.io/
- Python packaging user guide: https://packaging.python.org/
- `flake8` documentation: https://flake8.pycqa.org/
- `mypy` documentation: https://mypy.readthedocs.io/
- Breadth-first search and depth-first search references from standard algorithm courses and textbooks

AI usage in this project:

- AI was used to help structure documentation, review requirement coverage, and improve code organization.
- AI was also used to help refine type hints, error handling, and explanations of the implemented algorithms.
- The maze model, renderer behavior, packaging, and final repository content were reviewed and adjusted inside the project codebase.
