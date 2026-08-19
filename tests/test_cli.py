from __future__ import annotations

import importlib.metadata

from typer.testing import CliRunner

from cover_data.cli import app

runner = CliRunner()


def test_version_prints_installed_version_and_exits_zero() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == importlib.metadata.version("cover-data")


def test_help_lists_all_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "inspect" in result.output
    assert "search" in result.output
    assert "redact" in result.output


def test_inspect_is_not_yet_implemented() -> None:
    result = runner.invoke(app, ["inspect"])
    assert result.exit_code == 1
    assert "not yet implemented" in result.output.lower()


def test_search_is_not_yet_implemented() -> None:
    result = runner.invoke(app, ["search"])
    assert result.exit_code == 1
    assert "not yet implemented" in result.output.lower()


def test_redact_is_not_yet_implemented() -> None:
    result = runner.invoke(app, ["redact"])
    assert result.exit_code == 1
    assert "not yet implemented" in result.output.lower()
