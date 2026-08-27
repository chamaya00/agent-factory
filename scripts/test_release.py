#!/usr/bin/env python3
"""Run the release workflow's resolve step against real git repositories.

The step decides whether a release tag gets cut and what it is called. A bug
here is either a tag that disagrees with the plugin manifest, which installs as
the version already cached and updates nothing, or a release tag that moves,
which silently changes what a project resolves after its author reviewed and
pinned it. So it gets executed against real history rather than read.

The step's `run:` block is pulled straight out of the workflow, so these cases
cannot drift away from what actually ships. Only the `${{ }}` expressions are
substituted, since those are the runner's job.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"

DEFAULT_BRANCH = "main"
MANIFEST = "plugins/agent-factory/.claude-plugin/plugin.json"


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


def build_repo(repo: Path, manifest: dict | None) -> dict[str, str]:
    """Three commits on the default branch, carrying a plugin manifest."""
    git(repo, "init", "--quiet", "--initial-branch", DEFAULT_BRANCH)
    git(repo, "config", "user.email", "guard@example.invalid")
    git(repo, "config", "user.name", "guard")

    if manifest is not None:
        path = repo / MANIFEST
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest))

    shas = {}
    for name in ("first", "second", "third"):
        (repo / "file").write_text(name)
        git(repo, "add", "-A")
        git(repo, "commit", "--quiet", "-m", name)
        shas[name] = git(repo, "rev-parse", "HEAD")

    return shas


def run_case(script: str, repo: Path, version: str) -> tuple[int, dict[str, str]]:
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
            "VERSION": version,
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

    def case(name, version="", manifest=None, existing_tag=None,
             expected_code=0, expected_tag=None, expected_target=None):
        nonlocal failures
        if manifest is None:
            manifest = {"name": "agent-factory", "version": "1.2.0"}
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            shas = build_repo(repo, None if manifest is False else manifest)
            if existing_tag:
                git(repo, "tag", existing_tag, shas["first"])

            code, outputs = run_case(script, repo, version)

            problems = []
            if code != expected_code:
                problems.append(f"exit {code}, expected {expected_code}")
            if expected_tag is not None and outputs.get("tag") != expected_tag:
                problems.append(f"tag {outputs.get('tag') or 'unset'}, expected {expected_tag}")
            if expected_target is not None and outputs.get("target") != shas[expected_target]:
                got = outputs.get("target", "")
                problems.append(f"target {got[:7] or 'unset'}, expected {expected_target}")

            if problems:
                failures += 1
                print(f"  FAIL {name}")
                for problem in problems:
                    print(f"       {problem}")
            else:
                print(f"  ok   {name}")

    # The ordinary run: the manifest names the tag and it lands on the tip.
    case("an empty version takes the tag from the plugin manifest",
         expected_tag="v1.2.0", expected_target="third")

    # Typing it confirms the manifest rather than overriding it.
    case("a version matching the manifest is accepted",
         version="v1.2.0", expected_tag="v1.2.0", expected_target="third")

    # The one that stops a release from silently updating nothing: an installed
    # plugin compares versions, so a tag ahead of the manifest is a no-op.
    case("a version disagreeing with the manifest is refused",
         version="v1.3.0", expected_code=1)

    # The whole difference between a release tag and a pointer.
    case("a tag that already exists is refused rather than moved",
         existing_tag="v1.2.0", expected_code=1)

    case("an unrelated existing tag does not block the release",
         existing_tag="v1.1.0", expected_tag="v1.2.0", expected_target="third")

    # A manifest is required, and so is a version in it.
    case("a missing plugin manifest is refused", manifest=False, expected_code=1)
    case("a manifest with no version is refused",
         manifest={"name": "agent-factory"}, expected_code=1)

    # Not a general ref writer, and not a moving major tag either.
    for bad in ("main", "v1", "v1.2", "latest", "v", "release/v1",
                "v1.2.0-rc1", "v1.2.0; rm -rf /"):
        case(f"version {bad!r} is refused", version=bad,
             manifest={"name": "agent-factory", "version": bad.lstrip("v")},
             expected_code=1)

    print()
    if failures:
        print(f"release: {failures} failing case(s)")
        return 1
    print("release: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
