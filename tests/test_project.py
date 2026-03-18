"""Basic regression tests for parser and generator behavior."""

from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.errors import ConfigError  # noqa: E402
from app.parser import _INT_MAX, load_config  # noqa: E402
from app.renderer_ascii import build_ascii_lines, render_ascii, run_ascii_ui  # noqa: E402
from mazegen import MazeGenerator  # noqa: E402


class FancyTestResult(unittest.TextTestResult):
    """Render one clean line per test with a short final status."""

    def getDescription(self, test: unittest.case.TestCase) -> str:
        """Use a compact label instead of unittest's multiline default."""
        name = test._testMethodName.replace("_", " ")
        summary = test.shortDescription()
        if summary:
            return f"{name} :: {summary}"
        return name

    def startTest(self, test: unittest.case.TestCase) -> None:
        """Track timing for the active test."""
        super().startTest(test)
        self._current_start = time.perf_counter()

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        super().addSuccess(test)
        self._finish_current(test, "OK")

    def addFailure(
        self,
        test: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, object],
    ) -> None:
        super().addFailure(test, err)
        self._finish_current(test, "FAIL")

    def addError(
        self,
        test: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, object],
    ) -> None:
        super().addError(test, err)
        self._finish_current(test, "ERROR")

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self._finish_current(test, "SKIP", suffix=f" ({reason})")

    def addExpectedFailure(self, test: unittest.case.TestCase, err: object) -> None:
        super().addExpectedFailure(test, err)
        self._finish_current(test, "XFAIL")

    def addUnexpectedSuccess(self, test: unittest.case.TestCase) -> None:
        super().addUnexpectedSuccess(test)
        self._finish_current(test, "XPASS")

    def _finish_current(
        self,
        test: unittest.case.TestCase,
        label: str,
        *,
        suffix: str = "",
    ) -> None:
        """Print one final line for the completed test."""
        elapsed = time.perf_counter() - self._current_start
        self.stream.write(
            f"{label:5} {self.getDescription(test)} ({elapsed:.3f}s)"
            f"{suffix}\n"
        )
        self.stream.flush()


class FancyTestRunner(unittest.TextTestRunner):
    """Small custom runner with an ANSI summary banner."""

    resultclass = FancyTestResult

    def __init__(self, **kwargs: object) -> None:
        super().__init__(descriptions=False, **kwargs)

    def run(self, test: unittest.suite.TestSuite) -> unittest.result.TestResult:
        """Print a compact header before delegating to unittest."""
        self.stream.write("\n=== A-Maze-ing Test Suite ===\n")
        self.stream.flush()
        result = super().run(test)
        banner = "OK" if result.wasSuccessful() else "FAIL"
        self.stream.write(
            f"=== {banner} {result.testsRun} test(s) checked ===\n"
        )
        self.stream.flush()
        return result


class ParserTests(unittest.TestCase):
    """Cover configuration parsing edge cases."""

    def _write_config(self, lines: list[str]) -> Path:
        """Create a temporary config file for parser assertions."""
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        config_path = Path(tmp_dir.name) / "config.txt"
        config_path.write_text("\n".join(lines), encoding="utf-8")
        return config_path

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

    def test_load_config_rejects_float_values(self) -> None:
        """Float-like values should not be accepted as integers."""
        config_path = self._write_config(
            [
                "WIDTH=9.5",
                "HEIGHT=7",
                "ENTRY=0,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=True",
            ]
        )

        with self.assertRaisesRegex(ConfigError, "WIDTH must be an integer"):
            load_config(config_path)

    def test_load_config_rejects_values_above_int_max(self) -> None:
        """Integer fields should reject values outside the supported range."""
        config_path = self._write_config(
            [
                f"WIDTH={_INT_MAX + 1}",
                "HEIGHT=7",
                "ENTRY=0,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=True",
            ]
        )

        with self.assertRaisesRegex(ConfigError, "WIDTH must be between"):
            load_config(config_path)

    def test_load_config_rejects_missing_required_keys(self) -> None:
        """Missing required keys should fail with a useful message."""
        config_path = self._write_config(
            [
                "WIDTH=9",
                "HEIGHT=7",
                "ENTRY=0,0",
                "PERFECT=True",
            ]
        )

        with self.assertRaisesRegex(
            ConfigError, "missing required config key"
        ):
            load_config(config_path)

    def test_load_config_rejects_duplicate_keys(self) -> None:
        """Duplicate keys should not be silently accepted."""
        config_path = self._write_config(
            [
                "WIDTH=9",
                "WIDTH=10",
                "HEIGHT=7",
                "ENTRY=0,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=True",
            ]
        )

        with self.assertRaisesRegex(ConfigError, "duplicate key 'WIDTH'"):
            load_config(config_path)

    def test_load_config_rejects_unknown_keys(self) -> None:
        """Unknown settings should be rejected immediately."""
        config_path = self._write_config(
            [
                "WIDTH=9",
                "HEIGHT=7",
                "ENTRY=0,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=True",
                "ALGO=dfs",
            ]
        )

        with self.assertRaisesRegex(ConfigError, "unknown key 'ALGO'"):
            load_config(config_path)

    def test_load_config_rejects_invalid_boolean_values(self) -> None:
        """Boolean fields should reject arbitrary strings."""
        config_path = self._write_config(
            [
                "WIDTH=9",
                "HEIGHT=7",
                "ENTRY=0,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=maybe",
            ]
        )

        with self.assertRaisesRegex(
            ConfigError, "PERFECT must be a boolean value"
        ):
            load_config(config_path)

    def test_load_config_rejects_invalid_renderer(self) -> None:
        """Renderer should only accept the documented values."""
        config_path = self._write_config(
            [
                "WIDTH=9",
                "HEIGHT=7",
                "ENTRY=0,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=True",
                "RENDERER=gl",
            ]
        )

        with self.assertRaisesRegex(ConfigError, "RENDERER must be one of"):
            load_config(config_path)

    def test_load_config_rejects_negative_delay(self) -> None:
        """Animation delays should reject negative values."""
        config_path = self._write_config(
            [
                "WIDTH=9",
                "HEIGHT=7",
                "ENTRY=0,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=True",
                "GENERATE_DELAY_MS=-1",
            ]
        )

        with self.assertRaisesRegex(
            ConfigError, "GENERATE_DELAY_MS must be >= 0"
        ):
            load_config(config_path)

    def test_load_config_rejects_invalid_coordinate_format(self) -> None:
        """Coordinates must stay in strict x,y form."""
        config_path = self._write_config(
            [
                "WIDTH=9",
                "HEIGHT=7",
                "ENTRY=0;0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=True",
            ]
        )

        with self.assertRaisesRegex(
            ConfigError, "ENTRY must be in 'x,y' format"
        ):
            load_config(config_path)

    def test_load_config_rejects_out_of_bounds_entry(self) -> None:
        """Entry coordinates must fit inside the configured maze."""
        config_path = self._write_config(
            [
                "WIDTH=9",
                "HEIGHT=7",
                "ENTRY=9,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=True",
            ]
        )

        with self.assertRaisesRegex(ConfigError, "ENTRY out of bounds"):
            load_config(config_path)

    def test_load_config_rejects_same_entry_and_exit(self) -> None:
        """Entry and exit must remain distinct cells."""
        config_path = self._write_config(
            [
                "WIDTH=9",
                "HEIGHT=7",
                "ENTRY=0,0",
                "EXIT=0,0",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=True",
            ]
        )

        with self.assertRaisesRegex(
            ConfigError, "ENTRY and EXIT must be different"
        ):
            load_config(config_path)

    def test_load_config_accepts_comments_and_blank_lines(self) -> None:
        """Whole-line comments and blank lines should be ignored."""
        config_path = self._write_config(
            [
                "# Maze dimensions",
                "",
                "WIDTH=9",
                "HEIGHT=7",
                "",
                "# Path endpoints",
                "ENTRY=0,0",
                "EXIT=8,6",
                "OUTPUT_FILE=maze.txt",
                "PERFECT=on",
            ]
        )

        cfg = load_config(config_path)

        self.assertEqual(cfg.width, 9)
        self.assertEqual(cfg.exit, (8, 6))
        self.assertTrue(cfg.perfect)


class GeneratorTests(unittest.TestCase):
    """Cover reusable generator guarantees."""

    def test_generator_requires_generate_before_read_operations(self) -> None:
        """Read APIs should fail before maze generation has happened."""
        generator = MazeGenerator(
            width=9,
            height=7,
            entry=(0, 0),
            exit=(8, 6),
            perfect=True,
            seed=42,
        )

        with self.assertRaisesRegex(RuntimeError, "call generate"):
            generator.solve_shortest()
        with self.assertRaisesRegex(RuntimeError, "call generate"):
            generator.to_hex_lines()
        with self.assertRaisesRegex(RuntimeError, "call generate"):
            _ = generator.blocked_cells

    def test_generator_rejects_invalid_constructor_arguments(self) -> None:
        """Constructor validation should guard obvious invalid setups."""
        with self.assertRaisesRegex(ValueError, "must be > 0"):
            MazeGenerator(0, 7, (0, 0), (0, 1))
        with self.assertRaisesRegex(ValueError, "must be different"):
            MazeGenerator(9, 7, (0, 0), (0, 0))
        with self.assertRaisesRegex(TypeError, "must be a tuple"):
            MazeGenerator(9, 7, [0, 0], (8, 6))

    def test_generator_rejects_invalid_step_stride(self) -> None:
        """Generation callback stride must stay positive."""
        generator = MazeGenerator(
            width=9,
            height=7,
            entry=(0, 0),
            exit=(8, 6),
            perfect=True,
            seed=42,
        )

        with self.assertRaisesRegex(ValueError, "step_stride must be > 0"):
            generator.generate_with_callback(step_stride=0)

    def test_generator_is_deterministic_with_seed(self) -> None:
        """Same seed and settings should produce the same hex maze."""
        first = MazeGenerator(9, 7, (0, 0), (8, 6), True, 42)
        second = MazeGenerator(9, 7, (0, 0), (8, 6), True, 42)

        first.generate()
        second.generate()

        self.assertEqual(first.to_hex_lines(), second.to_hex_lines())
        self.assertEqual(first.path_moves(), second.path_moves())

    def test_generator_supports_small_mazes_without_42_stamp(self) -> None:
        """Generation should still work when the maze is too small for 42."""
        generator = MazeGenerator(
            width=3,
            height=3,
            entry=(0, 0),
            exit=(2, 2),
            perfect=True,
            seed=7,
        )

        generator.generate()

        self.assertEqual(generator.blocked_cells, set())
        self.assertEqual(generator.solve_shortest()[0], (0, 0))
        self.assertEqual(generator.solve_shortest()[-1], (2, 2))

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

    def test_generator_rejects_out_of_bounds_cell_lookup(self) -> None:
        """Cell wall reads should enforce maze bounds."""
        generator = MazeGenerator(
            width=9,
            height=7,
            entry=(0, 0),
            exit=(8, 6),
            perfect=True,
            seed=42,
        )

        generator.generate()

        with self.assertRaisesRegex(ValueError, "cell out of bounds"):
            generator.get_cell_walls(9, 0)


class AsciiRendererTests(unittest.TestCase):
    """Keep the fallback renderer plain-text safe and usable."""

    def _build_generator(self) -> tuple[object, MazeGenerator]:
        """Create a generated maze using the default project config."""
        cfg = load_config(ROOT / "config.txt")
        generator = MazeGenerator(
            cfg.width,
            cfg.height,
            cfg.entry,
            cfg.exit,
            cfg.perfect,
            cfg.seed,
        )
        generator.generate()
        return cfg, generator

    def test_build_ascii_lines_uses_plain_ascii_only(self) -> None:
        """Maze canvas should stay restricted to ASCII characters."""
        cfg, generator = self._build_generator()

        maze_lines = build_ascii_lines(cfg, generator, show_path=True)

        self.assertEqual(len(maze_lines), cfg.height * 2 + 1)
        self.assertTrue(all(line.isascii() for line in maze_lines))
        self.assertTrue(any("S" in line for line in maze_lines))
        self.assertTrue(any("G" in line for line in maze_lines))
        self.assertTrue(any("." in line for line in maze_lines))
        self.assertTrue(any("#" in line for line in maze_lines))

    def test_render_ascii_returns_ascii_panels_and_maze(self) -> None:
        """Static ASCII render should avoid Unicode box-drawing glyphs."""
        cfg, generator = self._build_generator()

        rendered = render_ascii(cfg, generator, show_path=False)

        self.assertTrue(rendered.isascii())
        self.assertIn("A-Maze-ing", rendered)
        self.assertIn("plain ASCII fallback", rendered)

    def test_run_ascii_ui_falls_back_to_static_render_without_tty(self) -> None:
        """ASCII UI should not prompt when stdin/stdout are not terminals."""
        cfg, generator = self._build_generator()

        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdout.isatty", return_value=False):
                with patch("builtins.input") as fake_input:
                    run_ascii_ui(cfg, generator, regenerate=None)

        fake_input.assert_not_called()


if __name__ == "__main__":
    try:
        SUITE = unittest.defaultTestLoader.loadTestsFromModule(
            sys.modules[__name__]
        )
        RESULT = FancyTestRunner(verbosity=0).run(SUITE)
        raise SystemExit(0 if RESULT.wasSuccessful() else 1)
    except KeyboardInterrupt:
        print("\nERROR interrupted by user")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR test runner failed: {exc}")
        raise SystemExit(1)
