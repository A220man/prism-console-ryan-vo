"""Product version from the repository VERSION file."""

from pathlib import Path


def read_version() -> str:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "VERSION"
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
    return "0.0.0"
