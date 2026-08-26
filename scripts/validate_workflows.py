#!/usr/bin/env python3
"""Check that every workflow in the factory parses and stays inside its limits.

A reusable workflow that does not parse fails in the caller's repo, where the
error message is furthest from the person who can fix it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
TEMPLATES = ROOT / "templates"

# An agent that can rewrite its own gates has no gates.
FORBIDDEN_PERMISSIONS = {"actions": {"write"}}

errors: list[str] = []


def check(path: Path) -> None:
    try:
        # YAML parses the bare `on:` key as True. That is correct YAML and the
        # workflow still runs; we just have to look it up under both spellings.
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        errors.append(f"{path.relative_to(ROOT)}: does not parse as YAML: {exc}")
        return
    if not isinstance(data, dict):
        errors.append(f"{path.relative_to(ROOT)}: top level is not a mapping")
        return

    triggers = data.get("on", data.get(True))
    if triggers is None:
        errors.append(f"{path.relative_to(ROOT)}: has no 'on' trigger block")

    for job_name, job in (data.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        permissions = job.get("permissions") or {}
        if isinstance(permissions, dict):
            for scope, banned in FORBIDDEN_PERMISSIONS.items():
                if permissions.get(scope) in banned:
                    errors.append(
                        f"{path.relative_to(ROOT)}: job {job_name!r} requests "
                        f"{scope}: {permissions[scope]}, which agents must never hold"
                    )
        if "uses" in job:
            continue
        if "timeout-minutes" not in job:
            errors.append(
                f"{path.relative_to(ROOT)}: job {job_name!r} has no timeout-minutes"
            )

    top_permissions = data.get("permissions") or {}
    if isinstance(top_permissions, dict):
        for scope, banned in FORBIDDEN_PERMISSIONS.items():
            if top_permissions.get(scope) in banned:
                errors.append(
                    f"{path.relative_to(ROOT)}: requests {scope}: "
                    f"{top_permissions[scope]}, which agents must never hold"
                )


def main() -> int:
    paths = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if TEMPLATES.is_dir():
        paths += sorted(TEMPLATES.rglob("*.yml")) + sorted(TEMPLATES.rglob("*.yaml"))
    if not paths:
        print("guard: no workflows found")
        return 1
    for path in paths:
        check(path)
    if errors:
        print(f"guard: {len(errors)} problem(s)\n")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"guard: {len(paths)} workflow(s) parse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
