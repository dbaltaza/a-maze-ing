"""Minimal PEP 517 backend for offline wheel/sdist builds."""

from __future__ import annotations

import base64
import hashlib
import os
import tarfile
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = ROOT / "mazegen"


def _project_metadata() -> dict[str, str]:
    """Read the core project metadata from pyproject.toml."""
    pyproject = ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data["project"]
    return {
        "name": project["name"],
        "version": project["version"],
        "summary": project.get("description", ""),
        "requires_python": project.get("requires-python", ""),
    }


def _dist_info_name(name: str, version: str) -> str:
    """Return the normalized dist-info directory name."""
    normalized = name.replace("-", "_")
    return f"{normalized}-{version}.dist-info"


def _wheel_filename(name: str, version: str) -> str:
    """Return the normalized wheel filename."""
    normalized = name.replace("-", "_")
    return f"{normalized}-{version}-py3-none-any.whl"


def _metadata_text(meta: dict[str, str]) -> str:
    """Build the wheel METADATA file contents."""
    return (
        "Metadata-Version: 2.1\n"
        f"Name: {meta['name']}\n"
        f"Version: {meta['version']}\n"
        f"Summary: {meta['summary']}\n"
        f"Requires-Python: {meta['requires_python']}\n"
    )


def _wheel_text() -> str:
    """Build the wheel WHEEL file contents."""
    return (
        "Wheel-Version: 1.0\n"
        "Generator: mazegen.build_backend\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    )


def _iter_package_files() -> list[Path]:
    """Return package files that must be included in built artifacts."""
    files: list[Path] = []
    for path in sorted(PACKAGE_DIR.rglob("*")):
        if path.is_dir():
            continue
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def _zipinfo(path: str) -> ZipInfo:
    """Return deterministic ZipInfo metadata for one archive member."""
    z = ZipInfo(path)
    z.date_time = (2020, 1, 1, 0, 0, 0)
    z.compress_type = ZIP_DEFLATED
    return z


def _record_hash(data: bytes) -> str:
    """Return the PEP 427 hash fragment for one file payload."""
    digest = hashlib.sha256(data).digest()
    b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"sha256={b64}"


def _write_metadata_dir(base: Path, dist_info: str) -> str:
    """Write wheel metadata files into a prepared directory."""
    md_dir = base / dist_info
    md_dir.mkdir(parents=True, exist_ok=True)
    meta = _project_metadata()
    (md_dir / "METADATA").write_text(_metadata_text(meta), encoding="utf-8")
    (md_dir / "WHEEL").write_text(_wheel_text(), encoding="utf-8")
    (md_dir / "top_level.txt").write_text("mazegen\n", encoding="utf-8")
    return dist_info


def get_requires_for_build_wheel(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    """Return build requirements for wheel generation."""
    del config_settings
    return []


def get_requires_for_build_sdist(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    """Return build requirements for sdist generation."""
    del config_settings
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    """Create the dist-info metadata directory for a wheel build."""
    del config_settings
    meta = _project_metadata()
    dist_info = _dist_info_name(meta["name"], meta["version"])
    _write_metadata_dir(Path(metadata_directory), dist_info)
    return dist_info


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Build a pure-Python wheel into the requested directory."""
    del config_settings
    del metadata_directory
    meta = _project_metadata()
    dist_info = _dist_info_name(meta["name"], meta["version"])
    wheel_name = _wheel_filename(meta["name"], meta["version"])
    wheel_path = Path(wheel_directory) / wheel_name
    os.makedirs(wheel_directory, exist_ok=True)

    records: list[tuple[str, str, str]] = []
    record_path = f"{dist_info}/RECORD"

    with ZipFile(wheel_path, "w", compression=ZIP_DEFLATED) as zf:
        for file_path in _iter_package_files():
            rel = file_path.relative_to(ROOT).as_posix()
            data = file_path.read_bytes()
            zf.writestr(_zipinfo(rel), data)
            records.append((rel, _record_hash(data), str(len(data))))

        metadata_files = {
            f"{dist_info}/METADATA": _metadata_text(meta).encode("utf-8"),
            f"{dist_info}/WHEEL": _wheel_text().encode("utf-8"),
            f"{dist_info}/top_level.txt": b"mazegen\n",
        }
        for rel, data in metadata_files.items():
            zf.writestr(_zipinfo(rel), data)
            records.append((rel, _record_hash(data), str(len(data))))

        rows: list[list[str]] = [[a, b, c] for a, b, c in records]
        rows.append([record_path, "", ""])
        out = []
        for row in rows:
            out.append(",".join(row))
        record_bytes = ("\n".join(out) + "\n").encode("utf-8")
        zf.writestr(_zipinfo(record_path), record_bytes)

    return wheel_name


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    """Build a source distribution into the requested directory."""
    del config_settings
    meta = _project_metadata()
    root_name = f"{meta['name']}-{meta['version']}"
    os.makedirs(sdist_directory, exist_ok=True)
    sdist_name = f"{root_name}.tar.gz"
    sdist_path = Path(sdist_directory) / sdist_name

    include_files = [
        ROOT / "pyproject.toml",
        ROOT / "README.md",
        * _iter_package_files(),
    ]
    with tarfile.open(sdist_path, "w:gz") as tf:
        for src in include_files:
            arcname = f"{root_name}/{src.relative_to(ROOT).as_posix()}"
            tf.add(src, arcname=arcname)

    return sdist_name
