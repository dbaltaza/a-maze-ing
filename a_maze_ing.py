"""Main entrypoint for A-Maze-ing."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

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
    )


def _generate_and_write(
    cfg: MazeConfig,
    generator: MazeGenerator,
    on_step: Callable[[], None] | None = None,
) -> None:
    """Generate maze data and write output file."""
    if cfg.width < 7 or cfg.height < 5:
        warning = (
            "Error: maze too small for visible 42 pattern "
            "(minimum is 7x5). Proceeding without it."
        )
        print(warning, file=sys.stderr)

    try:
        generator.generate_with_callback(on_step=on_step)
    except (ValueError, RuntimeError) as exc:
        raise RuntimeError(f"maze generation failed: {exc}") from exc

    try:
        write_output(cfg.output_file, cfg, generator)
    except OSError as exc:
        msg = f"could not write output file '{cfg.output_file}': {exc}"
        raise OutputError(msg) from exc
    except ValueError as exc:
        raise OutputError(f"invalid generated data: {exc}") from exc


def _announce_renderer(name: str, *, detail: str | None = None) -> None:
    """Print the selected renderer to stderr."""
    message = f"Renderer: {name}"
    if detail:
        message = f"{message} ({detail})"
    print(message, file=sys.stderr)


def _run_renderer(
    cfg: MazeConfig,
    generator: MazeGenerator,
    regenerate_and_save: Callable[[Callable[[], None] | None], None],
) -> None:
    """Run the requested renderer with ASCII fallback when needed."""
    requested = cfg.renderer

    if requested == "ascii":
        _announce_renderer("ascii", detail="requested")
        render_ascii(cfg, generator, show_path=False)
        return

    if requested == "curses":
        _announce_renderer("curses", detail="requested")
        run_curses_ui(
            cfg,
            generator,
            regenerate=regenerate_and_save,
            generate_delay_ms=cfg.generate_delay_ms,
            solve_delay_ms=cfg.solve_delay_ms,
        )
        return

    try:
        _announce_renderer("curses", detail="auto")
        run_curses_ui(
            cfg,
            generator,
            regenerate=regenerate_and_save,
            generate_delay_ms=cfg.generate_delay_ms,
            solve_delay_ms=cfg.solve_delay_ms,
        )
        return
    except RenderError as exc:
        print(f"Warning: curses unavailable: {exc}", file=sys.stderr)

    _announce_renderer("ascii", detail="auto fallback")
    render_ascii(cfg, generator, show_path=False)


def main(argv: list[str] | None = None) -> int:
    """Application entrypoint."""
    args = sys.argv[1:] if argv is None else argv[1:]
    config_path = Path(args[0]) if args else Path("config.txt")

    try:
        cfg = load_config(config_path)
        generator = _build_generator(cfg)
        _generate_and_write(cfg, generator)

        def regenerate_and_save(
            on_step: Callable[[], None] | None = None,
        ) -> None:
            """Regenerate the maze and persist the updated output file."""
            _generate_and_write(cfg, generator, on_step=on_step)

        _run_renderer(cfg, generator, regenerate_and_save)
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
