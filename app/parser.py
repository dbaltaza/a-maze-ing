"""Configuration parsing for the application layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError

_REQUIRED_KEYS = {"WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"}
_OPTIONAL_KEYS = {"SEED", "ALGO"}
_KNOWN_KEYS = _REQUIRED_KEYS | _OPTIONAL_KEYS


@dataclass(frozen=True)
class MazeConfig:
    """Validated maze configuration."""

    width: int
    height: int
    entry: tuple[int, int]
    exit: tuple[int, int]
    output_file: str
    perfect: bool
    seed: int | None = None
    algo: str = "dfs"


def _parse_int(value: str, key: str, *, line_no: int | None = None) -> int:
    """Parse an integer configuration value."""
    try:
        parsed = int(value)
    except ValueError as exc:
        where = f" on line {line_no}" if line_no is not None else ""
        raise ConfigError(f"{key} must be an integer{where}") from exc
    return parsed


def _parse_bool(value: str, key: str, *, line_no: int | None = None) -> bool:
    """Parse a flexible boolean configuration value."""
    normalized = value.strip().lower()
    truthy = {"1", "true", "yes", "y", "on"}
    falsy = {"0", "false", "no", "n", "off"}
    if normalized in truthy:
        return True
    if normalized in falsy:
        return False
    where = f" on line {line_no}" if line_no is not None else ""
    raise ConfigError(f"{key} must be a boolean value{where}")


def _parse_coord(
    value: str,
    key: str,
    *,
    line_no: int | None = None,
) -> tuple[int, int]:
    """Parse coordinates in x,y form."""
    raw = value.strip()
    parts = [part.strip() for part in raw.split(",")]
    where = f" on line {line_no}" if line_no is not None else ""
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ConfigError(f"{key} must be in 'x,y' format{where}")
    x = _parse_int(parts[0], key, line_no=line_no)
    y = _parse_int(parts[1], key, line_no=line_no)
    return (x, y)


def load_config(path: str | Path) -> MazeConfig:
    """Load and validate maze configuration from a file."""
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise ConfigError(f"config file not found: {cfg_path}")
    if not cfg_path.is_file():
        raise ConfigError(f"config path is not a file: {cfg_path}")

    raw_values: dict[str, tuple[str, int]] = {}
    try:
        with cfg_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    raise ConfigError(
                        f"invalid syntax on line {line_no}: expected KEY=VALUE"
                    )

                key_raw, value_raw = stripped.split("=", 1)
                key = key_raw.strip().upper()
                value = value_raw.strip()

                if not key:
                    raise ConfigError(
                        f"invalid syntax on line {line_no}: missing key"
                    )
                if key not in _KNOWN_KEYS:
                    raise ConfigError(f"unknown key '{key}' on line {line_no}")
                if key in raw_values:
                    raise ConfigError(
                        f"duplicate key '{key}' on line {line_no}"
                    )
                raw_values[key] = (value, line_no)
    except OSError as exc:
        raise ConfigError(
            f"failed to read config file '{cfg_path}': {exc}"
        ) from exc

    missing = sorted(_REQUIRED_KEYS - raw_values.keys())
    if missing:
        missing_msg = ", ".join(missing)
        raise ConfigError(f"missing required config key(s): {missing_msg}")

    width_raw, width_line = raw_values["WIDTH"]
    height_raw, height_line = raw_values["HEIGHT"]
    width = _parse_int(width_raw, "WIDTH", line_no=width_line)
    height = _parse_int(height_raw, "HEIGHT", line_no=height_line)
    if width <= 0:
        raise ConfigError("WIDTH must be > 0")
    if height <= 0:
        raise ConfigError("HEIGHT must be > 0")

    entry_raw, entry_line = raw_values["ENTRY"]
    exit_raw, exit_line = raw_values["EXIT"]
    entry = _parse_coord(entry_raw, "ENTRY", line_no=entry_line)
    exit_ = _parse_coord(exit_raw, "EXIT", line_no=exit_line)
    if not (0 <= entry[0] < width and 0 <= entry[1] < height):
        raise ConfigError(
            f"ENTRY out of bounds for maze {width}x{height}: {entry}"
        )
    if not (0 <= exit_[0] < width and 0 <= exit_[1] < height):
        raise ConfigError(
            f"EXIT out of bounds for maze {width}x{height}: {exit_}"
        )
    if entry == exit_:
        raise ConfigError("ENTRY and EXIT must be different")

    perfect_raw, perfect_line = raw_values["PERFECT"]
    perfect = _parse_bool(perfect_raw, "PERFECT", line_no=perfect_line)

    output_raw, _output_line = raw_values["OUTPUT_FILE"]
    output_file = output_raw.strip()
    if not output_file:
        raise ConfigError("OUTPUT_FILE must not be empty")

    seed: int | None = None
    if "SEED" in raw_values:
        seed_raw, seed_line = raw_values["SEED"]
        if seed_raw.strip():
            seed = _parse_int(seed_raw, "SEED", line_no=seed_line)

    if "ALGO" in raw_values:
        algo_raw, _algo_line = raw_values["ALGO"]
        algo = algo_raw.strip().lower() or "dfs"
    else:
        algo = "dfs"

    return MazeConfig(
        width=width,
        height=height,
        entry=entry,
        exit=exit_,
        output_file=output_file,
        perfect=perfect,
        seed=seed,
        algo=algo,
    )
