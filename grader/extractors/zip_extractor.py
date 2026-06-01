from __future__ import annotations

import tempfile
from pathlib import Path
from zipfile import ZipFile


def extract_zip(path: str | Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmpdir = tempfile.TemporaryDirectory(prefix="grader_zip_")
    extract_dir = Path(tmpdir.name)
    with ZipFile(path, "r") as zf:
        zf.extractall(extract_dir)
    return tmpdir, extract_dir
