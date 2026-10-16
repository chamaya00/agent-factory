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
PRIVILEGE_STEP = "A change to privilege is declared, not slipped in"


def check_privilege_cannot_arrive_undeclared() -> None:
    """A widening of what the automation may do cannot be silent.

    The merge gate in the house-rules skill asks the person merging to look for
    a new permission, a new secret, an action nobody vetted. That gate is prose,
    and under a standing "merge when green" the person applying it may be a
    session acting on an owner's instruction while the owner is asleep. This is
    the one item on that list with a machine behind it, so it has to survive an
    edit that quietly drops it - including an exemption for maintainers, which
    would exempt exactly the case the check is for.
    """
    path = WORKFLOWS / "project-guard.yml"
    data = yaml.safe_load(path.read_text())
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if step.get("name") != PRIVILEGE_STEP:
                continue
            script = step.get("run") or ""
            for pattern, why in (
                ("permissions:", "a token permission"),
                ("secrets[.:]", "a secret"),
                ("pull_request_target", "a trigger that runs a fork's code"),
                ("uses:", "an action the repository will execute"),
            ):
                if pattern not in script:
                    errors.append(
                        f"project-guard.yml: the {PRIVILEGE_STEP!r} step no "
                        f"longer looks for {why}."
                    )
            # Reading the body out of the event payload alone makes the
            # check unfixable under a re-run: the payload is replayed frozen,
            # so a corrected declaration is invisible to every attempt after
            # the first. Observed twice on one pull request before anybody
            # worked out that clicking re-run could not possibly help.
            if "gh pr view" not in script or "--json body" not in script:
                errors.append(
                    f"project-guard.yml: the {PRIVILEGE_STEP!r} step does not "
                    "read the pull request body live, so a re-run replays the "
                    "body the pull request opened with and a corrected "
                    "declaration can never clear it."
                )
            # Anchoring is what is being protected here, not the exact prefix.
            # The pattern may tolerate a heading or a bold lead-in - a
            # declaration written `## Privilege change: ...` reads as correct to
            # everyone except a regex demanding a bare line start - but it still
            # has to be anchored, or the phrase quoted mid-sentence passes and
            # the check means nothing.
            if not re.search(r"grep -qE '\^[^']*Privilege change:[^']*'", script):
                errors.append(
                    f"project-guard.yml: the {PRIVILEGE_STEP!r} step does not "
                    "match the declaration with a line-anchored pattern, so the "
                    "phrase quoted anywhere in a body would pass it."
                )

            # Two failures, and they must not share a sentence. A body with no
            # declaration and a body whose declaration is wrapped in backticks
            # both exit 1, and the generic text tells the second author to go
            # and write a declaration their body already contains - which reads
            # as the check being broken rather than as two characters needing
            # deleting, and sent one real incident an hour in the wrong
            # direction. Collapsing them back into one message is the
            # regression this asserts against, so it wants both the second
            # anchored test and the sentence that distinguishes them.
            anchored = re.findall(r"grep -qE '\^[^']*Privilege change:[^']*'", script)
            if len(anchored) < 2 or "no line begins with it" not in script:
                errors.append(
                    f"project-guard.yml: the {PRIVILEGE_STEP!r} step has one "
                    "message for two different failures. A declaration the "
                    "formatting hid has to be told that it is there and not "
                    "starting its line, separately from a body that never "
                    "declared anything."
                )
            # The documentation exclusion is a narrowing, and a narrowing is
            # how a check dies quietly: one more extension each time it is
            # inconvenient, until nothing is read. Markdown cannot grant a
            # permission; a workflow, a script, or a lockfile can. So read the
            # alternation itself rather than looking for a substring - the
            # first version of this check matched ".yml" and sailed past a
            # pattern that had grown "|yml)".
            exclusion = re.search(r"grep -vE '\\\.\(([^)]*)\)\$'", script)
            if exclusion is None:
                errors.append(
                    f"project-guard.yml: cannot find the file-type exclusion "
                    f"in the {PRIVILEGE_STEP!r} step, so nothing here can say "
                    "what it lets through."
                )
            else:
                allowed = {"md", "markdown", "txt", "rst", "adoc"}
                excluded = {e.strip() for e in exclusion.group(1).split("|")}
                for extension in sorted(excluded - allowed):
                    errors.append(
                        f"project-guard.yml: the {PRIVILEGE_STEP!r} step "
                        f"excludes .{extension} files from the scan. Only "
                        "documentation may be excluded - anything that runs "
                        "has to be read."
                    )
            if "MAINTAINERS" in script or "AUTHOR" in script:
                errors.append(
                    f"project-guard.yml: the {PRIVILEGE_STEP!r} step exempts "
                    "some authors. A pull request merged on the owner's behalf "
                    "is authored by a maintainer, and that is the case this "
                    "check exists for."
                )
            return
    errors.append(
        f"project-guard.yml: no {PRIVILEGE_STEP!r} step. Nothing then stops a "
        "diff widening what the automation may do without saying so."
    )


def check_the_guard_reruns_when_the_body_changes() -> None:
    """A check that reads a pull request body has to re-run when it changes.

    project-guard refuses a widening diff whose body carries no line starting
    `Privilege change:`. The body is the thing under test, and a body is edited
    far more often than it is pushed to - so a caller listening only for the
    default pull_request types (opened, synchronize, reopened) can reject a
    missing declaration and then have no way to observe one being added. The
    author's exits are a manual re-run or an empty commit, and the house rules
    forbid the second by name.

    Found by writing the declaration inside backticks, where it no longer
    starts a line. The check was right, the fix was one character, and applying
    it needed a click nothing in the repository told anybody to make.
    """
    template = TEMPLATES / "project" / ".github" / "workflows" / "guard.yml"
    if not template.exists():
        return
    data = yaml.safe_load(template.read_text())
    triggers = (data or {}).get("on", (data or {}).get(True)) or {}
    if "pull_request" not in triggers:
        errors.append(
            f"{template.relative_to(ROOT)}: no pull_request trigger, so "
            "nothing guards a pull request at all."
        )
        return
    types = (triggers.get("pull_request") or {}).get("types")
    if not types:
        errors.append(
            f"{template.relative_to(ROOT)}: the pull_request trigger names no "
            "`types`, so it takes the default set, which has no `edited` - "
            "correcting a body this guard rejected cannot re-run the guard "
            "that reads it."
        )
        return
    if "edited" not in types:
        errors.append(
            f"{template.relative_to(ROOT)}: the pull_request trigger does not "
            "list `edited`, so correcting a body this guard rejected cannot "
            "re-run the guard that reads it."
        )
    # Only once `types` is named, because naming it replaces the default set
    # rather than extending it: the three that were free by default now have
    # to be written out, and dropping one would not fail anything visibly - it
    # would just quietly stop guarding those pull requests.
    for required in ("opened", "synchronize", "reopened"):
        if required not in types:
            errors.append(
                f"{template.relative_to(ROOT)}: `types` is named, which "
                f"replaces the default set, and `{required}` is not in it - "
                "those pull requests would go unguarded."
            )


def check_the_gate_does_not_rename_itself() -> None:
    """The ci job name is what branch protection matches on, so it must not
    differ between the placeholder gate and the real one.

    This is a lesson with a scar behind it. The template used to ship
    `check-name: scaffolding` while the reusable workflow defaulted to the four
    Node script names, so a project that replaced its placeholder gate also
    renamed its required check - and a required check that stops reporting
    blocks every merge rather than gating them, including the pull request
    doing the replacing. The fix was one stable name on both paths, and the
    only way that stays true is if something fails when the two drift apart.
    """
    reusable = WORKFLOWS / "ci.yml"
    template = TEMPLATES / "project" / ".github" / "workflows" / "ci.yml"
    if not reusable.is_file() or not template.is_file():
        return

    default = ((yaml.safe_load(reusable.read_text()) or {}).get(True) or {})
    default = ((default.get("workflow_call") or {}).get("inputs") or {})
    default = (default.get("check-name") or {}).get("default")

    shipped = (yaml.safe_load(template.read_text()) or {}).get("jobs") or {}
    shipped = ((shipped.get("ci") or {}).get("with") or {}).get("check-name")

    if default is None or shipped is None:
        errors.append(
            "ci.yml: could not read check-name from the reusable workflow's "
            "default and the project template's caller. One of them stopped "
            "declaring it, and the name branch protection matches on is no "
            "longer pinned to anything."
        )
        return

    if default != shipped:
        errors.append(
            f"ci.yml: the reusable workflow defaults check-name to {default!r} "
            f"but the project template ships {shipped!r}. A project that "
            "swaps its placeholder gate for the real one would rename its "
            "required check, and a required check that no longer reports "
            "blocks every merge - including the pull request doing the swap. "
            "Keep one name on both paths."
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
    check_privilege_cannot_arrive_undeclared()
    check_the_guard_reruns_when_the_body_changes()
    check_the_gate_does_not_rename_itself()
    if errors:
        print(f"guard: {len(errors)} problem(s)\n")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"guard: {len(paths)} workflow(s) parse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
