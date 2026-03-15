"""Main entrypoint for A-Maze-ing."""

from __future__ import annotations

import sys
from pathlib import Path

from app.errors import ConfigError, OutputError, RenderError
from app.parser import MazeConfig, load_config
from app.renderer_ascii import render_ascii
from app.renderer_curses import run_curses_ui
from app.writer import write_output
from mazegen import MazeGenerator


def _build_generator(cfg: MazeConfig) -> MazeGenerator:
    """Construct the generator from validated configuration."""
    return MazeGenerator(
        width=cfg.width,
        height=cfg.height,
        entry=cfg.entry,
        exit=cfg.exit,
        perfect=cfg.perfect,
        seed=cfg.seed,
        algo=cfg.algo,
    )


def _generate_and_write(cfg: MazeConfig, generator: MazeGenerator) -> None:
    """Generate maze data and write output file."""
    try:
        generator.generate()
    except (ValueError, RuntimeError) as exc:
        if "too small for 42 stamp" in str(exc):
            warning = "Warning: maze too small for visible 42 pattern."
            print(warning, file=sys.stderr)
        raise RuntimeError(f"maze generation failed: {exc}") from exc

    try:
        write_output(cfg.output_file, cfg, generator)
    except OSError as exc:
        msg = f"could not write output file '{cfg.output_file}': {exc}"
        raise OutputError(msg) from exc
    except ValueError as exc:
        raise OutputError(f"invalid generated data: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    """Application entrypoint."""
    args = sys.argv[1:] if argv is None else argv[1:]
    config_path = Path(args[0]) if args else Path("config.txt")

    try:
        cfg = load_config(config_path)
        generator = _build_generator(cfg)
        _generate_and_write(cfg, generator)

        def regenerate_and_save() -> None:
            _generate_and_write(cfg, generator)

        try:
            run_curses_ui(cfg, generator, regenerate=regenerate_and_save)
        except RenderError as exc:
            print(
                f"Warning: {exc}. Falling back to ASCII view.",
                file=sys.stderr,
            )
            render_ascii(cfg, generator, show_path=False)
    except (
        ConfigError,
        OutputError,
        RenderError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: OS failure: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
