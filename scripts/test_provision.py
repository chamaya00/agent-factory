#!/usr/bin/env python3
"""Run the provision workflow's decisions against a fake `gh`.

That workflow is the one place in this repository that holds an admin token
for every repository the person owns, so its refusals get executed rather than
read. Three steps carry the decisions that matter:

- reading the request, where the one untrusted input - a repository name typed
  into an issue title or a dispatch box - is checked before anything uses it;
- the approval gate, which refuses to go on unless the environment that holds
  the token really does require somebody to approve;
- branch protection, where a wrong check name blocks every merge in the
  project, including the one that would fix it.

Each step's `run:` block is pulled straight out of the workflow and executed
under the same `bash -eo pipefail` a runner uses, so these cases cannot drift
from what ships. The `${{ }}` expressions in each step's env are the runner's
job; they are replaced by the values given here, and a step that grows an env
key this file does not supply fails the run rather than running with it empty.
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
WORKFLOW = ROOT / ".github" / "workflows" / "provision.yml"

OWNER = "example"
FACTORY = "example/agent-factory"
TARGET = "example/new-thing"

FAKE_GH = r"""#!/usr/bin/env python3
import json, os, subprocess, sys

state_path = os.environ["GH_STATE"]
state = json.load(open(state_path))
args = sys.argv[1:]

method, jq, path, reads_stdin = "GET", None, None, False
if args and args[0] == "api":
    rest = args[1:]
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg == "-X":
            method = rest[i + 1]; i += 2; continue
        if arg == "--jq":
            jq = rest[i + 1]; i += 2; continue
        if arg == "--input":
            reads_stdin = rest[i + 1] == "-"; i += 2; continue
        if arg in ("-f", "-F"):
            i += 2; continue
        if path is None:
            path = arg.lstrip("/")
        i += 1
    key = f"{method} {path}"
else:
    key = " ".join(args)

stdin = sys.stdin.read() if reads_stdin else ""
with open(os.environ["GH_CALLS"], "a") as log:
    log.write(json.dumps({"call": key, "stdin": stdin}) + "\n")

routes = state["routes"]
if key not in routes:
    print(f"gh: Not Found (HTTP 404) {key}", file=sys.stderr)
    sys.exit(1)

# A list of responses is a sequence over time: each call takes the next one
# and the last repeats, which is how a run that is still going is faked.
responses = routes[key]
response = responses[0]
if len(responses) > 1:
    routes[key] = responses[1:]
    json.dump(state, open(state_path, "w"))

if response.get("status", 200) >= 400:
    print(f"gh: HTTP {response['status']} {key}", file=sys.stderr)
    sys.exit(1)

body = json.dumps(response.get("body", {}))
if jq is None:
    print(body)
    sys.exit(0)
result = subprocess.run(["jq", "-r", jq], input=body, capture_output=True, text=True)
sys.stdout.write(result.stdout)
sys.exit(result.returncode)
"""


def step(job: str, step_id: str) -> dict:
    data = yaml.safe_load(WORKFLOW.read_text())
    for candidate in data["jobs"][job]["steps"]:
        if candidate.get("id") == step_id:
            return candidate
    raise SystemExit(f"provision.yml: job {job!r} has no step with id {step_id!r}")


def run_step(
    job: str, step_id: str, env: dict[str, str], routes: dict | None = None
) -> dict:
    """Execute one step's shell. Returns the exit code, outputs, calls and report."""
    definition = step(job, step_id)
    unsupplied = set(definition.get("env") or {}) - set(env)
    if unsupplied:
        raise SystemExit(
            f"provision.yml: step {step_id!r} reads {sorted(unsupplied)} from its env, "
            "and this test does not supply them. Add them to the case, or the "
            "step runs here with them empty and proves nothing."
        )

    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        bin_dir = temp / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "gh"
        fake.write_text(FAKE_GH)
        fake.chmod(0o755)
        state = temp / "state.json"
        state.write_text(json.dumps({"routes": routes or {}}))
        calls = temp / "calls.log"
        calls.touch()
        output = temp / "output"
        output.touch()
        runner_temp = temp / "runner"
        runner_temp.mkdir()

        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", definition["run"]],
            capture_output=True,
            text=True,
            env={
                "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/local/bin",
                "HOME": str(temp),
                "GH_STATE": str(state),
                "GH_CALLS": str(calls),
                "GITHUB_OUTPUT": str(output),
                "RUNNER_TEMP": str(runner_temp),
                "POLL_SECONDS": "0",
                "RUN_TRIES": "3",
                "FILE_TRIES": "2",
                **env,
            },
        )

        outputs = {}
        for line in output.read_text().splitlines():
            key, _, value = line.partition("=")
            outputs[key] = value
        report = runner_temp / "provision-report.md"
        refused = runner_temp / "provision-refused.md"
        return {
            "code": result.returncode,
            "outputs": outputs,
            "calls": [json.loads(line) for line in calls.read_text().splitlines()],
            "report": report.read_text() if report.exists() else "",
            "refused": refused.read_text() if refused.exists() else "",
            "stderr": result.stderr,
        }


failures = 0


def check(name: str, problems: list[str], result: dict) -> None:
    global failures
    if problems:
        failures += 1
        print(f"  FAIL {name}")
        for problem in problems:
            print(f"       {problem}")
        if result.get("stderr"):
            print("       stderr: " + result["stderr"].strip().replace("\n", "\n               "))
    else:
        print(f"  ok   {name}")


# --- the request -------------------------------------------------------------


def request_case(name: str, *, title: str = "", dispatch: str | None = None,
                 expect_repo: str | None = None) -> None:
    env = {
        "EVENT": "workflow_dispatch" if dispatch is not None else "issues",
        "TITLE": title,
        "INPUT": dispatch or "",
        "OWNER": OWNER,
        "FACTORY": FACTORY,
    }
    result = run_step("request", "request", env)
    problems = []
    if expect_repo is None:
        if result["code"] == 0:
            problems.append("accepted, expected a refusal")
        if result["outputs"]:
            problems.append(f"wrote outputs on a refusal: {result['outputs']}")
        if not result["refused"].strip():
            problems.append("refused without saying why on the request")
    else:
        if result["code"] != 0:
            problems.append(f"exit {result['code']}, expected 0")
        if result["outputs"].get("repo") != expect_repo:
            problems.append(f"repo {result['outputs'].get('repo')!r}, expected {expect_repo!r}")
        if result["outputs"].get("name") != expect_repo.split("/", 1)[1]:
            problems.append(f"name {result['outputs'].get('name')!r}")
    if result["calls"]:
        problems.append("called gh while reading the request; it holds no token and needs none")
    check(name, problems, result)


def request_cases() -> None:
    print("the request")
    request_case("an issue titled provision owner/repo is read",
                 title=f"provision {TARGET}", expect_repo=TARGET)
    request_case("a dispatch reads the typed repository",
                 dispatch=TARGET, expect_repo=TARGET)
    request_case("whitespace around the name is trimmed",
                 dispatch=f"  {TARGET}  ", expect_repo=TARGET)
    # The account's own spelling goes out, because it is what the token knows.
    request_case("the owner is matched case-insensitively and normalised",
                 title="Provision EXAMPLE/new-thing", expect_repo=TARGET)
    request_case("a title that does not start with provision is refused",
                 title=f"please set up {TARGET}")
    request_case("provisional is not provision",
                 title=f"provisional {TARGET}")
    request_case("an empty dispatch is refused", dispatch="")
    request_case("another account's repository is refused",
                 dispatch="somebody-else/new-thing")
    request_case("the factory itself is refused", dispatch=FACTORY)
    request_case("the factory itself is refused in any case",
                 dispatch="Example/Agent-Factory")
    request_case("a dot is not a repository", dispatch=f"{OWNER}/.")
    request_case("two dots are not a repository", dispatch=f"{OWNER}/..")
    request_case("a path is not a repository", dispatch=f"{OWNER}/../other")
    request_case("a bare name with no owner is refused", dispatch="new-thing")
    # The name reaches a shell and GITHUB_OUTPUT. None of these may get past
    # the shape check, and a newline must not be able to write a second output.
    for hostile in (
        f"{TARGET}; rm -rf /",
        f"{OWNER}/$(id)",
        f"{OWNER}/thing`id`",
        f"{TARGET}\nrepo=somebody-else/thing",
        f"{TARGET} extra",
    ):
        request_case(f"refused: {hostile!r}", dispatch=hostile)


# --- the approval gate -------------------------------------------------------

ENVIRONMENT = f"GET repos/{FACTORY}/environments/provision"

REVIEWERS = {"type": "required_reviewers", "reviewers": [{"type": "User"}]}
BRANCH_RULE = {"type": "branch_policy"}
BRANCH_POLICY = {"protected_branches": False, "custom_branch_policies": True}


def gate_case(name: str, *, environment: dict | None, ref: str = "refs/heads/main",
              expect_pass: bool, expect_no_calls: bool = False) -> None:
    routes = {}
    if environment is not None:
        routes[ENVIRONMENT] = [{"body": environment}]
    env = {
        "GH_TOKEN": "fake-token",
        "FACTORY": FACTORY,
        "REF": ref,
        "DEFAULT_BRANCH": "main",
    }
    result = run_step("request", "gate", env, routes)
    problems = []
    if expect_pass and result["code"] != 0:
        problems.append(f"exit {result['code']}, expected the gate to pass")
    if not expect_pass:
        if result["code"] == 0:
            problems.append("passed, expected a refusal")
        if not result["refused"].strip():
            problems.append("refused without saying why on the request")
    if expect_no_calls and result["calls"]:
        problems.append(f"made calls before refusing: {[c['call'] for c in result['calls']]}")
    check(name, problems, result)


def gate_cases() -> None:
    print("the approval gate")
    gate_case("a required reviewer and a branch policy pass",
              environment={"protection_rules": [REVIEWERS, BRANCH_RULE],
                           "deployment_branch_policy": BRANCH_POLICY},
              expect_pass=True)
    gate_case("no provision environment is refused", environment=None, expect_pass=False)
    gate_case("an environment with no rules is refused",
              environment={"protection_rules": [], "deployment_branch_policy": BRANCH_POLICY},
              expect_pass=False)
    # A wait timer is a protection rule too, and approves nothing.
    gate_case("a wait timer is not a reviewer",
              environment={"protection_rules": [{"type": "wait_timer", "wait_timer": 5}, BRANCH_RULE],
                           "deployment_branch_policy": BRANCH_POLICY},
              expect_pass=False)
    gate_case("a reviewer with every branch allowed is refused",
              environment={"protection_rules": [REVIEWERS], "deployment_branch_policy": None},
              expect_pass=False)
    gate_case("a run started from another branch is refused before any call",
              environment={"protection_rules": [REVIEWERS, BRANCH_RULE],
                           "deployment_branch_policy": BRANCH_POLICY},
              ref="refs/heads/edited-copy", expect_pass=False, expect_no_calls=True)


# --- branch protection -------------------------------------------------------

SHA = "abc123"
RUNS = f"GET repos/{TARGET}/actions/runs?head_sha={SHA}&event=push&per_page=100"
PROTECTION = f"GET repos/{TARGET}/branches/main/protection"
PUT_PROTECTION = f"PUT repos/{TARGET}/branches/main/protection"
ADD_CONTEXTS = f"POST repos/{TARGET}/branches/main/protection/required_status_checks/contexts"

CI_NAME = "ci / checks"
GUARD_NAME = "guard / memory cap and protected paths"


def run(run_id: int, path: str, status: str = "completed", conclusion: str | None = "success") -> dict:
    return {"id": run_id, "path": path, "status": status, "conclusion": conclusion}


CI = run(1, ".github/workflows/ci.yml")
GUARD = run(2, ".github/workflows/guard.yml")
# Push-triggered and on the same commit, and still not a gate: requiring it
# would block every pull request, which never runs it.
DEPLOY = run(3, ".github/workflows/deploy.yml")


def jobs(*names: str) -> list[dict]:
    return [{"body": {"jobs": [{"name": name} for name in names]}}]


def protection_routes(runs_over_time: list[list[dict]], *, existing: bool = False,
                      readback: list[str] | None = None) -> dict:
    after = {"required_status_checks": {"contexts": readback if readback is not None
                                        else [CI_NAME, GUARD_NAME]}}
    routes = {
        f"GET repos/{TARGET}/commits/main": [{"body": {"sha": SHA}}],
        RUNS: [{"body": {"workflow_runs": runs}} for runs in runs_over_time],
        f"GET repos/{TARGET}/actions/runs/1/jobs?per_page=100": jobs(CI_NAME),
        f"GET repos/{TARGET}/actions/runs/2/jobs?per_page=100": jobs(GUARD_NAME),
        f"GET repos/{TARGET}/actions/runs/3/jobs?per_page=100": jobs("deploy / publish"),
        f"POST repos/{TARGET}/actions/runs/2/rerun": [{"body": {}}],
        PUT_PROTECTION: [{"body": {}}],
        ADD_CONTEXTS: [{"body": []}],
    }
    if existing:
        routes[PROTECTION] = [{"body": after}]
    else:
        routes[PROTECTION] = [{"status": 404}, {"body": after}]
    return routes


def protection_case(name: str, routes: dict | None, *, files: str = "present",
                    expect_set: bool, expect_call: str | None = None,
                    forbid_call: str | None = None, expect_contexts: list[str] | None = None,
                    expect_reruns: int | None = None, expect_mention: str | None = None,
                    forbid_rule: bool = False) -> None:
    env = {"GH_TOKEN": "fake-token", "BRANCH": "main", "FILES": files, "REPO": TARGET}
    result = run_step("provision", "protection", env, routes)
    calls = [c["call"] for c in result["calls"]]
    problems = []
    if result["code"] != 0:
        problems.append(f"exit {result['code']}; this step records and carries on, it never fails the job itself")
    ticked = result["report"].startswith("- [x] Branch protection")
    unticked = result["report"].startswith("- [ ] Branch protection")
    if expect_set and not ticked:
        problems.append(f"report reads {result['report'].strip()!r}, expected it confirmed")
    if not expect_set:
        if not unticked:
            problems.append(f"report reads {result['report'].strip()!r}, expected an unticked line")
    if forbid_rule and (PUT_PROTECTION in calls or ADD_CONTEXTS in calls):
        problems.append("set a rule anyway")
    if expect_call and expect_call not in calls:
        problems.append(f"never called {expect_call}")
    if forbid_call and forbid_call in calls:
        problems.append(f"called {forbid_call}")
    if expect_contexts is not None:
        sent = [c for c in result["calls"] if c["call"] in (PUT_PROTECTION, ADD_CONTEXTS)]
        if not sent:
            problems.append("sent no contexts at all")
        else:
            body = json.loads(sent[0]["stdin"])
            got = body["contexts"] if "contexts" in body else body["required_status_checks"]["contexts"]
            if sorted(got) != sorted(expect_contexts):
                problems.append(f"required {got}, expected {expect_contexts}")
    if expect_reruns is not None:
        reruns = sum(1 for c in calls if c.endswith("/rerun"))
        if reruns != expect_reruns:
            problems.append(f"{reruns} re-run(s), expected {expect_reruns}")
    if expect_mention and expect_mention not in result["report"]:
        problems.append(f"report does not name {expect_mention!r}: {result['report'].strip()!r}")
    check(name, problems, result)


def protection_cases() -> None:
    print("branch protection")
    protection_case(
        "a fresh repository requires the two gates and nothing else",
        protection_routes([[CI, GUARD, DEPLOY]]),
        expect_set=True, expect_call=PUT_PROTECTION,
        expect_contexts=[CI_NAME, GUARD_NAME], expect_reruns=0,
    )
    protection_case(
        "a run path carrying a ref still counts as its gate",
        protection_routes([[run(1, ".github/workflows/ci.yml@refs/heads/main"),
                            run(2, ".github/workflows/guard.yml@refs/heads/main")]]),
        expect_set=True, expect_contexts=[CI_NAME, GUARD_NAME],
    )
    protection_case(
        "an existing rule is added to, never replaced",
        protection_routes([[CI, GUARD]], existing=True),
        expect_set=True, expect_call=ADD_CONTEXTS, forbid_call=PUT_PROTECTION,
        expect_contexts=[CI_NAME, GUARD_NAME],
    )
    protection_case(
        "a guard that failed at startup is re-run once, then required",
        protection_routes([
            [CI, run(2, ".github/workflows/guard.yml", conclusion="startup_failure")],
            [CI, run(2, ".github/workflows/guard.yml", status="in_progress", conclusion=None)],
            [CI, GUARD],
        ]),
        expect_set=True, expect_contexts=[CI_NAME, GUARD_NAME], expect_reruns=1,
    )
    # The guard's run then has no jobs, so its check name has never existed.
    stuck_routes = protection_routes(
        [[CI, run(2, ".github/workflows/guard.yml", conclusion="startup_failure")]])
    stuck_routes[f"GET repos/{TARGET}/actions/runs/2/jobs?per_page=100"] = [{"body": {"jobs": []}}]
    protection_case(
        "a guard still failing at startup after one re-run sets nothing",
        stuck_routes, expect_set=False, forbid_rule=True, expect_reruns=1, expect_mention="guard",
    )
    protection_case(
        "a gate that never ran sets nothing, rather than requiring the other alone",
        protection_routes([[CI]]), expect_set=False, forbid_rule=True, expect_mention="guard",
    )
    protection_case(
        "a gate still running when the wait ends sets nothing",
        protection_routes([[CI, run(2, ".github/workflows/guard.yml", status="in_progress", conclusion=None)]]),
        expect_set=False, forbid_rule=True, expect_mention="guard",
    )
    protection_case(
        "no gate files on the default branch makes no calls and sets nothing",
        {}, files="absent", expect_set=False, forbid_rule=True,
    )
    protection_case(
        "a rule that does not read back is reported, not claimed",
        protection_routes([[CI, GUARD]], readback=[CI_NAME]),
        expect_set=False, expect_call=PUT_PROTECTION, expect_mention=GUARD_NAME,
    )


def main() -> int:
    if subprocess.run(["which", "jq"], capture_output=True).returncode != 0:
        print("test_provision: jq is not installed, and the workflow's steps use it")
        return 1
    request_cases()
    gate_cases()
    protection_cases()
    if failures:
        print(f"\ntest_provision: {failures} case(s) failed")
        return 1
    print("\ntest_provision: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
