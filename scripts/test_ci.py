#!/usr/bin/env python3
"""Run the gate's commands step against real shells.

`ci.yml` decides whether a pull request can merge in every project, and the
commands path is hand-written shell rather than a package manager doing the
deciding. A bug here does not fail loudly; it passes a run that should have
failed, which is the one failure mode a gate cannot have.

The step's `run:` block is pulled straight out of the workflow, so these cases
cannot drift away from what actually ships. It is executed under the same shell
GitHub uses for a `run:` block - `bash -e -o pipefail` - since the step is
written expecting exactly that.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

STEP_NAME = "Run the caller's commands"


def commands_script() -> str:
    data = yaml.safe_load(WORKFLOW.read_text())
    for step in data["jobs"]["check"]["steps"]:
        if step.get("name") == STEP_NAME:
            return step["run"]
    raise SystemExit(f"ci.yml has no step named {STEP_NAME!r}")


def run_case(script: str, commands: str, cwd: Path) -> tuple[int, str]:
    with tempfile.NamedTemporaryFile("w+", suffix=".sh", delete=False) as handle:
        handle.write(script)
        path = Path(handle.name)
    try:
        # The shell GitHub gives a `run:` block, flags included.
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", str(path)],
            cwd=cwd,
            env={"COMMANDS": commands, "PATH": "/usr/bin:/bin:/usr/local/bin"},
            capture_output=True,
            text=True,
        )
    finally:
        path.unlink(missing_ok=True)
    return result.returncode, result.stdout + result.stderr


CASES: list[tuple[str, str, int, list[str], list[str]]] = [
    # name, commands, expected exit, files that must exist, files that must not
    (
        "every command runs, in order",
        "touch one\ntouch two\ntouch three",
        0,
        ["one", "two", "three"],
        [],
    ),
    (
        "a failing command stops the run there",
        "touch one\nexit 3\ntouch three",
        3,
        ["one"],
        ["three"],
    ),
    (
        "a missing binary fails rather than being skipped",
        "definitely-not-a-real-binary\ntouch after",
        127,
        [],
        ["after"],
    ),
    (
        "blank lines and comments are not commands",
        "touch one\n\n   \n# touch commented\n\ntouch two",
        0,
        ["one", "two"],
        ["commented"],
    ),
    (
        "leading and trailing whitespace is trimmed",
        "   touch spaced   ",
        0,
        ["spaced"],
        [],
    ),
    (
        "nothing runnable is a failure, not a pass",
        "\n   \n# only a comment\n",
        1,
        [],
        [],
    ),
    (
        "an empty-ish value cannot pass the gate by accident",
        "   ",
        1,
        [],
        [],
    ),
    (
        "the first half of a chained line still fails the line",
        "false && touch chained\ntouch after",
        1,
        [],
        ["chained", "after"],
    ),
    (
        "a failure mid-pipeline is not hidden by the last command",
        "definitely-not-a-real-binary | cat\ntouch after",
        127,
        [],
        ["after"],
    ),
    (
        "an unset variable inside a command is an error, not an empty string",
        "touch \"${NOT_SET_ANYWHERE}\"\ntouch after",
        1,
        [],
        ["after"],
    ),
]


def main() -> int:
    script = commands_script()
    failures = 0

    for name, commands, want_code, must_exist, must_not_exist in CASES:
        with tempfile.TemporaryDirectory() as workdir:
            cwd = Path(workdir)
            code, output = run_case(script, commands, cwd)

            problems = []
            if code != want_code:
                problems.append(f"exit {code}, wanted {want_code}")
            for filename in must_exist:
                if not (cwd / filename).exists():
                    problems.append(f"{filename} was not created")
            for filename in must_not_exist:
                if (cwd / filename).exists():
                    problems.append(f"{filename} was created and should not have been")

        if problems:
            failures += 1
            print(f"  FAIL  {name}")
            for problem in problems:
                print(f"          {problem}")
            for line in output.strip().splitlines():
                print(f"        | {line}")
        else:
            print(f"  ok    {name}")

    if failures:
        print(f"\nguard: {failures} of {len(CASES)} case(s) failed")
        return 1
    print(f"\nguard: {len(CASES)} case(s) pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
