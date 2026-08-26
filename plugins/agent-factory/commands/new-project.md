---
description: Provision a fresh repository end to end - Actions permissions, labels, caller workflows, memory files, and branch protection.
argument-hint: <owner/repo>
allowed-tools: Bash, Read, Write, Edit, Glob
---

Provision `$1` so agents can work in it. Run the steps in order; step 1 first is not a style preference, it is the one that makes every later step actually take effect.

If `$1` is empty, ask which repository before doing anything.

## 1. Allow Actions to create and approve pull requests

This is off by default on personal-account repositories, and with it off, every agent run appears to work and then silently fails to open a pull request.

```
gh api -X PUT "repos/$1/actions/permissions/workflow" \
  -f default_workflow_permissions=write \
  -F can_approve_pull_requests=true
```

Confirm it took by reading the setting back before continuing. If it did not, stop and say so - nothing below is worth doing until this is true.

## 2. Labels

```
gh label create objective            --repo "$1" --color 0B5394 --description "A goal, not a task. The orchestrator splits it." --force
gh label create agent:queued         --repo "$1" --color 1D76DB --description "A human has released this to run." --force
gh label create agent:running        --repo "$1" --color FBCA04 --description "An agent holds this right now." --force
gh label create agent:review         --repo "$1" --color 0E8A16 --description "Agent finished. Waiting on a human." --force
gh label create agent:blocked        --repo "$1" --color B60205 --description "Refused or failed. Needs a human." --force
gh label create needs-decomposition  --repo "$1" --color D93F0B --description "Too big to work as one issue." --force
gh label create role:researcher      --repo "$1" --color 5319E7 --description "Investigates options. Writes to docs/research/." --force
gh label create role:designer        --repo "$1" --color E99695 --description "Specifies flows and states. Writes to docs/design/." --force
gh label create role:engineer        --repo "$1" --color 0052CC --description "Implements and opens the pull request." --force
```

## 3. Caller workflows and project files

Copy from `${CLAUDE_PLUGIN_ROOT}/templates/project/` into the repository, on a branch, as one pull request:

- `.github/workflows/ci.yml`, `agent-run.yml`, `guard.yml` - thin callers, each pointing at `@v1`
- `.github/CODEOWNERS` - set the owner to the repository owner
- `CLAUDE.md` - fill in the product sentence, the stack, and the commands from what is actually in the repository. Do not leave a bracketed placeholder behind.
- `.claude/memory/orchestrator.md`, `researcher.md`, `designer.md`, `engineer.md` - empty, with their headers
- `docs/research/`, `docs/design/`, `docs/decisions/` with the ADR template

## 4. Branch protection

Only after the checks have run once and reported their names - a required check that has never run blocks every merge, including the pull request that would fix it.

```
gh api -X PUT "repos/$1/branches/main/protection" \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["ci / typecheck, lint, test, build", "guard / memory cap and protected paths"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

Read the check names back from the first run rather than trusting the strings above; they follow the job names and change when a job is renamed.

## 5. Report

List what was created, what already existed, and anything that failed, with the exact command that failed. Then state the two things only a human can do: add the `CLAUDE_CODE_OAUTH_TOKEN` secret, and install the agent identity App. Nothing runs without the first one.
