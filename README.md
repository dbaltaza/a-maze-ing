# A-Maze-ing

<div align="center">

**A sophisticated Python maze generator and solver with multiple algorithms and interactive visualization**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: flake8](https://img.shields.io/badge/code%20style-flake8-black.svg)](https://flake8.pycqa.org/)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration](#️-configuration)
- [Usage](#-usage)
- [Architecture](#-architecture)
- [Algorithms](#-algorithms)
- [Interactive Controls](#-interactive-controls)
- [API Reference](#-api-reference)
- [Development](#-development)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**A-Maze-ing** is a professional-grade maze generation and pathfinding library built in Python. It combines powerful algorithmic maze generation with interactive terminal-based visualization, making it perfect for education, algorithm visualization, and maze-based applications.

The project is architecturally split into two main components:
- **`mazegen/`** - A reusable, standalone maze generation engine
- **`app/`** - Application layer with config parsing, rendering, and I/O

---

## ✨ Features

### Core Capabilities
- 🎲 **Deterministic Generation** - Seed-based reproducible mazes
- 🧩 **Multiple Algorithms** - Recursive backtracking (DFS) with extensible architecture
- 🎯 **Pathfinding** - BFS-based shortest path solving
- 📦 **Reusable Package** - Import `mazegen` as a library in your own projects
- 🎨 **Dual Rendering** - Interactive curses UI with automatic ASCII fallback
- 📝 **Hex Export** - Standard hexadecimal wall encoding output format
- 🔒 **Perfect/Imperfect Modes** - Generate tree-structured or cyclic mazes
- 🎭 **Custom Patterns** - Built-in "42" blocked cell pattern

### Interactive Features
- ⚡ **Live Generation** - Watch mazes being generated step-by-step
- 🔍 **Solution Animation** - Visualize pathfinding in real-time
- 🎨 **Color Themes** - Cycle through different color schemes
- 🔄 **On-the-fly Regeneration** - Create new mazes without restarting
- 📐 **Responsive Display** - Automatic terminal size adaptation

---

## 🚀 Installation

### Requirements
- Python 3.10 or higher
- Tk support for the visual renderer

On Ubuntu/Debian, install Tk before running the visual mode:
```bash
sudo apt-get update
sudo apt-get install python3-tk
```

### Install via Makefile
```bash
make build
source .venv/bin/activate
make install
```

### Manual Installation
```bash
pip install --upgrade pip
pip install .
```

### Build as Package
```bash
# Build wheel
python3 -m pip wheel . -w .

# Build source distribution
python3 - <<'PY'
from mazegen import build_backend
print(build_backend.build_sdist("."))
PY
```

---

## 🎮 Quick Start

### Basic Usage
```bash
python3 a_maze_ing.py config.txt
```

### Using Makefile
```bash
make build      # Create .venv if missing
make run        # Run with default config
make debug      # Run with debugger
make clean      # Clean build artifacts
make lint       # Run flake8 and mypy
```

---

## ⚙️ Configuration

Create a configuration file (e.g., `config.txt`) with the following format:

### Required Parameters
```ini
WIDTH=25                    # Maze width (cells)
HEIGHT=15                   # Maze height (cells)
ENTRY=0,0                   # Entry point (x,y)
EXIT=24,14                  # Exit point (x,y)
OUTPUT_FILE=maze_output.txt # Output file path
PERFECT=True                # True = no loops, False = cycles allowed
```

### Optional Parameters
```ini
SEED=42                     # Deterministic seed (omit for random)
RENDERER=auto               # Renderer: auto|curses|ascii
GENERATE_DELAY_MS=120       # Animation delay during generation
SOLVE_DELAY_MS=100          # Animation delay during solving
```

### Configuration Details

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `WIDTH` | int | **required** | Maze width in cells (must be > 0) |
| `HEIGHT` | int | **required** | Maze height in cells (must be > 0) |
| `ENTRY` | x,y | **required** | Starting coordinate (0-indexed) |
| `EXIT` | x,y | **required** | Exit coordinate (0-indexed, must differ from entry) |
| `OUTPUT_FILE` | path | **required** | File path for hex output |
| `PERFECT` | bool | **required** | `True` for perfect maze, `False` for loops |
| `SEED` | int | random | Seed for reproducible generation |
| `RENDERER` | string | `auto` | Rendering mode (`auto`/`curses`/`ascii`) |
| `GENERATE_DELAY_MS` | int | `0` | Delay for generation animation (ms) |
| `SOLVE_DELAY_MS` | int | `0` | Delay for solving animation (ms) |

---

## 📖 Usage

### Command Line
```bash
# Use default config.txt
python3 a_maze_ing.py

# Use custom config
python3 a_maze_ing.py my_config.txt

# Force ASCII rendering
# (set RENDERER=ascii in config)
```

### Output Format

The generated output file contains:
1. Hexadecimal wall encoding (one row per maze row)
2. Blank line
3. Entry coordinates (`x,y`)
4. Exit coordinates (`x,y`)
5. Shortest path as directional moves (`NESW` string)

**Example:**
```
F9F9F9F...
ABABABAB...
...

0,0
24,14
EESSENEESWWN...
```

### Wall Encoding

Each cell is encoded as a 4-bit hexadecimal value:
- `0x1` - North wall
- `0x2` - East wall
- `0x4` - South wall
- `0x8` - West wall

Example: `0xF` = all walls closed, `0x6` = East and South walls only

---

## 🏗️ Architecture

```
a-maze-ing/
├── a_maze_ing.py          # Main entrypoint and orchestration
├── app/                   # Application layer
│   ├── errors.py          # Custom exception types
│   ├── parser.py          # Config file parsing
│   ├── writer.py          # Output file generation
│   ├── renderer_ascii.py  # ASCII fallback renderer
│   └── renderer_curses.py # Interactive curses UI
├── mazegen/               # Reusable maze engine
│   ├── __init__.py        # Public API
│   ├── maze.py            # Core maze data structure
│   ├── algorithms.py      # Generation algorithms
│   ├── pathfinding.py     # BFS shortest path solver
│   ├── validate.py        # Structural validators
│   ├── generator.py       # High-level generator facade
│   └── build_backend.py   # PEP 517 build backend
└── tests/                 # Test suite
```

### Design Principles

- **Separation of Concerns** - Engine and app layers are fully decoupled
- **Protocol-Based Interfaces** - Loose coupling via Python `Protocol` types
- **Fail-Fast Validation** - Comprehensive input validation before generation
- **Graceful Degradation** - Automatic fallback from curses to ASCII rendering
- **Immutable Configuration** - Frozen dataclasses prevent accidental mutation

---

## 🧮 Algorithms

### Maze Generation

#### Recursive Backtracking (DFS)
- **Type:** Depth-first search with backtracking
- **Properties:** Generates perfect mazes (spanning tree)
- **Characteristics:** Long winding corridors, high "river" factor
- **Time Complexity:** O(width × height)
- **Space Complexity:** O(width × height)

**Algorithm Steps:**
1. Start at entry point with all walls closed
2. Mark current cell as visited
3. Randomly select an unvisited neighbor
4. Carve passage by opening wall between cells
5. Recursively visit neighbor
6. Backtrack when no unvisited neighbors remain
7. Repeat until all cells visited

### Non-Perfect Mode

For imperfect mazes (`PERFECT=False`):
1. Generate perfect maze using DFS
2. Identify all remaining closed internal walls
3. Randomly open ~10% of walls to create cycles
4. Result: Multiple solution paths with loops

### Pathfinding

#### Breadth-First Search (BFS)
- **Guarantees:** Shortest path in unweighted grid
- **Time Complexity:** O(width × height)
- **Output:** Coordinate path + directional moves (NESW)

---

## 🎮 Interactive Controls

When using the curses renderer, the following keyboard controls are available:

| Key | Action |
|-----|--------|
| `g` | **Generate** - Animate maze generation step-by-step |
| `s` | **Solve** - Animate pathfinding from entry to exit |
| `p` | **Path** - Toggle shortest path overlay |
| `c` | **Color** - Cycle through color themes |
| `r` | **Regenerate** - Create a new random maze |
| `q` | **Quit** - Exit the application |

---

## 📚 API Reference

### Using as a Library

```python
from mazegen import MazeGenerator

# Create generator
generator = MazeGenerator(
    width=25,
    height=15,
    entry=(0, 0),
    exit=(24, 14),
    perfect=True,
    seed=42  # Optional
)

# Generate maze
generator.generate()

# Get results
hex_lines = generator.to_hex_lines()        # List of hex strings
path = generator.solve_shortest()           # List of (x, y) coordinates
moves = generator.path_moves()              # "NESW..." string
blocked = generator.blocked_cells           # Set of (x, y) blocked cells
walls = generator.get_cell_walls(5, 3)      # Get wall bitmask for cell
```

### Core API Methods

#### `MazeGenerator.__init__(...)`
```python
def __init__(
    width: int,
    height: int,
    entry: tuple[int, int],
    exit: tuple[int, int],
    perfect: bool,
    seed: int | None = None
)
```

#### `generate()`
Generates the maze structure. Must be called before accessing results.

#### `to_hex_lines() -> list[str]`
Returns maze wall encoding as hexadecimal strings.

#### `solve_shortest() -> list[tuple[int, int]]`
Returns shortest path as list of coordinates.

#### `path_moves() -> str`
Returns path as directional string (e.g., `"EESSENW"`).

#### `get_cell_walls(x: int, y: int) -> int`
Returns 4-bit wall encoding for specified cell.

#### `blocked_cells -> set[tuple[int, int]]`
Returns set of cells blocked by "42" pattern.

---

## 🛠️ Development

### Project Structure

The codebase follows a clean architecture pattern:

- **Domain Layer** (`mazegen/`) - Pure maze logic, no I/O dependencies
- **Application Layer** (`app/`) - User-facing features, config, rendering
- **Orchestration** (`a_maze_ing.py`) - Coordinates components

### Code Quality

```bash
# Run linters
make lint

# Manual linting
flake8 a_maze_ing.py app/ mazegen/
mypy a_maze_ing.py app/ mazegen/
```

### Testing

```bash
# Run tests
python3 -m pytest tests/

# With coverage
python3 -m pytest --cov=mazegen --cov=app tests/
```

### Adding New Algorithms

The project uses a recursive backtracking (DFS) algorithm for maze generation. To modify or extend the generation algorithm, update the implementation in `mazegen/algorithms.py` and `mazegen/generator.py`.

---

## 🤝 Contributing

Contributions are welcome! This project was created as part of the 42 curriculum by **luispais** and **dbaltaza**.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the existing code style
4. Run linters: `make lint`
5. Test your changes thoroughly
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request

### Code Standards

- Python 3.10+ type hints required
- Follow PEP 8 style guide
- Pass flake8 and mypy checks
- Document public APIs with docstrings
- Maintain separation between `app/` and `mazegen/` layers

---

## 📄 License

This project is open source and available under the MIT License.

---

## 🙏 Acknowledgments

### Team
- **dbaltaza** - Maze engine (`mazegen/`) and core algorithms
- **luispais** - Application layer (`app/`) and UI/UX

### Resources
- [Python Documentation](https://docs.python.org/3/)
- [PEP 517 - Build System](https://peps.python.org/pep-0517/)
- Maze generation algorithms from classic CS literature
- 42 School curriculum guidelines

### AI Transparency
AI tools were used to assist with:
- Code structure and architecture patterns
- Documentation and technical writing
- Type hint consistency and error handling

All code was reviewed, adapted, and validated against project requirements.

---

## 📞 Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check existing documentation in this README
- Review inline code documentation

---

<div align="center">

**Built with ❤️ as part of the 42 curriculum**

*Perfect mazes, perfectly generated*

</div>
