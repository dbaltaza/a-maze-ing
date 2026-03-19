"""Main entrypoint for A-Maze-ing."""

from __future__ import annotations

import sys
from pathlib import Path

from app.errors import ConfigError, OutputError
from app.parser import MazeConfig, load_config
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
) -> None:
    """Generate maze data and write output file."""
    if cfg.width < 7 or cfg.height < 5:
        warning = (
            "Error: maze too small for visible 42 pattern "
            "(minimum is 7x5). Proceeding without it."
        )
        print(warning, file=sys.stderr)

    try:
        generator.generate()
    except (ValueError, RuntimeError) as exc:
        raise RuntimeError(f"maze generation failed: {exc}") from exc

    try:
        write_output(cfg.output_file, cfg, generator)
    except OSError as exc:
        msg = f"could not write output file '{cfg.output_file}': {exc}"
        raise OutputError(msg) from exc
    except ValueError as exc:
        raise OutputError(f"invalid generated data: {exc}") from exc

    if cfg.renderer == "mlx":
        from app.renderer_mlx import draw_mlx_maze

        draw_mlx_maze(generator, cfg)
    else:
        print(f"Maze successfully saved to {cfg.output_file}")


def main(argv: list[str] | None = None) -> int:
    """Application entrypoint."""
    args = sys.argv[1:] if argv is None else argv[1:]
    config_path = Path(args[0]) if args else Path("config.txt")

    try:
        cfg = load_config(config_path)
        generator = _build_generator(cfg)
        _generate_and_write(cfg, generator)
    except (ConfigError, OutputError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: OS failure: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
