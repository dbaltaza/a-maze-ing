"""Launch the AA-style visual renderer in a Tk-capable interpreter."""

from __future__ import annotations

import json
from glob import glob
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from app.parser import MazeConfig
from mazegen import MazeGenerator


def _choose_python() -> str:
    """Pick an interpreter that has tkinter available."""
    raw_candidates = [
        shutil.which("python3"),
        shutil.which("python"),
        getattr(sys, "_base_executable", None),
        sys.executable,
        str(Path(sys.base_prefix) / "bin" / "python3"),
        str(Path(sys.base_prefix) / "bin" / "python"),
        "/opt/homebrew/bin/python3",
        "/opt/homebrew/bin/python3.14",
        "/opt/homebrew/bin/python3.13",
        "/opt/homebrew/bin/python3.12",
        "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
        *sorted(
            glob("/Library/Frameworks/Python.framework/Versions/*/bin/python3"),
            reverse=True,
        ),
    ]
    candidates: list[str] = []
    seen: set[str] = set()
    for candidate in raw_candidates:
        if not candidate:
            continue
        resolved = str(Path(candidate).resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        candidates.append(resolved)
    probe = (
        "import tkinter as tk\n"
        "root = tk.Tk()\n"
        "root.withdraw()\n"
        "root.update_idletasks()\n"
        "root.destroy()\n"
        "print('ok')\n"
    )
    for candidate in candidates:
        if not Path(candidate).exists():
            continue
        completed = subprocess.run(
            [candidate, "-c", probe],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return candidate
    raise RuntimeError(
        "AA-style visual renderer requires tkinter, but no local Python "
        "interpreter with tkinter was found."
    )


def draw_mlx_maze(maze: MazeGenerator, cfg: MazeConfig) -> None:
    """Launch the visual helper using a Python interpreter with tkinter."""
    root = Path(__file__).resolve().parents[1]
    helper = root / "app" / "renderer_mlx_tk.py"
    python_bin = _choose_python()

    payload = {
        "cfg": {
            "width": cfg.width,
            "height": cfg.height,
            "entry": list(cfg.entry),
            "exit": list(cfg.exit),
            "output_file": cfg.output_file,
            "perfect": cfg.perfect,
            "seed": cfg.seed,
            "renderer": cfg.renderer,
            "algorithm": cfg.algorithm,
            "density": cfg.density,
        },
        "maze": {
            "hex_lines": maze.to_hex_lines(),
            "solution": [list(cell) for cell in maze.solve_shortest()],
        },
    }

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as handle:
        json.dump(payload, handle)
        temp_path = handle.name

    try:
        completed = subprocess.run(
            [python_bin, str(helper), temp_path],
            cwd=root,
            check=False,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    if completed.returncode != 0:
        raise RuntimeError(
            f"visual renderer using '{python_bin}' exited with status "
            f"{completed.returncode}"
        )
