"""PostToolUse hook: format and lint Python files after Claude edits them.

Launched by .claude/settings.json on every Write/Edit. Reads the hook payload on
stdin, and no-ops unless the edited file is a .py file inside this project.

Deliberately stdlib-only and launched with whatever `python` is on PATH: this is
hook infrastructure, not project code, so it must keep working when .venv is
missing or half-built. The tools it *runs* always come from .venv — never from
system Python.

Silently skips when ruff is not installed yet, so a half-provisioned environment
never blocks an edit. Exit code 2 hands ruff's complaint back to Claude to fix.

mypy is intentionally not run here: per-file type checking in a src-layout
produces spurious import errors. lefthook.yml runs `mypy src` at commit time.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:  # includes json.JSONDecodeError
        return 0

    # Tolerate more than one payload shape: a silently-wrong field name would
    # turn this hook into a permanent no-op with no visible symptom.
    raw_path = (
        (payload.get("tool_input") or {}).get("file_path")
        or (payload.get("tool_response") or {}).get("filePath")
        or payload.get("file_path")
    )
    if not raw_path or not str(raw_path).endswith(".py"):
        return 0

    target = Path(raw_path)
    if not target.is_file():
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    bin_dir = root / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    ruff = bin_dir / ("ruff.exe" if os.name == "nt" else "ruff")
    if not ruff.exists():
        return 0

    problems: list[str] = []
    for args in (["format", str(target)], ["check", "--fix", str(target)]):
        result = subprocess.run(
            [str(ruff), *args],
            capture_output=True,
            text=True,
            cwd=root,
            check=False,
        )
        if result.returncode != 0:
            problems.append(f"{result.stdout}{result.stderr}".strip())

    if problems:
        print("\n\n".join(p for p in problems if p), file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
