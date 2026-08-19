"""Smoke test for the packaging wiring.

Guards that the src-layout package is importable from the installed
environment — that uv_build, `src/cover_data/`, and the `.venv` install all
line up. It asserts nothing about behaviour; real coverage arrives with the
first roadmap slice.

It also gives pytest something to collect. An empty suite exits 5, which
lefthook reads as a failed job.
"""

from __future__ import annotations

import importlib


def test_package_is_importable() -> None:
    assert importlib.import_module("cover_data") is not None
