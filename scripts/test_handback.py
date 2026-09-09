#!/usr/bin/env python3
"""Run the agent-run hand-back shell against a fake `gh` and check who it wakes.

The hand-back step is where an objective either keeps moving or quietly stops.
It decides, from a child that has just finished, whether there is a parent
orchestrator to wake - and every failure in it is silent by design, because a
wake that cannot happen must not fail the run that earned it. Silent and
untested is the combination that produced the bug this file exists to keep
fixed: children created in a run carry no native sub-issue link, both parent
lookups answered null, and the cascade stopped at the first child with nothing
in any log to say so.

The step's `run:` block is pulled straight out of the workflow, so these tests
cannot drift away from what actually ships.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "agent-run.yml"
HANDBACK_STEP = "Hand back to a human"

# Answers `gh` calls from a JSON state file and logs every call made.
FAKE_GH = """#!/usr/bin/env python3
import json, os, sys

args = sys.argv[1:]
state = json.load(open(os.environ["GH_STATE"]))
with open(os.environ["GH_CALLS"], "a") as log:
    log.write(" ".join(args) + "\\n")

# `gh issue view <n> --json <field>`
if args[:2] == ["issue", "view"]:
    number = args[2]
    issue = state["issues"].get(number)
    if issue is None:
        sys.exit(1)
    if "parent" in args:
        parent = issue.get("parent")
        print(parent if parent is not None else "")
    elif "labels" in args:
        print("\\n".join(issue.get("labels", [])))
    elif "body" in args:
        print(issue.get("body", ""))
    sys.exit(0)

# `gh api repos/<owner>/<repo>/issues/<n> --jq .parent.number`
if args[:1] == ["api"]:
    number = args[1].rsplit("/", 1)[-1]
    issue = state["issues"].get(number, {})
    parent = issue.get("rest_parent")
    print(parent if parent is not None else "")
    sys.exit(0)

sys.exit(0)
"""


def handback_script() -> tuple[str, dict]:
    data = yaml.safe_load(WORKFLOW.read_text())
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if step.get("name") == HANDBACK_STEP:
                return step["run"], step.get("env") or {}
    raise SystemExit(f"no {HANDBACK_STEP!r} step in agent-run.yml")


def run_case(state: dict, role: str = "engineer", kind: str = "issue") -> list[str]:
    script, _ = handback_script()
    # Only wake_parent is under test; the label writes around it need a job
    # status, and `success` is the path a finished child takes.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        gh = tmp / "bin" / "gh"
        gh.parent.mkdir()
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        calls = tmp / "calls"
        calls.touch()
        state_file = tmp / "state.json"
        state_file.write_text(json.dumps(state))

        env = dict(os.environ)
        env["PATH"] = f"{gh.parent}:{env['PATH']}"
        env["GH_STATE"] = str(state_file)
        env["GH_CALLS"] = str(calls)
        env["GH_TOKEN"] = "fake-token"
        env["GH_REPO"] = "owner/repo"
        env["ISSUE"] = "30"
        env["KIND"] = kind
        env["ROLE"] = role
        env["RUN_LABEL"] = "agent:queued"
        env["JOB_STATUS"] = "success"
        env["RUN_URL"] = "https://example.invalid/run"
        env["RUNNER_TEMP"] = str(tmp)

        subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
        return calls.read_text().splitlines()


def woke(calls: list[str], parent: str) -> bool:
    return any(
        line.startswith(f"issue edit {parent}") and "agent:queued" in line
        for line in calls
    )


def objective(labels=None, body="", parent=None, rest_parent=None) -> dict:
    return {
        "labels": labels if labels is not None else ["objective"],
        "body": body,
        "parent": parent,
        "rest_parent": rest_parent,
    }


CASES = []


def case(name):
    def register(fn):
        CASES.append((name, fn))
        return fn
    return register


@case("a body reference wakes the parent when there is no native link")
def _():
    # The case that matters: this is what a run-created child actually looks
    # like. `gh issue create` cannot make a sub-issue, so both lookups answer null
    # and the first line of the body is the only link there is.
    state = {"issues": {
        "30": objective(labels=["role:researcher"], body="Parent: #28\n\nRest of it."),
        "28": objective(labels=["objective"]),
    }}
    return woke(run_case(state), "28")


@case("a native parent link is used when present")
def _():
    state = {"issues": {
        "30": objective(labels=["role:researcher"], body="", parent="28"),
        "28": objective(labels=["objective"]),
    }}
    return woke(run_case(state), "28")


@case("no parent anywhere wakes nothing")
def _():
    state = {"issues": {"30": objective(labels=["role:researcher"], body="No link here.")}}
    return not any("issue edit" in c and "agent:queued" in c for c in run_case(state))


@case("a parent that is not an objective is left alone")
def _():
    state = {"issues": {
        "30": objective(labels=["role:researcher"], body="Parent: #28"),
        "28": objective(labels=["role:engineer"]),
    }}
    return not woke(run_case(state), "28")


@case("a parent stopped for a human is not woken")
def _():
    state = {"issues": {
        "30": objective(labels=["role:researcher"], body="Parent: #28"),
        "28": objective(labels=["objective", "agent:blocked"]),
    }}
    return not woke(run_case(state), "28")


@case("a parent already queued is not queued twice")
def _():
    state = {"issues": {
        "30": objective(labels=["role:researcher"], body="Parent: #28"),
        "28": objective(labels=["objective", "agent:queued"]),
    }}
    return not woke(run_case(state), "28")


@case("an orchestrator run does not wake anything")
def _():
    # An objective has no parent to wake, and waking itself is a loop.
    state = {"issues": {
        "30": objective(labels=["objective"], body="Parent: #28"),
        "28": objective(labels=["objective"]),
    }}
    return not woke(run_case(state, role="orchestrator"), "28")


def main() -> int:
    failures = 0
    for name, fn in CASES:
        try:
            ok = fn()
        except Exception as exc:  # a crash is a failure, not a stack trace
            ok = False
            print(f"       {type(exc).__name__}: {exc}")
        if ok:
            print(f"  ok   {name}")
        else:
            failures += 1
            print(f"  FAIL {name}")

    print()
    if failures:
        print(f"handback: {failures} failing case(s)")
        return 1
    print(f"handback: {len(CASES)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
