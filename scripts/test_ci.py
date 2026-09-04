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


TEMPLATE = ROOT / "plugins" / "agent-factory" / "templates" / "project" / ".github" / "workflows" / "ci.yml"

# What provisioning puts in a repository, and nothing else. The placeholder
# gate's tripwire treats anything outside this as product code arriving.
SCAFFOLDING = [
    "README.md",
    "CLAUDE.md",
    ".claude/agent-factory.json",
    ".claude/agents/engineer.md",
    ".claude/skills/house-rules/SKILL.md",
    ".claude/commands/retro.md",
    ".claude/memory/engineer.md",
    ".github/CODEOWNERS",
    ".github/workflows/ci.yml",
    "docs/research/.gitkeep",
    "docs/design/.gitkeep",
    "docs/decisions/.gitkeep",
]


def template_commands() -> str:
    """The placeholder gate exactly as it ships, so this cannot drift from it."""
    data = yaml.safe_load(TEMPLATE.read_text())
    commands = data["jobs"]["ci"]["with"].get("commands")
    if not commands:
        raise SystemExit(
            "the project ci.yml template has no 'commands' - it is on the Node "
            "path, and the placeholder gate's tripwire is no longer shipping"
        )
    return commands


def build_repo(cwd: Path, extra: list[str]) -> None:
    for name in SCAFFOLDING + extra:
        path = cwd / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n")
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.run(["git", "init", "-q"], cwd=cwd, check=True, **quiet)
    subprocess.run(["git", "add", "-A"], cwd=cwd, check=True, **quiet)


# name, files added on top of the scaffolding, expected exit, text wanted in output
TRIPWIRE_CASES: list[tuple[str, list[str], int, str]] = [
    ("a freshly provisioned repository passes", [], 0, ""),
    ("research writing an ADR does not trip it", ["docs/decisions/0001-a-choice.md"], 0, ""),
    ("design writing a document does not trip it", ["docs/design/navigation.md"], 0, ""),
    ("product code at the root trips it", ["index.html"], 1, "index.html"),
    ("product code in a subdirectory trips it", ["src/main.py"], 1, "src/main.py"),
    ("a manifest the gate would need trips it", ["package.json"], 1, "package.json"),
]


def check_tripwire(script: str) -> int:
    """The placeholder gate must fail the moment it stops being adequate.

    A placeholder nobody replaced is the failure this exists to stop: every
    check green, and none of them testing the product.
    """
    failures = 0
    commands = template_commands()

    for name, extra, want_code, want_text in TRIPWIRE_CASES:
        with tempfile.TemporaryDirectory() as workdir:
            cwd = Path(workdir)
            build_repo(cwd, extra)
            code, output = run_case(script, commands, cwd)

        problems = []
        if code != want_code:
            problems.append(f"exit {code}, wanted {want_code}")
        if want_text and want_text not in output:
            problems.append(f"output never names {want_text!r}, so nobody knows what tripped it")

        if problems:
            failures += 1
            print(f"  FAIL  {name}")
            for problem in problems:
                print(f"          {problem}")
            for line in output.strip().splitlines():
                print(f"        | {line}")
        else:
            print(f"  ok    {name}")

    return failures


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

    print()
    failures += check_tripwire(script)

    total = len(CASES) + len(TRIPWIRE_CASES)
    if failures:
        print(f"\nguard: {failures} of {total} case(s) failed")
        return 1
    print(f"\nguard: {total} case(s) pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
