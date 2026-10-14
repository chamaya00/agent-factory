#!/usr/bin/env python3
"""Prove the capability checks fire on drift and stay quiet on prose.

Three checks now: the two that read a role's prose against its frontmatter, and
the one that reads the same prose against the allowlist a run is actually given.
The first two read English rather than structure, which makes them the only part
of the guard that can be wrong in both directions. A missed claim ships a
false statement to every provisioned repository; a false positive fails pull
requests that changed nothing about capability, and the cure for that is
usually to delete the check. So both directions are pinned here.

The sentences below are the real ones. The drift cases are what `main` carried
before this was written, and the quiet cases are sentences already in the
repository that an earlier, looser version of the pattern fired on.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_plugin as guard

# Each case: a description, the prose, and whether the check should fire.
# Written as the claim only - the checks read one sentence at a time.
DENIAL_CASES = [
    (
        "the sentence the template shipped",
        "The researcher and the designer cannot open pull requests - they push "
        "a branch and leave a link for a human - so their work can be complete "
        "and still invisible to the next agent.",
        True,
    ),
    (
        "one role, singular, spelled with an apostrophe",
        "The designer can't open a pull request for its own spec.",
        True,
    ),
    (
        "the same claim as an inability rather than a permission",
        "The researcher is unable to open a pull request.",
        True,
    ),
    (
        "a sweeping claim that names no role directly",
        "No role in this system can open a pull request for the work it did.",
        True,
    ),
    (
        "a claim about a capability no role holds is true and stays quiet",
        "The orchestrator cannot merge a pull request.",
        False,
    ),
    (
        "a policy restriction on a tool the role holds is not a capability claim",
        "The researcher may not edit this file, and the first engineer pull "
        "request is what trips the tripwire.",
        False,
    ),
    (
        "a description of what went wrong is not a claim",
        "A finished diff on a branch nobody opened a pull request for is "
        "invisible to the engineer downstream.",
        False,
    ),
    (
        "the corrected sentence stays quiet",
        "Every role opens a pull request for its own work, the researcher and "
        "the designer included.",
        False,
    ),
    (
        "an absent pull request is a state of the world, not an inability",
        "If no pull request exists the designer has nothing waiting on a human.",
        False,
    ),
    (
        "a sweeping claim scoped to a condition is not a capability denial",
        "No role can file an issue without the label.",
        False,
    ),
    (
        "a true claim about a role that holds no tool for it stays quiet",
        "The orchestrator cannot open a pull request for a child's work.",
        False,
    ),
    (
        "a shell is not a wildcard that claims every role can do everything",
        "The engineer cannot file an issue.",
        False,
    ),
    (
        "a restriction on writing files is not a claim about pull requests",
        "The designer cannot write to files under src/, though it may open a "
        "pull request.",
        False,
    ),
]

INSTRUCTION_CASES = [
    (
        "a role told to open one without a tool that can",
        "researcher",
        "Push the document and open a pull request for it.",
        {"Read", "Write"},
        True,
    ),
    (
        "the same instruction with the tool granted",
        "researcher",
        "Push the document and open a pull request for it.",
        {"Read", "mcp__github__create_pull_request"},
        False,
    ),
    (
        "the shell form counts as a tool that can",
        "engineer",
        "Branch, one empty-or-trivial commit, gh pr create --draft, then work.",
        {"Bash"},
        False,
    ),
    (
        "narrating a missing pull request is not an instruction",
        "orchestrator",
        "Say that the branch exists and that nobody opened a pull request for it.",
        {"Read"},
        False,
    ),
]

# Each case: a description, the runtime allowlist a role would hold, the body it
# is given, and whether the runtime check should fire. The allowlists are cut
# down to the entries the case is about - the real ones are read from the
# workflow in the last block below.
RUNTIME_CASES = [
    (
        "the gap that was reachable with the gate green",
        "Push the document and open a pull request for it.",
        {"Bash(gh issue view:*)", "Bash(git push:*)", "Write"},
        True,
    ),
    (
        "the same instruction with the run-time grant present",
        "Push the document and open a pull request for it.",
        {"Bash(gh pr create:*)", "Write"},
        False,
    ),
    (
        "scoped shell entries on both sides still do not grant the thing",
        "Search the web for how this kind of surface is being made now.",
        {"Bash(gh pr create:*)", "Bash(git diff:*)", "WebFetch"},
        True,
    ),
    (
        "a body that asks for none of it stays quiet on any allowlist",
        "Read the issue and its acceptance criteria before anything else.",
        set(),
        False,
    ),
]

failures: list[str] = []


def report(ok: bool, description: str) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {description}")
    if not ok:
        failures.append(description)


def main() -> int:
    # Judged against the grants the repository actually ships, so a case cannot
    # pass against an invented tool list.
    granted = guard.role_tools()

    print("Denial: no file may say a role cannot do what it is granted\n")
    for description, sentence, should_fire in DENIAL_CASES:
        fired = False
        for flat in guard.prose_sentences(sentence):
            if guard.capability_claim_violations(flat, granted):
                fired = True
        report(fired == should_fire, description)

    print("\nInstruction: a role told to do something must hold a tool for it\n")
    for description, _role, body, tools, should_fire in INSTRUCTION_CASES:
        fired = bool(guard.instruction_violations(body, tools))
        report(fired == should_fire, description)

    print("\nRuntime: a role told to do something must be granted it in the run\n")
    for description, body, allowlist, should_fire in RUNTIME_CASES:
        fired = any(
            re.search(capability["instruction"], body, re.I)
            and not allowlist & capability["runtime"]
            for capability in guard.CAPABILITIES
        )
        report(fired == should_fire, description)

    # Pinned against the real workflow, because the parser is the part that can
    # go quiet: a step renamed or reshaped would leave every case above passing
    # against nothing. These are grants the workflow argues for at length, so a
    # change to one is a change somebody meant to make.
    print("\nThe allowlist as agent-run.yml actually builds it\n")
    guard.errors.clear()
    runtime = guard.runtime_allowlist()
    report(not guard.errors, "the role allowlist parses")
    for error in guard.errors:
        print(f"       {error}")
    report(sorted(runtime) == sorted(guard.ROLES), "every role has a branch")
    report(
        "Bash(gh pr create:*)" in runtime.get("designer", set()),
        "the designer can open its own pull request in a run",
    )
    report(
        "Bash(gh pr create:*)" not in runtime.get("orchestrator", set()),
        "the orchestrator still cannot, which is the arrangement on purpose",
    )
    report(
        guard.RUNTIME_SCRIPTS_GRANT in runtime.get("engineer", set())
        and guard.RUNTIME_SCRIPTS_GRANT in runtime.get("designer", set()),
        "both roles told to run ./scripts/ entry points are granted them",
    )

    print("\nThe repository itself\n")
    guard.errors.clear()
    guard.check_capability_claims()
    guard.check_roles_can_do_what_they_are_told()
    guard.check_roles_can_run_what_they_are_told()
    guard.check_named_project_commands()
    report(not guard.errors, "no capability claim drifts from frontmatter or the allowlist")
    for error in guard.errors:
        print(f"       {error}")

    # The exemption earns its keep only if it stays narrow.
    report(
        guard.CLAIM_FIXTURES == {
            "scripts/validate_plugin.py",
            "scripts/test_capability_claims.py",
        },
        "only the two fixture files are exempt from the scan",
    )

    if failures:
        print(f"\ncapability: {len(failures)} case(s) failed")
        return 1
    total = len(DENIAL_CASES) + len(INSTRUCTION_CASES) + len(RUNTIME_CASES) + 7
    print(f"\ncapability: {total} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
