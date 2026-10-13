#!/usr/bin/env python3
"""Run setup-project.sh against a fake `gh` and check what --verify reports.

`--verify` makes one promise that matters more than anything it prints: it
writes nothing. It is the mode a person runs against a repository they set up
by hand, to have the settings proved rather than trusted, and a verify that
quietly flipped a setting would prove whatever it had just written. So every
case here fails on any `gh` call that is not a read, and the allowlist of reads
is closed - a new subcommand counts as a write until it is added here on
purpose.

The second promise is the reason the mode exists: "not set" and "cannot read"
are different answers. A login without administration gets a 403 for the
Actions permission and for branch protection, and reporting that as "off"
would send a person to change a setting that may well be right.

The script under test is the real one, copied into a temporary root so the
output file it appends to lands there and not in this checkout. The fake `gh`
answers from canned API responses and applies `--jq` with the real `jq`, as
`gh` applies its own built-in one, so an expression the script gets wrong
fails here the way it would against GitHub.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "setup-project.sh"
TEMPLATE_MANIFEST = ROOT / "plugins" / "agent-factory" / "templates" / "project" / ".claude" / "agent-factory.json"

REPO = "owner/proj"
LABELS = json.loads(TEMPLATE_MANIFEST.read_text())["labels"]
CHECKS = ["ci / checks", "guard / memory cap and protected paths"]
ALL_SECRETS = ["CLAUDE_CODE_OAUTH_TOKEN", "AGENT_APP_ID", "AGENT_APP_PRIVATE_KEY"]
PROBLEM_TAGS = ("NOT SET", "WRONG", "CANNOT READ")

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, subprocess, sys

state = json.load(open(os.environ["GH_STATE"]))
args = sys.argv[1:]
with open(os.environ["GH_CALLS"], "a") as log:
    log.write(json.dumps(args) + "\n")

VALUED = {"-X", "--method", "-H", "--header", "--jq", "-q", "-f", "-F",
          "--field", "--raw-field", "--input", "--repo", "-R", "--json"}

def option(*names):
    for name in names:
        if name in args:
            return args[args.index(name) + 1]
    return None

def emit(data):
    jq = option("--jq", "-q")
    if jq is None:
        print(data if isinstance(data, str) else json.dumps(data))
        return 0
    done = subprocess.run(["jq", "-r", jq], input=json.dumps(data), text=True, capture_output=True)
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    return done.returncode

def refuse(status):
    sys.stderr.write(f"gh: HTTP {status}\n")
    sys.exit(1)

if args[:2] == ["secret", "list"]:
    if state["secrets"] is None:
        refuse(403)
    sys.exit(emit([{"name": name} for name in state["secrets"]]))

if args and args[0] == "api":
    method = (option("-X", "--method") or "GET").upper()
    if method != "GET" or any(flag in args for flag in ("-f", "-F", "--field", "--raw-field", "--input")):
        sys.exit(0)
    positional, skip = [], False
    for arg in args[1:]:
        if skip:
            skip = False
        elif arg in VALUED:
            skip = True
        elif not arg.startswith("-"):
            positional.append(arg)
    answer = state["api"].get(positional[0].split("?")[0])
    if answer is None:
        refuse(404)
    if isinstance(answer, dict) and "__status__" in answer:
        refuse(answer["__status__"])
    sys.exit(emit(answer))

sys.exit(0)
'''


def is_read(call: list[str]) -> bool:
    """Closed list. Anything not named here is treated as a write."""
    if call[:2] in (["secret", "list"], ["run", "list"], ["run", "view"]):
        return True
    if call and call[0] == "api":
        method = "GET"
        for flag in ("-X", "--method"):
            if flag in call:
                method = call[call.index(flag) + 1].upper()
        # `gh api` with a field and no method is a POST.
        fields = any(flag in call for flag in ("-f", "-F", "--field", "--raw-field", "--input"))
        return method == "GET" and not fields
    return False


def scenario(
    admin=True,
    private=False,
    perms="write",
    can_approve=True,
    secrets=ALL_SECRETS,
    labels=LABELS,
    manifest_labels=LABELS,
    required=CHECKS,
    reported=CHECKS,
    rulesets=(),
    events=None,
    runs_readable=True,
    visible=True,
) -> dict:
    """The API as a repository in some state answers it.

    `required` is the classic protection rule. `required=None` is no classic
    rule at all, which GitHub answers with a 404, and `required=[]` is a rule
    that exists and requires no checks. `rulesets` is the checks a ruleset
    requires, which any login that can read the repository can read.
    `events` maps a reported name to the event of the run that reported it,
    `push` when not named: bootstrap's run is `workflow_dispatch`, a Pages
    build is `dynamic`, and neither ever runs on a pull request.
    `manifest_labels=None` is a repository with no `.claude/agent-factory.json`.
    `secrets=None` is a login that cannot list them.
    """
    base = f"repos/{REPO}"
    api: dict = {}
    if visible:
        api[base] = {"default_branch": "main", "private": private, "permissions": {"admin": admin}}
    api[f"{base}/labels"] = [{"name": name} for name in labels]
    api[f"{base}/commits/main/check-runs"] = {"check_runs": [{"name": name} for name in reported]}
    api[f"{base}/commits/main"] = {"sha": "0123abc"}
    if runs_readable:
        events = events or {}
        runs = [{"id": index, "event": events.get(name, "push")} for index, name in enumerate(reported, 1)]
        api[f"{base}/actions/runs"] = {"workflow_runs": runs}
        for index, name in enumerate(reported, 1):
            api[f"{base}/actions/runs/{index}/jobs"] = {"jobs": [{"name": name}]}
    api[f"{base}/rules/branches/main"] = (
        [{
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": name} for name in rulesets]},
        }]
        if rulesets
        else []
    )
    if manifest_labels is not None:
        api[f"{base}/contents/.claude/agent-factory.json"] = json.dumps({"labels": manifest_labels})
    if admin:
        api[f"{base}/actions/permissions/workflow"] = {
            "default_workflow_permissions": perms,
            "can_approve_pull_request_reviews": can_approve,
        }
        if required is not None:
            api[f"{base}/branches/main/protection"] = {
                "required_status_checks": {"contexts": list(required)} if required else None
            }
    else:
        api[f"{base}/actions/permissions/workflow"] = {"__status__": 403}
        api[f"{base}/branches/main/protection"] = {"__status__": 404}
    return {"api": api, "secrets": None if secrets is None else list(secrets)}


def run(args: list[str], state: dict) -> tuple[int, str, list[list[str]], str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "scripts").mkdir()
        shutil.copy(SCRIPT, root / "scripts" / "setup-project.sh")
        manifest = root / TEMPLATE_MANIFEST.relative_to(ROOT)
        manifest.parent.mkdir(parents=True)
        shutil.copy(TEMPLATE_MANIFEST, manifest)

        gh = root / "bin" / "gh"
        gh.parent.mkdir()
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        calls = root / "calls"
        calls.touch()
        state_file = root / "state.json"
        state_file.write_text(json.dumps(state))

        env = dict(os.environ)
        env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
        env["PATH"] = f"{gh.parent}:{env['PATH']}"
        env["GH_STATE"] = str(state_file)
        env["GH_CALLS"] = str(calls)

        result = subprocess.run(
            ["bash", str(root / "scripts" / "setup-project.sh"), *args],
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )
        logged = (root / "setup-project-output.txt").read_text() if (root / "setup-project-output.txt").exists() else ""
        made = [json.loads(line) for line in calls.read_text().splitlines()]
        return result.returncode, result.stdout + result.stderr, made, logged


def lines_tagged(output: str, tag: str) -> list[str]:
    return [line for line in output.splitlines() if line.strip().startswith(tag)]


def problems(output: str) -> list[str]:
    return [line for tag in PROBLEM_TAGS for line in lines_tagged(output, tag)]


# Each case: name, args, state, and a predicate over (rc, output, calls) that
# returns an error string or None.
def expect_clean(rc, out, calls):
    if rc != 0:
        return f"exit {rc}, wanted 0"
    if problems(out):
        return f"reported problems on a clean repository: {problems(out)}"
    return None


def expect_problem(tag: str, *needles: str):
    def check(rc, out, calls):
        if rc == 0:
            return "exit 0 with a problem present; the exit status has to carry it"
        hits = [line for line in lines_tagged(out, tag) if all(n in line for n in needles)]
        if not hits:
            return f"no {tag!r} line naming {needles}; got:\n{out}"
        return None
    return check


def expect_refused_before_any_call(*needles: str):
    def check(rc, out, calls):
        if rc == 0:
            return "accepted arguments it should have refused"
        if calls:
            return f"called gh before refusing: {calls}"
        missing = [n for n in needles if n not in out]
        return f"refusal does not say {missing}" if missing else None
    return check


def no_app(rc, out, calls):
    if rc != 0:
        return f"exit {rc}: a repository with no App is a choice, not a failure"
    if not any("agent identity App" in line for line in lines_tagged(out, "optional")):
        return "does not say what having no App costs"
    return expect_clean(rc, out, calls)


def older_release(rc, out, calls):
    # The repository's own manifest predates agent:revise and so does its
    # preflight. Holding it to the factory's current list would report a
    # label its release never matches on.
    if "own .claude/agent-factory.json" not in out:
        return "did not say which label list it checked against"
    return expect_clean(rc, out, calls)


def unprovisioned(rc, out, calls):
    if "not provisioned yet" not in out:
        return "did not say the repository has no manifest of its own"
    return expect_problem("NOT SET", "agent:revise")(rc, out, calls)


def extra_check_is_a_note(rc, out, calls):
    if not any("ci / lint" in line and "not required" in line for line in lines_tagged(out, "note")):
        return "a reported check nobody requires should be named as a note"
    return expect_clean(rc, out, calls)


def pages_not_offered(rc, out, calls):
    named = [line for line in lines_tagged(out, "note") if "'build'" in line or "'deploy'" in line]
    if named:
        return f"offered a check no pull request runs as one to require: {named}"
    return expect_clean(rc, out, calls)


def runs_unread(rc, out, calls):
    if not any("could not read which runs" in line for line in lines_tagged(out, "note")):
        return "did not say the gate-or-not distinction went unchecked"
    return expect_clean(rc, out, calls)


def not_admin(rc, out, calls):
    if rc == 0:
        return "exit 0 with two settings unknown"
    unread = lines_tagged(out, "CANNOT READ")
    if len(unread) != 2:
        return f"wanted CANNOT READ for the Actions permission and protection, got {unread}"
    if lines_tagged(out, "NOT SET"):
        return f"reported an unreadable setting as unset: {lines_tagged(out, 'NOT SET')}"
    if any("not required" in line for line in out.splitlines()):
        return "claimed a check is not required without being able to read the rule"
    if "gh auth login" not in out:
        return "did not say how to get a login that can read them"
    return None


def invisible(rc, out, calls):
    if rc == 0:
        return "exit 0 on a repository it cannot see"
    return None if "not visible" in out else "did not say the repository is not visible"


def setup_still_writes(rc, out, calls):
    writes = [call for call in calls if not is_read(call)]
    if not any("actions/permissions/workflow" in " ".join(call) for call in writes):
        return f"the setup path no longer sets the Actions permission; writes were {writes}"
    return None


CASES = [
    ("a repository with everything set verifies clean", ["--verify", REPO], scenario(), expect_clean),
    ("--verify may come after the repository", [REPO, "--verify"], scenario(), expect_clean),
    (
        "an unrecognised flag is refused before any call",
        ["--verfiy", REPO],
        scenario(),
        expect_refused_before_any_call("Unknown option '--verfiy'"),
    ),
    (
        "a mistyped flag after the repository is refused, not ignored",
        [REPO, "--verfiy"],
        scenario(),
        expect_refused_before_any_call("Unknown option '--verfiy'"),
    ),
    (
        "two repositories are refused before any call",
        ["--verify", REPO, "other/repo"],
        scenario(),
        expect_refused_before_any_call("One repository at a time"),
    ),
    (
        "a private repository is wrong",
        ["--verify", REPO],
        scenario(private=True),
        expect_problem("WRONG", "private"),
    ),
    (
        "Actions unable to open pull requests is not set",
        ["--verify", REPO],
        scenario(can_approve=False),
        expect_problem("NOT SET", "may not create pull requests"),
    ),
    (
        "a read-only default token is not set",
        ["--verify", REPO],
        scenario(perms="read"),
        expect_problem("NOT SET", "read-only"),
    ),
    (
        "a missing token secret is not set",
        ["--verify", REPO],
        scenario(secrets=["AGENT_APP_ID", "AGENT_APP_PRIVATE_KEY"]),
        expect_problem("NOT SET", "CLAUDE_CODE_OAUTH_TOKEN"),
    ),
    (
        "secrets this login cannot list are cannot read",
        ["--verify", REPO],
        scenario(secrets=None),
        expect_problem("CANNOT READ", "secrets"),
    ),
    (
        "no agent identity App is optional, and says what it costs",
        ["--verify", REPO],
        scenario(secrets=["CLAUDE_CODE_OAUTH_TOKEN"]),
        no_app,
    ),
    (
        "an App id without its key is wrong",
        ["--verify", REPO],
        scenario(secrets=["CLAUDE_CODE_OAUTH_TOKEN", "AGENT_APP_ID"]),
        expect_problem("WRONG", "AGENT_APP_ID without AGENT_APP_PRIVATE_KEY"),
    ),
    (
        "an App key without its id is wrong",
        ["--verify", REPO],
        scenario(secrets=["CLAUDE_CODE_OAUTH_TOKEN", "AGENT_APP_PRIVATE_KEY"]),
        expect_problem("WRONG", "AGENT_APP_PRIVATE_KEY without AGENT_APP_ID"),
    ),
    (
        "a missing label is named",
        ["--verify", REPO],
        scenario(labels=[name for name in LABELS if name != "agent:revise"]),
        expect_problem("NOT SET", "agent:revise"),
    ),
    (
        "labels are checked against the repository's own release",
        ["--verify", REPO],
        scenario(
            labels=[name for name in LABELS if name != "agent:revise"],
            manifest_labels=[name for name in LABELS if name != "agent:revise"],
        ),
        older_release,
    ),
    (
        "an unprovisioned repository is checked against the factory's labels",
        ["--verify", REPO],
        scenario(labels=[name for name in LABELS if name != "agent:revise"], manifest_labels=None),
        unprovisioned,
    ),
    (
        "a required check that never reported is wrong",
        ["--verify", REPO],
        scenario(required=CHECKS + ["ci / test"]),
        expect_problem("WRONG", "ci / test", "never reported"),
    ),
    (
        "a reported check nobody requires is a note, not a problem",
        ["--verify", REPO],
        scenario(reported=CHECKS + ["ci / lint"]),
        extra_check_is_a_note,
    ),
    (
        "a required check only bootstrap reports is wrong, though it reported",
        ["--verify", REPO],
        scenario(
            required=CHECKS + ["bootstrap / labels and check names"],
            reported=CHECKS + ["bootstrap / labels and check names"],
            events={"bootstrap / labels and check names": "workflow_dispatch"},
        ),
        expect_problem("WRONG", "bootstrap / labels and check names", "every pull request waits on it forever"),
    ),
    (
        "a Pages build on the default branch is not offered as a gate",
        ["--verify", REPO],
        scenario(reported=CHECKS + ["build", "deploy"], events={"build": "dynamic", "deploy": "dynamic"}),
        pages_not_offered,
    ),
    (
        "runs it cannot read are counted, and it says so",
        ["--verify", REPO],
        scenario(runs_readable=False),
        runs_unread,
    ),
    (
        "no protection at all is not set",
        ["--verify", REPO],
        scenario(required=None),
        expect_problem("NOT SET", "nothing requires a status check"),
    ),
    (
        "a classic rule requiring no checks is not set",
        ["--verify", REPO],
        scenario(required=[]),
        expect_problem("NOT SET", "nothing requires a status check"),
    ),
    (
        "a ruleset requiring the checks counts as protection",
        ["--verify", REPO],
        scenario(required=None, rulesets=CHECKS),
        expect_clean,
    ),
    (
        "without administration a ruleset is still read",
        ["--verify", REPO],
        scenario(admin=False, rulesets=CHECKS + ["ci / test"]),
        expect_problem("WRONG", "ci / test", "never reported"),
    ),
    (
        "without administration the two admin settings are cannot read, never not set",
        ["--verify", REPO],
        scenario(admin=False),
        not_admin,
    ),
    (
        "a repository this login cannot see stops and says so",
        ["--verify", REPO],
        scenario(visible=False),
        invisible,
    ),
]


def main() -> int:
    if shutil.which("jq") is None:
        print("setup-project: `jq` is not on PATH. The fake gh applies --jq with it,")
        print("as gh applies its own built-in one, so these cases cannot run without it.")
        return 1

    failures = 0
    for name, args, state, check in CASES:
        rc, out, calls, _ = run(args, state)
        error = check(rc, out, calls)
        writes = [call for call in calls if not is_read(call)] if "--verify" in args else []
        if writes:
            error = f"--verify made {len(writes)} call(s) that are not reads: {writes}"
        if error:
            failures += 1
            print(f"  FAIL {name}: {error}")
        else:
            print(f"  ok   {name}")

    # The flag has to be what removes the writes. A verify mode that wrote
    # nothing because the whole script had stopped writing would pass every
    # case above.
    rc, out, calls, _ = run([REPO], scenario())
    error = setup_still_writes(rc, out, calls)
    if error:
        failures += 1
        print(f"  FAIL without --verify the setup path still writes: {error}")
    else:
        print("  ok   without --verify the setup path still writes")

    # The output file is what a person copies a URL out of, and a verify run
    # has to be told apart from a setup run in it.
    _, _, _, logged = run(["--verify", REPO], scenario())
    if "=== verify " not in logged or "Everything the setup path sets is in place" not in logged:
        failures += 1
        print("  FAIL a verify run is recorded as one in setup-project-output.txt")
    else:
        print("  ok   a verify run is recorded as one in setup-project-output.txt")

    print()
    if failures:
        print(f"setup-project: {failures} failing case(s)")
        return 1
    print(f"setup-project: {len(CASES) + 2} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
