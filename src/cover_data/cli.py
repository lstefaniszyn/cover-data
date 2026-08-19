from __future__ import annotations

import importlib.metadata
from typing import Annotated

import typer

app = typer.Typer()


def _version_callback(value: bool) -> None:
    if value:
        try:
            typer.echo(importlib.metadata.version("cover-data"))
        except importlib.metadata.PackageNotFoundError:
            typer.echo("cover-data is not installed as a package.", err=True)
            raise typer.Exit(code=1) from None
        raise typer.Exit()


@app.callback()
def _app_callback(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """Cover the Data — redact every debtor row except one from a scanned list."""


def _not_yet_implemented(slice_id: str) -> None:
    typer.echo(f"Not yet implemented — see roadmap slice {slice_id}.")
    raise typer.Exit(code=1)


@app.command()
def inspect() -> None:
    """Show reconstructed table rows with OCR confidence flagged. (S-01)"""
    _not_yet_implemented("S-01")


@app.command()
def search() -> None:
    """Search rows by name and confirm/preview a match. (S-02)"""
    _not_yet_implemented("S-02")


@app.command()
def redact() -> None:
    """Generate the person-selective redacted PDF. (S-03)"""
    _not_yet_implemented("S-03")
