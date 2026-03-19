"""Configuration parsing for the application layer."""

from __future__ import annotations

from pathlib import Path
import re

from pydantic import BaseModel, ConfigDict, ValidationError, ValidationInfo
from pydantic import field_validator, model_validator

from .errors import ConfigError

_REQUIRED_KEYS = {"WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"}
_OPTIONAL_KEYS = {
    "SEED",
    "RENDERER",
    "GENERATE_DELAY_MS",
    "SOLVE_DELAY_MS",
}
_KNOWN_KEYS = _REQUIRED_KEYS | _OPTIONAL_KEYS
_RENDERERS = {"auto", "ascii", "curses"}
_INT_MIN = -(2**31)
_INT_MAX = 2**31 - 1
_INT_PATTERN = re.compile(r"^[+-]?\d+$")


class MazeConfig(BaseModel):
    """Validated maze configuration."""

    model_config = ConfigDict(frozen=True)

    width: int
    height: int
    entry: tuple[int, int]
    exit: tuple[int, int]
    output_file: str
    perfect: bool
    seed: int | None = None
    renderer: str = "auto"
    generate_delay_ms: int = 8
    solve_delay_ms: int = 25

    @field_validator("width", "height")
    @classmethod
    def _validate_dimensions(cls, value: int, info: ValidationInfo) -> int:
        """Require strictly positive maze dimensions."""
        if value <= 0:
            raise ValueError(f"{info.field_name.upper()} must be > 0")
        return value

    @field_validator("output_file")
    @classmethod
    def _validate_output_file(cls, value: str) -> str:
        """Reject empty output targets after trimming whitespace."""
        output_file = value.strip()
        if not output_file:
            raise ValueError("OUTPUT_FILE must not be empty")
        return output_file

    @field_validator("renderer")
    @classmethod
    def _validate_renderer(cls, value: str) -> str:
        """Normalize and validate the configured renderer name."""
        renderer = value.strip().lower() or "auto"
        if renderer not in _RENDERERS:
            raise ValueError(
                f"RENDERER must be one of {', '.join(sorted(_RENDERERS))}"
            )
        return renderer

    @field_validator("generate_delay_ms", "solve_delay_ms")
    @classmethod
    def _validate_delays(cls, value: int, info: ValidationInfo) -> int:
        """Require non-negative animation delays."""
        if value < 0:
            raise ValueError(f"{info.field_name.upper()} must be >= 0")
        return value

    @model_validator(mode="after")
    def _validate_coordinates(self) -> MazeConfig:
        """Ensure entry and exit are distinct and inside maze bounds."""
        if not (
            0 <= self.entry[0] < self.width
            and 0 <= self.entry[1] < self.height
        ):
            raise ValueError(
                f"ENTRY out of bounds for maze {self.width}x{self.height}: "
                f"{self.entry}"
            )
        if not (
            0 <= self.exit[0] < self.width
            and 0 <= self.exit[1] < self.height
        ):
            raise ValueError(
                f"EXIT out of bounds for maze {self.width}x{self.height}: "
                f"{self.exit}"
            )
        if self.entry == self.exit:
            raise ValueError("ENTRY and EXIT must be different")
        return self


def _parse_int(value: str, key: str, *, line_no: int | None = None) -> int:
    """Parse an integer configuration value."""
    raw = value.strip()
    where = f" on line {line_no}" if line_no is not None else ""
    if not _INT_PATTERN.fullmatch(raw):
        raise ConfigError(f"{key} must be an integer{where}")
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer{where}") from exc
    if parsed < _INT_MIN or parsed > _INT_MAX:
        raise ConfigError(
            f"{key} must be between {_INT_MIN} and {_INT_MAX}{where}"
        )
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

    entry_raw, entry_line = raw_values["ENTRY"]
    exit_raw, exit_line = raw_values["EXIT"]
    entry = _parse_coord(entry_raw, "ENTRY", line_no=entry_line)
    exit_ = _parse_coord(exit_raw, "EXIT", line_no=exit_line)

    perfect_raw, perfect_line = raw_values["PERFECT"]
    perfect = _parse_bool(perfect_raw, "PERFECT", line_no=perfect_line)

    output_raw, _output_line = raw_values["OUTPUT_FILE"]
    output_file = output_raw

    seed: int | None = None
    if "SEED" in raw_values:
        seed_raw, seed_line = raw_values["SEED"]
        if seed_raw.strip():
            seed = _parse_int(seed_raw, "SEED", line_no=seed_line)

    if "RENDERER" in raw_values:
        renderer_raw, _renderer_line = raw_values["RENDERER"]
        renderer = renderer_raw
    else:
        renderer = "auto"

    generate_delay_ms = 8
    if "GENERATE_DELAY_MS" in raw_values:
        delay_raw, delay_line = raw_values["GENERATE_DELAY_MS"]
        generate_delay_ms = _parse_int(
            delay_raw, "GENERATE_DELAY_MS", line_no=delay_line
        )

    solve_delay_ms = 25
    if "SOLVE_DELAY_MS" in raw_values:
        delay_raw, delay_line = raw_values["SOLVE_DELAY_MS"]
        solve_delay_ms = _parse_int(
            delay_raw, "SOLVE_DELAY_MS", line_no=delay_line
        )
    try:
        return MazeConfig(
            width=width,
            height=height,
            entry=entry,
            exit=exit_,
            output_file=output_file,
            perfect=perfect,
            seed=seed,
            renderer=renderer,
            generate_delay_ms=generate_delay_ms,
            solve_delay_ms=solve_delay_ms,
        )
    except ValidationError as exc:
        first_error = exc.errors(include_url=False)[0]
        raise ConfigError(first_error["msg"]) from exc
