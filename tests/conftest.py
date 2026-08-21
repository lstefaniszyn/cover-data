"""Shared pytest fixtures giving tests typed access to `context/test_images/`.

`generate_edge_cases.py` is fixture tooling, not product code (see its module
docstring) -- Pillow/numpy are deliberately not project dependencies there.
They arrive transitively via the OCR stack added in Phase 2, so importing the
generator module from tests is safe without adding it as a direct dependency.
`manifest.json` is the authoritative fixture index (see
`context/test_images/README.md`); these fixtures parse it once per session
rather than letting each test re-implement that.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

TEST_IMAGES_DIR = Path(__file__).resolve().parent.parent / "context" / "test_images"
MANIFEST_PATH = TEST_IMAGES_DIR / "manifest.json"

if str(TEST_IMAGES_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_IMAGES_DIR))


@dataclass(frozen=True)
class FixtureEntry:
    """One `manifest.json` fixture entry, typed for test consumption."""

    filename: str
    generated: bool
    layout: str | None
    ground_truth_rows: list[dict[str, Any]] | None
    geometry: dict[str, Any] | None
    search_scenarios: list[dict[str, Any]]
    raw: dict[str, Any]

    @property
    def path(self) -> Path:
        return TEST_IMAGES_DIR / self.filename


def _load_entries() -> list[FixtureEntry]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [
        FixtureEntry(
            filename=entry["filename"],
            generated=entry["generated"],
            layout=entry.get("layout"),
            ground_truth_rows=entry.get("ground_truth_rows"),
            geometry=entry.get("geometry"),
            search_scenarios=entry.get("search_scenarios", []),
            raw=entry,
        )
        for entry in data["fixtures"]
    ]


def _ids(entries: list[FixtureEntry]) -> list[str]:
    return [entry.filename for entry in entries]


_ALL_ENTRIES = _load_entries()
_GENERATED_ENTRIES = [e for e in _ALL_ENTRIES if e.generated]
_ORIGINAL_ENTRIES = [e for e in _ALL_ENTRIES if not e.generated]


@pytest.fixture(scope="session")
def manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def fixture_entries() -> list[FixtureEntry]:
    return _ALL_ENTRIES


@pytest.fixture(params=_ALL_ENTRIES, ids=_ids(_ALL_ENTRIES))
def any_fixture(request: pytest.FixtureRequest) -> FixtureEntry:
    """Parametrized over all 26 fixtures, id'd by filename."""
    fixture_entry: FixtureEntry = request.param
    return fixture_entry


@pytest.fixture(params=_GENERATED_ENTRIES, ids=_ids(_GENERATED_ENTRIES))
def generated_fixture(request: pytest.FixtureRequest) -> FixtureEntry:
    """Parametrized over the 20 script-generated fixtures (`7.png`-`26.png`):
    content and geometry ground truth are both available."""
    fixture_entry: FixtureEntry = request.param
    return fixture_entry


@pytest.fixture(params=_ORIGINAL_ENTRIES, ids=_ids(_ORIGINAL_ENTRIES))
def original_fixture(request: pytest.FixtureRequest) -> FixtureEntry:
    """Parametrized over the 6 image-model fixtures (`1.png`-`6.png`):
    structural assertions only, no ground truth."""
    fixture_entry: FixtureEntry = request.param
    return fixture_entry
