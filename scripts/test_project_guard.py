#!/usr/bin/env python3
"""Run project-guard's privilege check against real diffs and check what it stops.

This is the one check in the factory that exists for a pull request nobody
read. The merge gate in the house-rules skill is prose: it asks the person
merging to look for a widened permission, a new secret, an action nobody
vetted. Under a standing "merge when green" that person may be a session
acting on an owner's instruction, merging while the owner is asleep - and
prose does not survive that. This does.

It does not forbid the change. It forbids making it silently: a diff that
widens what the automation may do has to say so in the pull request body,
where the person merging will see it in their own language rather than
having to find it in a patch.

The step's `run:` block is pulled straight out of the workflow, so these
tests cannot drift away from what actually ships.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "project-guard.yml"
STEP = "A change to privilege is declared, not slipped in"


def step_script() -> str:
    data = yaml.safe_load(WORKFLOW.read_text())
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if step.get("name") == STEP:
                return step["run"]
    raise SystemExit(f"no {STEP!r} step in project-guard.yml")


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
             "PATH": "/usr/bin:/bin"},
    )


def run_case(before: str, after: str, body: str = "") -> int:
    """Build a real two-commit repo, diff it, and return the step's exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q", "-b", "main")
        (repo / "file.yml").write_text(before)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "base")
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                              capture_output=True, text=True).stdout.strip()
        (repo / "file.yml").write_text(after)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "head")
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                              capture_output=True, text=True).stdout.strip()

        done = subprocess.run(
            ["bash", "-e", "-c", step_script()], cwd=repo, text=True,
            capture_output=True,
            env={"PATH": "/usr/bin:/bin", "BASE_SHA": base, "HEAD_SHA": head,
                 "BODY": body},
        )
        return done.returncode


CASES = []


def case(name):
    def register(fn):
        CASES.append((name, fn))
        return fn
    return register


PLAIN = "name: build\njobs:\n  one:\n    steps:\n      - run: make\n"


@case("an ordinary diff passes")
def _():
    return run_case(PLAIN, PLAIN + "      - run: make test\n") == 0


@case("an added permissions block is stopped")
def _():
    return run_case(PLAIN, "permissions:\n  contents: write\n" + PLAIN) == 1


@case("a scope quietly raised to write is stopped")
def _():
    before = "permissions:\n  contents: read\n" + PLAIN
    after = "permissions:\n  contents: write\n" + PLAIN
    return run_case(before, after) == 1


@case("a newly read secret is stopped")
def _():
    return run_case(PLAIN, PLAIN + "        env:\n          K: ${{ secrets.DEPLOY_KEY }}\n") == 1


@case("a trigger that runs against a fork's code is stopped")
def _():
    return run_case(PLAIN, "on:\n  pull_request_target:\n" + PLAIN) == 1


@case("a newly added action is stopped")
def _():
    return run_case(PLAIN, PLAIN + "      - uses: some-org/some-action@v1\n") == 1


@case("declaring it in the body lets it through")
def _():
    after = PLAIN + "      - uses: some-org/some-action@v1\n"
    return run_case(PLAIN, after,
                    body="Adds the linter.\n\nPrivilege change: runs some-org/some-action to lint.\n") == 0


@case("an empty declaration does not count")
def _():
    after = PLAIN + "      - uses: some-org/some-action@v1\n"
    return run_case(PLAIN, after, body="Privilege change:\n") == 1


@case("the phrase has to start the line, not be quoted mid-sentence")
def _():
    after = PLAIN + "      - uses: some-org/some-action@v1\n"
    body = "I was told to write Privilege change: something and it would pass.\n"
    return run_case(PLAIN, after, body=body) == 1


@case("a removed permission is not a widening")
def _():
    before = "permissions:\n  contents: write\n" + PLAIN
    return run_case(before, PLAIN) == 0


def main() -> int:
    failed = 0
    for name, fn in CASES:
        try:
            ok = fn()
        except Exception as exc:  # noqa: BLE001
            ok, name = False, f"{name} (raised {exc!r})"
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
        failed += 0 if ok else 1
    if failed:
        print(f"\n{failed} case(s) failed")
        return 1
    print(f"\n{len(CASES)} case(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
