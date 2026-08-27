#!/usr/bin/env python3
"""Run the release workflow's resolve step against real git repositories.

The step decides which commit a major tag lands on, and every project resolves
that tag on its next run. A bug here is not a failed job; it is a silent change
to what every project executes. So it gets executed against real history rather
than read.

The step's `run:` block is pulled straight out of the workflow, so these cases
cannot drift away from what actually ships. Only the `${{ }}` expressions are
substituted, since those are the runner's job.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"

DEFAULT_BRANCH = "main"


def resolve_script() -> str:
    data = yaml.safe_load(WORKFLOW.read_text())
    for step in data["jobs"]["release"]["steps"]:
        if step.get("id") == "target":
            return step["run"]
    raise SystemExit("release.yml has no step with id 'target'")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def build_repo(repo: Path) -> dict[str, str]:
    """Three commits on the default branch, one on a branch that never merged."""
    git(repo, "init", "--quiet", "--initial-branch", DEFAULT_BRANCH)
    git(repo, "config", "user.email", "guard@example.invalid")
    git(repo, "config", "user.name", "guard")

    shas = {}
    for name in ("first", "second", "third"):
        (repo / "file").write_text(name)
        git(repo, "add", "file")
        git(repo, "commit", "--quiet", "-m", name)
        shas[name] = git(repo, "rev-parse", "HEAD")

    git(repo, "checkout", "--quiet", "-b", "unmerged")
    (repo / "file").write_text("unmerged")
    git(repo, "add", "file")
    git(repo, "commit", "--quiet", "-m", "unmerged")
    shas["unmerged"] = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "--quiet", DEFAULT_BRANCH)

    return shas


def run_case(script: str, repo: Path, tag: str, commit: str) -> tuple[int, dict[str, str]]:
    with tempfile.NamedTemporaryFile("w+", delete=False) as handle:
        output = Path(handle.name)
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=repo,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(repo),
            "TAG": tag,
            "COMMIT": commit,
            "DEFAULT_BRANCH": DEFAULT_BRANCH,
            "GITHUB_OUTPUT": str(output),
        },
    )
    outputs = {}
    for line in output.read_text().splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            outputs[key] = value
    output.unlink()
    return result.returncode, outputs


def main() -> int:
    script = resolve_script()
    failures = 0

    def case(name, tag, commit, tagged, expected_code, expected_target=None, expected_moved=None):
        nonlocal failures
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            shas = build_repo(repo)
            if tagged:
                git(repo, "tag", "v1", shas[tagged])
            target = shas.get(commit, commit)
            code, outputs = run_case(script, repo, tag, target if commit else "")

            problems = []
            if code != expected_code:
                problems.append(f"exit {code}, expected {expected_code}")
            if expected_target is not None and outputs.get("target") != shas[expected_target]:
                got = outputs.get("target", "")
                problems.append(f"target {got[:7] or 'unset'}, expected {expected_target}")
            if expected_moved is not None and outputs.get("moved") != expected_moved:
                problems.append(f"moved {outputs.get('moved')}, expected {expected_moved}")

            if problems:
                failures += 1
                print(f"  FAIL {name}")
                for problem in problems:
                    print(f"       {problem}")
            else:
                print(f"  ok   {name}")

    # The ordinary run: the tag is behind, and it goes to the tip.
    case("an empty commit input means the tip of the default branch",
         "v1", "", tagged="first", expected_code=0, expected_target="third", expected_moved="true")

    # A tag that never existed is created rather than refused. Cutting v2 is
    # the same operation as moving v1.
    case("a tag that does not exist yet is a move like any other",
         "v2", "", tagged=None, expected_code=0, expected_target="third", expected_moved="true")

    # Nothing to do, and it has to say so rather than push an identical ref.
    case("a tag already at the target does not move",
         "v1", "", tagged="third", expected_code=0, expected_target="third", expected_moved="false")

    # Rolling back is the same operation with an older commit.
    case("an older merged commit is allowed, which is how a rollback works",
         "v1", "second", tagged="third", expected_code=0, expected_target="second", expected_moved="true")

    # The one that matters. An unmerged commit has not been through the gate,
    # and tagging it puts it in every project.
    case("a commit that is not on the default branch is refused",
         "v1", "unmerged", tagged="first", expected_code=1)

    case("a commit that does not exist is refused",
         "v1", "0000000000000000000000000000000000000000", tagged="first", expected_code=1)

    # Not a general ref writer.
    for name in ("main", "v1.2", "latest", "v", "release/v1", "v1; rm -rf /"):
        case(f"tag name {name!r} is refused",
             name, "", tagged="first", expected_code=1)

    print()
    if failures:
        print(f"release: {failures} failing case(s)")
        return 1
    print("release: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
