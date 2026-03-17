"""Basic regression tests for parser and generator behavior."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.parser import load_config  # noqa: E402
from mazegen import MazeGenerator  # noqa: E402


class ParserTests(unittest.TestCase):
    """Cover configuration parsing edge cases."""

    def test_load_config_accepts_optional_keys(self) -> None:
        """Parser should read every documented optional setting."""
        config_text = "\n".join(
            [
                "WIDTH=9",
                "HEIGHT=7",
                "ENTRY=0,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=False",
                "SEED=42",
                "ALGO=dfs",
                "RENDERER=ascii",
                "GENERATE_DELAY_MS=5",
                "SOLVE_DELAY_MS=7",
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.txt"
            config_path.write_text(config_text, encoding="utf-8")
            cfg = load_config(config_path)

        self.assertEqual(cfg.width, 9)
        self.assertEqual(cfg.height, 7)
        self.assertFalse(cfg.perfect)
        self.assertEqual(cfg.renderer, "ascii")
        self.assertEqual(cfg.generate_delay_ms, 5)
        self.assertEqual(cfg.solve_delay_ms, 7)


class GeneratorTests(unittest.TestCase):
    """Cover reusable generator guarantees."""

    def test_generator_produces_hex_rows_and_path(self) -> None:
        """Generated mazes should expose rows and a valid shortest path."""
        generator = MazeGenerator(
            width=9,
            height=7,
            entry=(0, 0),
            exit=(8, 6),
            perfect=True,
            seed=42,
        )

        generator.generate()

        hex_rows = generator.to_hex_lines()
        path_moves = generator.path_moves()

        self.assertEqual(len(hex_rows), 7)
        self.assertTrue(all(len(row) == 9 for row in hex_rows))
        self.assertNotEqual(path_moves, "")
        self.assertEqual(generator.solve_shortest()[0], (0, 0))
        self.assertEqual(generator.solve_shortest()[-1], (8, 6))


if __name__ == "__main__":
    unittest.main()
