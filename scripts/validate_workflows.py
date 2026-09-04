#!/usr/bin/env python3
"""Check that every workflow in the factory parses and stays inside its limits.

A reusable workflow that does not parse fails in the caller's repo, where the
error message is furthest from the person who can fix it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
TEMPLATES = ROOT / "plugins" / "agent-factory" / "templates"

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


# Tools a role can declare that the action does not grant on its own. An agent
# started without them does not fail cleanly, it improvises: it spends the run
# and leaves a comment explaining that it had no tools. Bash is checked as a
# family, since the allowlist grants it one scoped command at a time.
GRANTABLE = ("Write", "Edit", "WebFetch", "WebSearch", "Bash")

AGENTS = ROOT / "plugins" / "agent-factory" / "agents"
ALLOWLIST_STEP = "Resolve the tool allowlist for this role"


def declared_tools(path: Path) -> set[str]:
    """The tools named on the `tools:` line of a role definition's frontmatter."""
    for line in path.read_text().splitlines():
        if line.startswith("tools:"):
            return {tool.strip() for tool in line[len("tools:") :].split(",")}
    return set()


def granted_tools(branch: str, common: str) -> set[str]:
    """The tool names a `case` branch actually assigns to `tools`.

    Parsed rather than substring-matched: the prose in a comment above a branch
    ("Writes code, runs the tests") contains the name of a tool the branch may
    not grant, and a guard that matches that passes a broken allowlist.
    """
    names: set[str] = set()
    for line in branch.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        match = re.match(r'tools="(.*)"\s*$', line)
        if not match:
            continue
        value = match.group(1).replace("$common", common).replace("$tools", "")
        names.update(name.strip() for name in value.split(",") if name.strip())
    return names


def check_roles_can_work() -> None:
    """Every role must be granted the tools its own definition declares.

    This is the check for the failure that produced it: agent-run passed no
    allowlist, so every role ran with a read-only tool set. The orchestrator
    surfaced it first because it runs first, but the engineer was worse off - it
    could not have written a line of code or run a test.
    """
    workflow = WORKFLOWS / "agent-run.yml"
    if not workflow.exists():
        errors.append("agent-run.yml is missing; nothing grants the roles their tools")
        return
    if not AGENTS.is_dir():
        errors.append(f"no role definitions under {AGENTS.relative_to(ROOT)}")
        return

    data = yaml.safe_load(workflow.read_text())
    script = ""
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if isinstance(step, dict) and step.get("name") == ALLOWLIST_STEP:
                script = step.get("run") or ""
    if not script:
        errors.append(
            f".github/workflows/agent-run.yml: no {ALLOWLIST_STEP!r} step. "
            "Without one the action's read-only default is what every role gets."
        )
        return

    # `common` is built up over several lines; fold them into one value so a
    # branch that only says "$common" is checked against what it really gets.
    common = ""
    for line in script.splitlines():
        match = re.match(r"""common=['"](.*)['"]\s*$""", line.strip())
        if match:
            common = match.group(1).replace("$common", common)

    for role_file in sorted(AGENTS.glob("*.md")):
        role = role_file.stem
        # The branch of the case statement that belongs to this role: from its
        # label to the `;;` that closes it.
        start = script.find(f"{role})")
        if start == -1:
            errors.append(
                f".github/workflows/agent-run.yml: no allowlist branch for role "
                f"{role!r}, so it would run with the read-only default"
            )
            continue
        end = script.find(";;", start)
        branch = script[start : end if end != -1 else len(script)]
        granted = granted_tools(branch, common)

        for tool in sorted(declared_tools(role_file) & set(GRANTABLE)):
            if tool == "Bash":
                ok = any(name.startswith("Bash(") for name in granted)
            else:
                ok = tool in granted
            if not ok:
                errors.append(
                    f"role {role!r} declares {tool} but the agent-run allowlist "
                    f"does not grant it; the role cannot do its job"
                )


def main() -> int:
    paths = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if TEMPLATES.is_dir():
        # Only what sits in .github/workflows/ is a workflow. A template may
        # carry other YAML - a Pages config, for one - and demanding an `on:`
        # block of those fails the guard for a reason that has nothing to do
        # with workflows.
        paths += sorted(
            path
            for pattern in ("*.yml", "*.yaml")
            for path in TEMPLATES.rglob(pattern)
            if path.parent.name == "workflows" and path.parent.parent.name == ".github"
        )
    if not paths:
        print("guard: no workflows found")
        return 1
    for path in paths:
        check(path)
    check_roles_can_work()
    if errors:
        print(f"guard: {len(errors)} problem(s)\n")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"guard: {len(paths)} workflow(s) parse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
