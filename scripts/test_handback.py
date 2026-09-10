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
    elif "comments" in args:
        print(issue.get("last_marker", ""))
    elif "body" in args:
        print(issue.get("body", ""))
    sys.exit(0)

# `gh issue list --label <l> --json number`
if args[:2] == ["issue", "list"]:
    print("\\n".join(str(n) for n in state.get("queued", [])))
    sys.exit(0)

# `gh pr view <n> --json closingIssuesReferences`
if args[:2] == ["pr", "view"]:
    number = args[2]
    print("\\n".join(str(n) for n in state.get("closes", {}).get(number, [])))
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

        subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True, text=True)
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


def run_diagnosis(subtype: str, turns: int, cap: str = "40") -> str:
    """Run the hand-back over a synthetic action result and return its comment."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        gh = tmp / "bin" / "gh"
        gh.parent.mkdir()
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        calls = tmp / "calls"
        calls.touch()
        state_file = tmp / "state.json"
        state_file.write_text(json.dumps({"issues": {}}))
        (tmp / "claude-execution-output.json").write_text(
            json.dumps({"type": "result", "subtype": subtype, "num_turns": turns})
        )
        env = dict(os.environ)
        env.update({
            "PATH": f"{gh.parent}:{env['PATH']}",
            "GH_STATE": str(state_file), "GH_CALLS": str(calls),
            "GH_TOKEN": "fake-token", "GH_REPO": "owner/repo",
            "ISSUE": "46", "KIND": "issue", "ROLE": "engineer",
            "RUN_LABEL": "agent:queued", "JOB_STATUS": "failure",
            "RUN_URL": "https://example.invalid/run",
            "RUNNER_TEMP": str(tmp), "MAX_TURNS": cap,
        })
        script, _ = handback_script()
        subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True, text=True)
        return calls.read_text()


@case("a run over the cap is named as such even when it reports success")
def _():
    # The exact shape seen on new-project-agents-v3#46: `success`, 48 turns,
    # cap 40. The old branch keyed on the subtype and said nothing about it.
    said = run_diagnosis("success", 48)
    return "cap" in said and "48" in said


@case("a run inside the cap is not accused of hitting it")
def _():
    said = run_diagnosis("error_during_execution", 12)
    return "is the cap" not in said


@case("the diagnosis says pushed work survives its run")
def _():
    said = run_diagnosis("success", 48)
    return "committed and pushed survives" in said


MERGE_STEP = "Queue the parent objective"


def merge_script() -> str:
    data = yaml.safe_load(WORKFLOW.read_text())
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if step.get("name") == MERGE_STEP:
                return step["run"]
    raise SystemExit(f"no {MERGE_STEP!r} step in agent-run.yml")


def run_merge(state: dict, pr: str = "43") -> list[str]:
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
        env["PR"] = pr
        env["RUN_LABEL"] = "agent:queued"
        subprocess.run(["bash", "-e", "-c", merge_script()], env=env,
                       capture_output=True, text=True)
        return calls.read_text().splitlines()


@case("a merged pull request wakes the objective its child belongs to")
def _():
    state = {
        "closes": {"43": [40]},
        "issues": {
            "40": objective(labels=["role:researcher"], body="Parent: #39"),
            "39": objective(labels=["objective"]),
        },
    }
    return woke(run_merge(state), "39")


@case("a merged pull request closing nothing wakes nothing")
def _():
    state = {"closes": {"43": []}, "issues": {}}
    return not any("issue edit" in c for c in run_merge(state))


@case("a merge does not re-queue an objective already running")
def _():
    state = {
        "closes": {"43": [40]},
        "issues": {
            "40": objective(labels=["role:researcher"], body="Parent: #39"),
            "39": objective(labels=["objective", "agent:running"]),
        },
    }
    return not woke(run_merge(state), "39")


@case("a merge does not wake an objective stopped for a human")
def _():
    state = {
        "closes": {"43": [40]},
        "issues": {
            "40": objective(labels=["role:researcher"], body="Parent: #39"),
            "39": objective(labels=["objective", "agent:blocked"]),
        },
    }
    return not woke(run_merge(state), "39")


STALE_STEP = "Name the issues that are queued and idle"


def stale_script() -> tuple[str, dict]:
    """The step's script and its literal env.

    The env matters: the marker this step writes is defined there, not in the
    script, so a harness that supplies its own would be testing a value the
    workflow does not use. Only literal values are taken - anything with a
    ${{ }} expression in it is the runner's job and is set by the caller.
    """
    data = yaml.safe_load(WORKFLOW.read_text())
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if step.get("name") == STALE_STEP:
                env = {
                    k: str(v)
                    for k, v in (step.get("env") or {}).items()
                    if "${{" not in str(v)
                }
                return step["run"], env
    raise SystemExit(f"no {STALE_STEP!r} step in agent-run.yml")


def run_stale(state: dict) -> list[str]:
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
        env.update({
            "PATH": f"{gh.parent}:{env['PATH']}",
            "GH_STATE": str(state_file), "GH_CALLS": str(calls),
            "GH_TOKEN": "fake-token", "GH_REPO": "owner/repo",
            "RUN_LABEL": "agent:queued",
        })
        script, step_env = stale_script()
        env.update(step_env)
        subprocess.run(["bash", "-e", "-c", script], env=env,
                       capture_output=True, text=True)
        return calls.read_text().splitlines()


def reported(calls: list[str], n: str) -> bool:
    return any(c.startswith(f"issue comment {n}") and "stalled" in c for c in calls)


@case("a queued issue with nothing running it is reported")
def _():
    state = {"queued": [46], "issues": {
        "46": objective(labels=["agent:queued", "role:engineer"]),
    }}
    return reported(run_stale(state), "46")


@case("a queued issue that is running is left alone")
def _():
    state = {"queued": [46], "issues": {
        "46": objective(labels=["agent:queued", "agent:running"]),
    }}
    return not reported(run_stale(state), "46")


@case("an issue already stopped for a human is not reported")
def _():
    state = {"queued": [46], "issues": {
        "46": objective(labels=["agent:queued", "agent:blocked"]),
    }}
    return not reported(run_stale(state), "46")


@case("the report is not repeated on the next tick")
def _():
    state = {"queued": [46], "issues": {
        "46": dict(objective(labels=["agent:queued"]),
                   last_marker="<!-- agent-factory:stalled --> already said"),
    }}
    return not reported(run_stale(state), "46")


@case("a run starting since the last report re-arms it")
def _():
    state = {"queued": [46], "issues": {
        "46": dict(objective(labels=["agent:queued"]),
                   last_marker="<!-- agent-factory:attempt --> Starting engineer"),
    }}
    return reported(run_stale(state), "46")


@case("the detector never writes a label")
def _():
    state = {"queued": [46], "issues": {"46": objective(labels=["agent:queued"])}}
    return not any("--add-label" in c or "--remove-label" in c
                   for c in run_stale(state))


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
