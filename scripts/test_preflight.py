#!/usr/bin/env python3
"""Run the agent-run preflight shell against a fake `gh` and check its decisions.

The preflight is the only place in this repo where a bug is expensive: it is
what stops a Pro subscription being spent on a run nobody asked for. So it gets
executed here rather than merely parsed.

The step's `run:` block is pulled straight out of the workflow, so the tests
cannot drift away from what actually ships. Only the `${{ }}` expressions are
substituted, since those are the runner's job.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "agent-run.yml"

FAKE_GH = """#!/usr/bin/env python3
import json, os, sys

state = json.load(open(os.environ["GH_STATE"]))
args = sys.argv[1:]
kind, verb = args[0], args[1]

with open(os.environ["GH_CALLS"], "a") as log:
    log.write(" ".join(args) + "\\n")

if verb == "view":
    if "--json" in args and "labels" in args:
        print("\\n".join(state["labels"]))
    elif "--json" in args and "comments" in args:
        print(state["attempts"])
    sys.exit(0)
if verb == "diff":
    print("\\n".join(state.get("changed", [])))
    sys.exit(0)
sys.exit(0)
"""


def preflight_script() -> str:
    data = yaml.safe_load(WORKFLOW.read_text())
    triggers = data.get("on", data.get(True))
    step = data["jobs"]["preflight"]["steps"][0]
    return step["run"], step["env"], triggers


def resolve(expression: str, event: dict) -> str:
    """Substitute the handful of ${{ }} expressions the preflight env uses."""
    inputs = event["inputs"]
    literals = {
        "github.token": "fake-token",
        "github.repository": "owner/repo",
        "github.event_name": event["event_name"],
        "github.event.action": event.get("action", ""),
        "github.event.comment.body": event.get("comment_body", ""),
        "github.event.label.name": event.get("label", ""),
    }
    body = expression.strip()
    if body.startswith("${{") and body.endswith("}}"):
        body = body[3:-2].strip()
    else:
        return expression

    for key, value in literals.items():
        if body == key:
            return value
    if body.startswith("inputs."):
        return str(inputs[body.split(".", 1)[1]])
    if "github.event.issue.number" in body:
        # Emulate the `a || b || c` fallback chain the runner evaluates.
        return str(event.get("number") or inputs["issue-number"] or "")
    if "pull_request != null" in body:
        return "pr" if event.get("kind") == "pr" else "issue"
    raise AssertionError(f"test harness cannot resolve {expression!r}")


def run_case(name: str, event: dict, state: dict) -> tuple[str, str, int, list[str]]:
    script, env_block, _ = preflight_script()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        gh = tmp / "bin" / "gh"
        gh.parent.mkdir()
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        output = tmp / "output"
        output.touch()
        calls = tmp / "calls"
        calls.touch()
        state_file = tmp / "state.json"
        state_file.write_text(json.dumps(state))

        env = dict(os.environ)
        env["PATH"] = f"{gh.parent}:{env['PATH']}"
        env["GITHUB_OUTPUT"] = str(output)
        env["GH_STATE"] = str(state_file)
        env["GH_CALLS"] = str(calls)
        for key, value in env_block.items():
            env[key] = resolve(str(value), event)

        result = subprocess.run(
            ["bash", "-c", script], env=env, capture_output=True, text=True
        )
        outputs = dict(
            line.split("=", 1)
            for line in output.read_text().splitlines()
            if "=" in line
        )
        return (
            outputs.get("should-run", "<unset>"),
            outputs.get("role", ""),
            result.returncode,
            calls.read_text().splitlines(),
        ), result


DEFAULT_INPUTS = {
    "issue-number": "",
    "run-label": "agent:queued",
    "trigger-phrase": "@claude",
    "max-attempts": 3,
    "skip-path-patterns": "docs/**\n*.md\n**/*.md\npackage-lock.json\n**/package-lock.json\npnpm-lock.yaml\n**/pnpm-lock.yaml\nyarn.lock\n**/yarn.lock\nLICENSE\n",
}


def event(**overrides) -> dict:
    base = {
        "event_name": "issues",
        "action": "labeled",
        "label": "agent:queued",
        "number": 7,
        "kind": "issue",
        "comment_body": "",
        "inputs": dict(DEFAULT_INPUTS),
    }
    base.update(overrides)
    return base


def state(labels, attempts=0, changed=None) -> dict:
    return {"labels": labels, "attempts": attempts, "changed": changed or []}


CASES = [
    (
        "objective issue queued runs the orchestrator",
        event(),
        state(["objective", "agent:queued"]),
        ("true", "orchestrator", 0),
    ),
    (
        "engineer role label runs the engineer",
        event(),
        state(["role:engineer", "agent:queued"]),
        ("true", "engineer", 0),
    ),
    (
        "no role label does not run",
        event(),
        state(["agent:queued"]),
        ("false", "", 0),
    ),
    (
        "two role labels refuse rather than guess",
        event(),
        state(["role:engineer", "role:designer"]),
        ("false", "", 0),
    ),
    (
        "needs-decomposition is a human's call",
        event(),
        state(["role:engineer", "needs-decomposition"]),
        ("false", "", 0),
    ),
    (
        "agent:blocked refuses",
        event(),
        state(["role:engineer", "agent:blocked"]),
        ("false", "", 0),
    ),
    (
        "a label that is not the run label does not run",
        event(label="documentation"),
        state(["role:engineer"]),
        ("false", "", 0),
    ),
    (
        "a comment without the trigger phrase does not run",
        event(event_name="issue_comment", comment_body="looks good to me"),
        state(["role:engineer"]),
        ("false", "", 0),
    ),
    (
        "a comment with the trigger phrase runs",
        event(event_name="issue_comment", comment_body="@claude please fix the empty state"),
        state(["role:engineer"]),
        ("true", "engineer", 0),
    ),
    (
        "the third attempt still runs",
        event(),
        state(["role:engineer"], attempts=2),
        ("true", "engineer", 0),
    ),
    (
        "the fourth attempt fails the job",
        event(),
        state(["role:engineer"], attempts=3),
        ("false", "", 1),
    ),
    (
        "a docs-only pull request is not worth a run",
        event(event_name="issue_comment", kind="pr", comment_body="@claude take a look"),
        state(["role:engineer"], changed=["README.md", "docs/design/1-flow.md", "package-lock.json"]),
        ("false", "", 0),
    ),
    (
        "a pull request touching source does run",
        event(event_name="issue_comment", kind="pr", comment_body="@claude take a look"),
        state(["role:engineer"], changed=["README.md", "src/app.ts"]),
        ("true", "engineer", 0),
    ),
    (
        "workflow_dispatch takes the issue number from the input",
        event(event_name="workflow_dispatch", action="", label="", number="",
              inputs=dict(DEFAULT_INPUTS, **{"issue-number": "42"})),
        state(["role:researcher"]),
        ("true", "researcher", 0),
    ),
]


def main() -> int:
    failures = 0
    for name, evt, st, expected in CASES:
        (should_run, role, code, calls), result = run_case(name, evt, st)
        actual = (should_run, role, code)
        if actual == expected:
            print(f"  ok   {name}")
        else:
            failures += 1
            print(f"  FAIL {name}")
            print(f"       expected (should-run, role, exit) {expected}, got {actual}")
            print(f"       stdout: {result.stdout.strip()}")
            print(f"       stderr: {result.stderr.strip()}")

    # The refusal has to leave a trace, or a fourth attempt looks like a flake.
    (_, _, _, calls), _ = run_case("cap", event(), state(["role:engineer"], attempts=3))
    joined = " ".join(calls)
    if "agent:blocked" not in joined or "comment" not in joined:
        failures += 1
        print("  FAIL refusing a fourth attempt must label agent:blocked and say why")
    else:
        print("  ok   refusing a fourth attempt labels agent:blocked and says why")

    print()
    if failures:
        print(f"preflight: {failures} failing case(s)")
        return 1
    print(f"preflight: {len(CASES) + 1} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
