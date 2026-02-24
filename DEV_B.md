# Dev B — App Layer, Config, Output, UI (a_maze_ing.py)

You own the **application glue**: config parsing, required output file, and interactive terminal UI.
You should treat `mazegen.MazeGenerator` as a black box with a stable public API.

---

## Your scope (you own these files)
- `a_maze_ing.py`
- `app/**`
- `config.txt`
- Most of `Makefile` + `README.md` structure (coordinate changes with Dev A if needed)

**Avoid editing**: `mazegen/**` unless coordinating.

---

## Interface you can rely on (from Dev A)
Import:

```python
from mazegen import MazeGenerator
```

You can call:
- `g = MazeGenerator(width, height, entry, exit, perfect, seed, algo)`
- `g.generate()`
- `hex_lines = g.to_hex_lines()`
- `path = g.path_moves()`
- `walls = g.get_cell_walls(x,y)`
- `blocked = g.blocked_cells`

---

## What you must implement
### 1) Config parser + validation (`app/parser.py`)
Parse a file of `KEY=VALUE` lines and ignore `# comments`.

Mandatory keys (subject):  
- `WIDTH`, `HEIGHT`
- `ENTRY` (x,y)
- `EXIT` (x,y)
- `OUTPUT_FILE`
- `PERFECT` (true/false)

Optional but useful:
- `SEED`
- `ALGO`

Validation:
- required keys exist
- types correct
- entry/exit in bounds and not equal
- if maze too small for the 42 stamp: print the required message (still proceed with a plain maze if subject expects that behavior)

Return a `MazeConfig` dataclass.

---

### 2) Output writer (`app/writer.py`)
Write the output file in required structure:
1. `height` lines of `width` hex digits (from `to_hex_lines()`)
2. blank line
3. entry coords
4. exit coords
5. shortest path string (`NESW...`)

Keep formatting consistent and simple.

---

### 3) Renderers
#### ASCII fallback (`app/renderer_ascii.py`)
- Draw maze walls in terminal
- Mark entry/exit
- Mark 42 blocked cells (e.g., `#` or special char)
- Optional overlay of path (toggle)

#### Curses UI (`app/renderer_curses.py`)
Interactive requirements:
- regenerate maze
- show/hide shortest path
- change wall colors
- (optional) different color for the 42 pattern

Suggested keys:
- `r`: regenerate
- `p`: toggle path
- `c`: cycle colors
- `q`: quit
- optional `s`: save output again

Renderer must only use generator public methods:
- `get_cell_walls(x,y)` for walls
- `blocked_cells` for 42
- `path_moves()` (or `solve_shortest()` if you need coords)

---

### 4) Entry point (`a_maze_ing.py`)
Execution flow:
1. read config path from argv (default `config.txt`)
2. parse config
3. create generator
4. `generate()`
5. write output file
6. start UI loop (curses if available else ASCII)

Make sure errors are friendly (no stack traces unless debug mode).

---

## Work order (recommended)
1. Build parser returning `MazeConfig`
2. Build writer using `to_hex_lines()` + `path_moves()`
3. Implement ASCII renderer to validate walls quickly
4. Implement curses UI + keybinds
5. Integrate everything in `a_maze_ing.py`
6. Polish Makefile + README

---

## Makefile targets you should ensure work
- `make install`: installs deps (dev) + editable install of package
- `make run`: runs `python3 a_maze_ing.py config.txt`
- `make debug`: runs with debug flag/env var
- `make lint`: flake8 + mypy (or whichever chosen)
- `make clean`: removes `__pycache__`, `.mypy_cache`, `dist`, `build`, etc

---

## Integration checkpoints with Dev A
- When Dev A ships a working `MazeGenerator`, you should:
  - Render a small maze (e.g., 10×6) in ASCII
  - Verify hex output file has correct dimensions and hex chars
  - Toggle path on/off in UI
  - Regenerate repeatedly to ensure no crashes

---

## Notes to avoid merge pain
- Don’t change `mazegen/**` without coordination
- If you need extra data (like path coords), request a new method from Dev A before hacking internals
- Keep UI logic separate from parsing/writing (no “god file”)
