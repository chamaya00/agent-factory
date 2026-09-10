#!/usr/bin/env python3
"""Check that every workflow in the factory parses and stays inside its limits.

A reusable workflow that does not parse fails in the caller's repo, where the
error message is furthest from the person who can fix it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
TEMPLATES = ROOT / "plugins" / "agent-factory" / "templates"

# An agent that can rewrite its own gates has no gates.
FORBIDDEN_PERMISSIONS = {"actions": {"write"}}

errors: list[str] = []


def check(path: Path) -> None:
    try:
        # YAML parses the bare `on:` key as True. That is correct YAML and the
        # workflow still runs; we just have to look it up under both spellings.
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        errors.append(f"{path.relative_to(ROOT)}: does not parse as YAML: {exc}")
        return
    if not isinstance(data, dict):
        errors.append(f"{path.relative_to(ROOT)}: top level is not a mapping")
        return

    triggers = data.get("on", data.get(True))
    if triggers is None:
        errors.append(f"{path.relative_to(ROOT)}: has no 'on' trigger block")

    for job_name, job in (data.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        permissions = job.get("permissions") or {}
        if isinstance(permissions, dict):
            for scope, banned in FORBIDDEN_PERMISSIONS.items():
                if permissions.get(scope) in banned:
                    errors.append(
                        f"{path.relative_to(ROOT)}: job {job_name!r} requests "
                        f"{scope}: {permissions[scope]}, which agents must never hold"
                    )
        if "uses" in job:
            continue
        if "timeout-minutes" not in job:
            errors.append(
                f"{path.relative_to(ROOT)}: job {job_name!r} has no timeout-minutes"
            )

    top_permissions = data.get("permissions") or {}
    if isinstance(top_permissions, dict):
        for scope, banned in FORBIDDEN_PERMISSIONS.items():
            if top_permissions.get(scope) in banned:
                errors.append(
                    f"{path.relative_to(ROOT)}: requests {scope}: "
                    f"{top_permissions[scope]}, which agents must never hold"
                )


# Tools a role can declare that the action does not grant on its own. An agent
# started without them does not fail cleanly, it improvises: it spends the run
# and leaves a comment explaining that it had no tools. Bash is checked as a
# family, since the allowlist grants it one scoped command at a time.
GRANTABLE = ("Write", "Edit", "WebFetch", "WebSearch", "Bash")

AGENTS = ROOT / "plugins" / "agent-factory" / "agents"
ALLOWLIST_STEP = "Resolve the tool allowlist for this role"


def declared_tools(path: Path) -> set[str]:
    """The tools named on the `tools:` line of a role definition's frontmatter."""
    for line in path.read_text().splitlines():
        if line.startswith("tools:"):
            return {tool.strip() for tool in line[len("tools:") :].split(",")}
    return set()


def granted_tools(branch: str, common: str) -> set[str]:
    """The tool names a `case` branch actually assigns to `tools`.

    Parsed rather than substring-matched: the prose in a comment above a branch
    ("Writes code, runs the tests") contains the name of a tool the branch may
    not grant, and a guard that matches that passes a broken allowlist.
    """
    names: set[str] = set()
    for line in branch.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        match = re.match(r'tools="(.*)"\s*$', line)
        if not match:
            continue
        value = match.group(1).replace("$common", common).replace("$tools", "")
        names.update(name.strip() for name in value.split(",") if name.strip())
    return names


def check_roles_can_work() -> None:
    """Every role must be granted the tools its own definition declares.

    This is the check for the failure that produced it: agent-run passed no
    allowlist, so every role ran with a read-only tool set. The orchestrator
    surfaced it first because it runs first, but the engineer was worse off - it
    could not have written a line of code or run a test.
    """
    workflow = WORKFLOWS / "agent-run.yml"
    if not workflow.exists():
        errors.append("agent-run.yml is missing; nothing grants the roles their tools")
        return
    if not AGENTS.is_dir():
        errors.append(f"no role definitions under {AGENTS.relative_to(ROOT)}")
        return

    data = yaml.safe_load(workflow.read_text())
    script = ""
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if isinstance(step, dict) and step.get("name") == ALLOWLIST_STEP:
                script = step.get("run") or ""
    if not script:
        errors.append(
            f".github/workflows/agent-run.yml: no {ALLOWLIST_STEP!r} step. "
            "Without one the action's read-only default is what every role gets."
        )
        return

    # `common` is built up over several lines; fold them into one value so a
    # branch that only says "$common" is checked against what it really gets.
    common = ""
    for line in script.splitlines():
        match = re.match(r"""common=['"](.*)['"]\s*$""", line.strip())
        if match:
            common = match.group(1).replace("$common", common)

    for role_file in sorted(AGENTS.glob("*.md")):
        role = role_file.stem
        # The branch of the case statement that belongs to this role: from its
        # label to the `;;` that closes it.
        start = script.find(f"{role})")
        if start == -1:
            errors.append(
                f".github/workflows/agent-run.yml: no allowlist branch for role "
                f"{role!r}, so it would run with the read-only default"
            )
            continue
        end = script.find(";;", start)
        branch = script[start : end if end != -1 else len(script)]
        granted = granted_tools(branch, common)

        for tool in sorted(declared_tools(role_file) & set(GRANTABLE)):
            if tool == "Bash":
                ok = any(name.startswith("Bash(") for name in granted)
            else:
                ok = tool in granted
            if not ok:
                errors.append(
                    f"role {role!r} declares {tool} but the agent-run allowlist "
                    f"does not grant it; the role cannot do its job"
                )


# Runners that do not assume a package.json. The engineer has to be able to run
# the checks the gate runs, and ci.yml's commands path means the gate is not
# necessarily a Node gate.
NON_NPM_RUNNERS = ("Bash(make", "Bash(pytest", "Bash(python", "Bash(go test",
                   "Bash(cargo", "Bash(bash ", "Bash(sh ", "Bash(./")


def check_engineer_can_run_tests() -> None:
    """The engineer must have a way to run tests that does not assume npm.

    `check_roles_can_work` treats Bash as a family, so an allowlist granting
    nothing but `Bash(npm ...)` satisfies it - which is how a Node-only engineer
    shipped and stayed shipped. On a repository with no package.json that role
    cannot execute its own test script, and it does not fail cleanly: it falls
    back to inline greps, calls the criteria verified, and a test that cannot
    pass on any tree ships looking green.
    """
    workflow = WORKFLOWS / "agent-run.yml"
    if not workflow.exists():
        return

    data = yaml.safe_load(workflow.read_text())
    script = ""
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if isinstance(step, dict) and step.get("name") == ALLOWLIST_STEP:
                script = step.get("run") or ""
    if not script:
        return

    start = script.find("engineer)")
    if start == -1:
        return
    end = script.find(";;", start)
    branch = script[start : end if end != -1 else len(script)]
    granted = granted_tools(branch, "")

    if not any(name.startswith(NON_NPM_RUNNERS) for name in granted):
        errors.append(
            "role 'engineer' is granted no test runner that works without a "
            "package.json, so it cannot run the checks the gate runs on a "
            "non-Node project; ci.yml's commands path exists for exactly those"
        )


def check_allowlist_entries_can_match() -> None:
    """No `Bash(...:*)` entry may end its prefix mid-argument.

    `Bash(x:*)` is shorthand for `Bash(x *)`, and the space is part of the rule,
    so a prefix ending in `/` names a command that cannot exist:
    `Bash(bash tests/:*)` asks for `bash tests/` followed by a space. Six
    entries were written that way and every one of them granted nothing.

    This is the check for the failure that produced it, and it exists next to
    `check_engineer_can_run_tests` because that check passed throughout: it
    confirms a runner entry is present, which says nothing about whether the
    entry can ever match. Run 34200686220 is what the gap cost - an engineer
    that wrote its whole diff, was refused `bash tests/check.sh` by an allowlist
    naming `bash tests/`, and stopped without pushing. Write `Bash(bash
    tests/*)` instead: a bare trailing `*` has no space in front of it.
    """
    workflow = WORKFLOWS / "agent-run.yml"
    if not workflow.exists():
        return

    data = yaml.safe_load(workflow.read_text())
    script = ""
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if isinstance(step, dict) and step.get("name") == ALLOWLIST_STEP:
                script = step.get("run") or ""
    if not script:
        return

    # Assignments only. The comments around them quote the broken form on
    # purpose, and a guard that reads those reports the explanation as the bug.
    entries: set[str] = set()
    for line in script.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        match = re.match(r"""(?:tools|common)=['"](.*)['"]\s*$""", line)
        if not match:
            continue
        value = match.group(1).replace("$common", "").replace("$tools", "")
        entries.update(name.strip() for name in value.split(",") if name.strip())

    for name in sorted(entries):
        match = re.fullmatch(r"Bash\((.*):\*\)", name)
        if match and match.group(1).endswith("/"):
            errors.append(
                f".github/workflows/agent-run.yml: allowlist entry {name} can "
                f"never match. `:*` means the prefix then a space, so this asks "
                f"for a command ending at {match.group(1)!r}; write "
                f"Bash({match.group(1)}*) instead"
            )


HANDBACK_STEP = "Hand back to a human"
PRIVILEGE_STEP = "A change to privilege is declared, not slipped in"
SWEEP_STEP = "Name what is not moving"
ATTEMPT_MARKER = "<!-- agent-factory:attempt -->"


def agent_run_steps() -> list[dict]:
    """Every step of agent-run.yml, or an empty list if it is unreadable."""
    workflow = WORKFLOWS / "agent-run.yml"
    if not workflow.exists():
        return []
    data = yaml.safe_load(workflow.read_text())
    steps: list[dict] = []
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if isinstance(step, dict):
                steps.append(step)
    return steps


def check_prompt_states_the_turn_budget() -> None:
    """The prompt must tell the agent how many turns it has.

    `--max-turns` is passed to the SDK but never mentioned to the agent, so the
    one limit that can kill a run mid-sentence is the one thing the agent cannot
    see. It reads exhaustively, plans to commit at the end, and the cap arrives
    first - the run fails, nothing uncommitted survives, and the attempt is
    spent with no branch to resume from.

    This is the check for the failure that produced it. new-project-agents-v3#19
    ended `error_max_turns` at 41 turns with its checklist stopped at "read the
    design spec": eight minutes and a slice of the subscription, no branch
    pushed, and the issue left agent:blocked as though it had been scoped wrong.
    """
    for step in agent_run_steps():
        if not str(step.get("uses") or "").startswith("anthropics/claude-code-action"):
            continue
        prompt = ((step.get("with") or {}).get("prompt")) or ""
        if "inputs.max-turns" not in prompt:
            errors.append(
                ".github/workflows/agent-run.yml: the agent prompt never states "
                "the turn budget. A cap the agent cannot see is a cap it cannot "
                "spend deliberately; name inputs.max-turns in the prompt."
            )
        return


def check_failure_is_diagnosed() -> None:
    """A failed run must say why on the issue, not just label it.

    `agent:blocked` alone cannot distinguish an agent that got the work wrong
    from a harness that stopped it, and those want opposite responses: rewrite
    the issue, or raise the cap and re-queue. Told nothing, a human reads the
    label as the former and decomposes an issue that was scoped correctly.
    """
    for step in agent_run_steps():
        if step.get("name") != HANDBACK_STEP:
            continue
        script = step.get("run") or ""
        if "claude-execution-output.json" not in script:
            errors.append(
                f".github/workflows/agent-run.yml: the {HANDBACK_STEP!r} step "
                "does not read the action's execution output, so a failed run "
                "leaves a label and no reason. Diagnosing it means reading the "
                "raw job log, which is the wrong place for the person holding "
                "the issue."
            )
        if "comment" not in script:
            errors.append(
                f".github/workflows/agent-run.yml: the {HANDBACK_STEP!r} step "
                "posts no comment on failure; the label is not the diagnosis."
            )
        return
    errors.append(
        f".github/workflows/agent-run.yml: no {HANDBACK_STEP!r} step, so a run "
        "that fails leaves the issue labelled agent:running forever"
    )


def check_only_the_attempt_marker_counts_attempts() -> None:
    """Only the run-start comment may carry the attempt marker.

    Preflight counts attempts by counting comments containing
    `<!-- agent-factory:attempt -->`, so any second comment carrying that string
    doubles the count of every run and refuses the issue after two. The failure
    comment sits in the same workflow and is the obvious place to paste the
    marker from, which is exactly why this is checked rather than remembered.
    """
    for step in agent_run_steps():
        if step.get("name") != HANDBACK_STEP:
            continue
        if ATTEMPT_MARKER in (step.get("run") or ""):
            errors.append(
                f".github/workflows/agent-run.yml: the {HANDBACK_STEP!r} step "
                f"carries {ATTEMPT_MARKER}, which preflight counts. Every run "
                "would spend two attempts and the third would be refused after "
                "one real try. Use a different marker."
            )
        return


def check_concurrency_gates_the_agent_not_the_preflight() -> None:
    """The concurrency group belongs on the agent job, never on the workflow.

    A concurrency group holds exactly one pending entry: a third arrival
    cancels the one already waiting. With the group at workflow level the
    preflight sits in that queue too - and preflight is what decides an event
    is not worth running. So the agent's own writes (labelling an issue
    agent:running, posting its marker) raised events that queued behind the run
    that made them, and cancelled each other and eventually something real.

    Observed, not theorised: in new-project-agents-v3 the orchestrator queued
    its first child and that run was cancelled before its preflight ran a
    single step, displaced by the hand-back step labelling the parent
    agent:review. The child kept agent:queued and nothing ran it.
    """
    workflow = WORKFLOWS / "agent-run.yml"
    if not workflow.exists():
        return
    data = yaml.safe_load(workflow.read_text())
    if not isinstance(data, dict):
        return
    if data.get("concurrency") is not None:
        errors.append(
            ".github/workflows/agent-run.yml: concurrency is set at workflow "
            "level, which puts the preflight in the queue and lets a run be "
            "cancelled before it can decide it was not worth running. Move it "
            "onto the agent job."
        )
    agent = (data.get("jobs") or {}).get("agent") or {}
    if not agent.get("concurrency"):
        errors.append(
            ".github/workflows/agent-run.yml: the agent job has no concurrency "
            "group, so two agent runs can hold the subscription at once."
        )


def check_only_our_own_app_may_start_a_run() -> None:
    """The action refuses bot-started runs, and every handover is bot-started.

    The orchestrator queues a child by labelling it and a finished child wakes
    its parent the same way, so without an allowed_bots value naming the App
    the cascade dies at the first handover - three seconds in, with the issue
    left agent:blocked as though the work had failed.

    It must stay narrow. `*` would let any bot with write access start an agent
    run, and this is the one place where an unexpected trigger spends the
    subscription and pushes a commit.
    """
    for step in agent_run_steps():
        uses = step.get("uses") or ""
        if not uses.startswith("anthropics/claude-code-action"):
            continue
        allowed = str((step.get("with") or {}).get("allowed_bots", "")).strip()
        if not allowed:
            errors.append(
                ".github/workflows/agent-run.yml: the agent step sets no "
                "allowed_bots, so the action refuses every run the "
                "orchestrator starts for itself and the cascade stops at the "
                "first handover."
            )
        elif "*" in allowed:
            errors.append(
                ".github/workflows/agent-run.yml: allowed_bots is "
                f"{allowed!r}. Any bot with write access could then start an "
                "agent run. Name the App's own slug and nothing else."
            )
        return
    errors.append(
        ".github/workflows/agent-run.yml: no anthropics/claude-code-action "
        "step, so nothing runs the agent at all."
    )


def check_a_merge_can_wake_an_objective() -> None:
    """A merge is the other half of the loop and needs its own trigger and job.

    The hand-back tells an objective that a child's run ended. It cannot tell
    it that the child's work landed - the researcher and designer push a branch
    and a human merges it later - and landing is what makes the next child
    ready. Without this an objective reports "waiting on the merge", the merge
    happens, and nothing wakes it.
    """
    template = TEMPLATES / "project" / ".github" / "workflows" / "agent-run.yml"
    if template.exists():
        data = yaml.safe_load(template.read_text())
        triggers = (data or {}).get("on", (data or {}).get(True)) or {}
        pr = triggers.get("pull_request") or {}
        if "closed" not in (pr.get("types") or []):
            errors.append(
                f"{template.relative_to(ROOT)}: no `pull_request: [closed]` "
                "trigger, so a merge raises nothing and an objective stops "
                "mid-chain waiting for one."
            )

    workflow = WORKFLOWS / "agent-run.yml"
    if not workflow.exists():
        return
    data = yaml.safe_load(workflow.read_text())
    jobs = (data or {}).get("jobs") or {}
    wake = jobs.get("wake-on-merge")
    if not wake:
        errors.append(
            ".github/workflows/agent-run.yml: no wake-on-merge job, so the "
            "pull_request trigger the callers carry has nothing to handle it."
        )
    elif "merged == true" not in str(wake.get("if", "")):
        errors.append(
            ".github/workflows/agent-run.yml: wake-on-merge does not require "
            "the pull request to be merged, so closing one unmerged would "
            "queue the objective as though the work had landed."
        )
    preflight_if = str((jobs.get("preflight") or {}).get("if", ""))
    if "pull_request" not in preflight_if:
        errors.append(
            ".github/workflows/agent-run.yml: preflight does not exclude "
            "pull_request events, so a merge would also reach it as a pull "
            "request to work and spend a run on it."
        )


def check_the_diagnosis_reads_the_turn_count() -> None:
    """A run at its cap must be named as such whatever subtype it reports.

    On new-project-agents-v3#46 both attempts reported `success` with 42 and 48
    turns against a cap of 40. Because this branch once keyed on the subtype
    alone, the diagnosis said "ended `success`, 48 turns" and never mentioned
    the cap - so every later reader, human and agent, went looking for a
    different explanation. The count is the evidence; the subtype is a label
    that has been observed to contradict it.
    """
    for step in agent_run_steps():
        if step.get("name") != HANDBACK_STEP:
            continue
        script = step.get("run") or ""
        env = step.get("env") or {}
        if "MAX_TURNS" not in env:
            errors.append(
                f".github/workflows/agent-run.yml: the {HANDBACK_STEP!r} step "
                "has no MAX_TURNS, so it cannot tell a run that hit its cap "
                "from one that did not."
            )
        if "turns >= cap" not in script:
            errors.append(
                f".github/workflows/agent-run.yml: the {HANDBACK_STEP!r} step "
                "does not compare the turn count against the cap, so a run that "
                "died at the cap while reporting `success` is diagnosed as a "
                "success."
            )
        if "git ls-remote" not in script:
            errors.append(
                f".github/workflows/agent-run.yml: the {HANDBACK_STEP!r} step "
                "does not report which branches were pushed, leaving the "
                "orchestrator to infer from the absence of a pull request that "
                "nothing landed."
            )
        return


def check_something_notices_the_silence() -> None:
    """A queued issue with no run must produce a signal, not nothing.

    Five separate faults in this system produced one identical symptom: an
    issue correctly labelled `agent:queued`, nothing running, and nothing in
    any log saying so. Each was found by a human noticing an absence.

    The detector must also stay report-only. Re-queueing from a watchdog is a
    second path into the one place where a bug spends the subscription.
    """
    template = TEMPLATES / "project" / ".github" / "workflows" / "agent-run.yml"
    if template.exists():
        data = yaml.safe_load(template.read_text())
        triggers = (data or {}).get("on", (data or {}).get(True)) or {}
        if not triggers.get("schedule"):
            errors.append(
                f"{template.relative_to(ROOT)}: no schedule trigger, so nothing "
                "ever looks for a queued issue that never started."
            )

    workflow = WORKFLOWS / "agent-run.yml"
    if not workflow.exists():
        return
    data = yaml.safe_load(workflow.read_text())
    jobs = (data or {}).get("jobs") or {}
    stale = jobs.get("stale-queue")
    if not stale:
        errors.append(
            ".github/workflows/agent-run.yml: no stale-queue job, so the "
            "schedule the callers carry has nothing to handle it."
        )
        return
    if "schedule" not in str(stale.get("if", "")):
        errors.append(
            ".github/workflows/agent-run.yml: stale-queue is not restricted to "
            "the schedule, so it would run on ordinary issue events."
        )
    script = " ".join(
        str((step or {}).get("run") or "") for step in (stale.get("steps") or [])
    )
    if "--add-label" in script or "--remove-label" in script:
        errors.append(
            ".github/workflows/agent-run.yml: stale-queue writes a label. It is "
            "meant to report only - re-queueing from a watchdog is a second "
            "path into the one place where a bug spends the subscription."
        )
    if "agent-factory:stalled" not in script:
        errors.append(
            ".github/workflows/agent-run.yml: stale-queue leaves no marker, so "
            "it would repeat its comment on every tick."
        )
    preflight_if = str((jobs.get("preflight") or {}).get("if", ""))
    if "schedule" not in preflight_if:
        errors.append(
            ".github/workflows/agent-run.yml: preflight does not exclude "
            "schedule events, so every tick would reach it as work to do."
        )


def check_a_delivered_run_is_a_review() -> None:
    """A run that got its work out is a review, whatever stopped it.

    The turn cap is a spend limit. It was being read as a verdict too: hitting
    it failed the job, which labelled the issue agent:blocked, which spent an
    attempt - on new-project-agents-v3#50 and #51 all three fired on work that
    was complete, tested, and merged unchanged. The orchestrator had to notice
    and relabel by hand, twice.
    """
    for step in agent_run_steps():
        if step.get("name") != HANDBACK_STEP:
            continue
        script = step.get("run") or ""
        if "delivered()" not in script:
            errors.append(
                f".github/workflows/agent-run.yml: the {HANDBACK_STEP!r} step "
                "does not check whether the run delivered, so a failed job "
                "labels agent:blocked even when a pull request is sitting "
                "ready for review."
            )
        if "isDraft" not in script:
            errors.append(
                f".github/workflows/agent-run.yml: the {HANDBACK_STEP!r} step "
                "does not distinguish a draft pull request from a ready one. A "
                "draft is work in progress and must not count as delivered."
            )
        return


def check_privilege_cannot_arrive_undeclared() -> None:
    """A widening of what the automation may do cannot be silent.

    The merge gate in the house-rules skill asks the person merging to look for
    a new permission, a new secret, an action nobody vetted. That gate is prose,
    and under a standing "merge when green" the person applying it may be a
    session acting on an owner's instruction while the owner is asleep. This is
    the one item on that list with a machine behind it, so it has to survive an
    edit that quietly drops it - including an exemption for maintainers, which
    would exempt exactly the case the check is for.
    """
    path = WORKFLOWS / "project-guard.yml"
    data = yaml.safe_load(path.read_text())
    for job in (data.get("jobs") or {}).values():
        for step in (job or {}).get("steps") or []:
            if step.get("name") != PRIVILEGE_STEP:
                continue
            script = step.get("run") or ""
            for pattern, why in (
                ("permissions:", "a token permission"),
                ("secrets[.:]", "a secret"),
                ("pull_request_target", "a trigger that runs a fork's code"),
                ("uses:", "an action the repository will execute"),
            ):
                if pattern not in script:
                    errors.append(
                        f"project-guard.yml: the {PRIVILEGE_STEP!r} step no "
                        f"longer looks for {why}."
                    )
            if "^Privilege change:" not in script:
                errors.append(
                    f"project-guard.yml: the {PRIVILEGE_STEP!r} step does not "
                    "require the declaration to start a line, so the phrase "
                    "quoted anywhere in a body would pass it."
                )
            # The documentation exclusion is a narrowing, and a narrowing is
            # how a check dies quietly: one more extension each time it is
            # inconvenient, until nothing is read. Markdown cannot grant a
            # permission; a workflow, a script, or a lockfile can. So read the
            # alternation itself rather than looking for a substring - the
            # first version of this check matched ".yml" and sailed past a
            # pattern that had grown "|yml)".
            exclusion = re.search(r"grep -vE '\\\.\(([^)]*)\)\$'", script)
            if exclusion is None:
                errors.append(
                    f"project-guard.yml: cannot find the file-type exclusion "
                    f"in the {PRIVILEGE_STEP!r} step, so nothing here can say "
                    "what it lets through."
                )
            else:
                allowed = {"md", "markdown", "txt", "rst", "adoc"}
                excluded = {e.strip() for e in exclusion.group(1).split("|")}
                for extension in sorted(excluded - allowed):
                    errors.append(
                        f"project-guard.yml: the {PRIVILEGE_STEP!r} step "
                        f"excludes .{extension} files from the scan. Only "
                        "documentation may be excluded - anything that runs "
                        "has to be read."
                    )
            if "MAINTAINERS" in script or "AUTHOR" in script:
                errors.append(
                    f"project-guard.yml: the {PRIVILEGE_STEP!r} step exempts "
                    "some authors. A pull request merged on the owner's behalf "
                    "is authored by a maintainer, and that is the case this "
                    "check exists for."
                )
            return
    errors.append(
        f"project-guard.yml: no {PRIVILEGE_STEP!r} step. Nothing then stops a "
        "diff widening what the automation may do without saying so."
    )


def check_the_sweep_looks_past_the_queue() -> None:
    """Whether the default branch shipped is asked before the queue is read.

    The failure this exists for had nothing queued: the objective was finished
    and closed, and the deployment had been failing for nineteen hours. A
    watchdog that returns early on an empty queue never looks at the branch,
    and an empty queue is exactly the state a finished objective leaves behind.

    So the order is the guarantee, and it is invisible in a diff - moving the
    check below the queue fetch reads as tidying and silently restores the
    blind spot.
    """
    for step in agent_run_steps():
        if step.get("name") != SWEEP_STEP:
            continue
        script = step.get("run") or ""
        if "gh run list" not in script:
            errors.append(
                f".github/workflows/agent-run.yml: the {SWEEP_STEP!r} step does "
                "not read runs on the default branch, so a merge that shipped "
                "nothing is invisible to it."
            )
            return
        looked = script.index("gh run list")
        queue = script.index("gh issue list")
        if looked > queue:
            errors.append(
                f".github/workflows/agent-run.yml: the {SWEEP_STEP!r} step reads "
                "the queue before it reads the default branch. An empty queue "
                "must not stop it looking - a finished objective leaves one."
            )
        return
    errors.append(
        f".github/workflows/agent-run.yml: no {SWEEP_STEP!r} step."
    )


def main() -> int:
    paths = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if TEMPLATES.is_dir():
        paths += sorted(TEMPLATES.rglob("*.yml")) + sorted(TEMPLATES.rglob("*.yaml"))
    if not paths:
        print("guard: no workflows found")
        return 1
    for path in paths:
        check(path)
    check_roles_can_work()
    check_engineer_can_run_tests()
    check_allowlist_entries_can_match()
    check_prompt_states_the_turn_budget()
    check_failure_is_diagnosed()
    check_only_the_attempt_marker_counts_attempts()
    check_concurrency_gates_the_agent_not_the_preflight()
    check_only_our_own_app_may_start_a_run()
    check_a_merge_can_wake_an_objective()
    check_the_diagnosis_reads_the_turn_count()
    check_something_notices_the_silence()
    check_a_delivered_run_is_a_review()
    check_privilege_cannot_arrive_undeclared()
    check_the_sweep_looks_past_the_queue()
    if errors:
        print(f"guard: {len(errors)} problem(s)\n")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"guard: {len(paths)} workflow(s) parse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
