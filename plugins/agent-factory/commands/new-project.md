---
description: Provision a fresh repository end to end - caller workflows, project files, labels, and the two settings only a human can change.
argument-hint: <owner/repo>
allowed-tools: Bash, Read, Write, Edit, Glob, mcp__github__get_file_contents, mcp__github__create_repository, mcp__github__create_branch, mcp__github__push_files, mcp__github__create_pull_request, mcp__github__get_label, mcp__github__list_branches
---

Provision `$1` so agents can work in it.

If `$1` is empty, ask which repository before doing anything.

## How to do the work

Check once, at the start, and say which path you are on:

```
command -v gh
```

**No `gh`** - the normal case, because this runs in a cloud session. Do the file
work with the `mcp__github__*` tools named in each step. Three things have no
tool at all in that environment: the Actions permission, the labels, and branch
protection. Those are steps 1, 4, and 5, and they are handled without one.

**`gh` present and authenticated** - you may use it for steps 4 and 5 directly
instead of handing them over, and should. Step 1 still cannot be scripted from
a session token; leave it as a human step either way.

Do not fake progress on a step you cannot perform. A step reported as done that
was not done is worse than a step reported as blocked, because the failure it
causes surfaces three steps later, somewhere unrelated.

## 1. Allow Actions to create and approve pull requests

Stop and hand this to the human. It is off by default on personal-account
repositories, and with it off every agent run appears to work and then silently
fails to open a pull request. It cannot be set from a session token: it is a
repository administration setting.

Give them exactly this, and wait for confirmation before continuing:

> 1. Open `github.com/$1/settings/actions`
> 2. Scroll to **Workflow permissions**
> 3. Select **Read and write permissions**
> 4. Tick **Allow GitHub Actions to create and approve pull requests**
> 5. **Save**

Nothing below is worth doing until they confirm. Ask again rather than assuming.

## 2. Make sure the repository exists and has a commit

Read the repository root with `mcp__github__get_file_contents`.

- Missing entirely: create it with `mcp__github__create_repository`, passing
  `autoInit: true`. A repository with no commits has no default branch, and
  every later step needs one to branch from.
- Present but empty: ask the human to add a README from the web UI, which
  creates the first commit.

Note the default branch name from `mcp__github__list_branches` and use it
everywhere below rather than assuming it is `main`.

## 3. Caller workflows and project files

One branch, one pull request. Create the branch with `mcp__github__create_branch`,
push every file in a single commit with `mcp__github__push_files`, then open the
pull request with `mcp__github__create_pull_request`.

Read each file out of `${CLAUDE_PLUGIN_ROOT}/templates/project/` and send its
contents through. What goes in:

- `.github/workflows/ci.yml`, `agent-run.yml`, `guard.yml`, `bootstrap.yml` -
  thin callers, each pointing at `@v1`
- `.github/CODEOWNERS` - set the owner to the repository owner
- `CLAUDE.md` - fill in the product sentence, the stack, and the commands from
  what is actually in the repository. Do not leave a bracketed placeholder
  behind; if you cannot tell what belongs in one, ask rather than guess.
- `.claude/memory/orchestrator.md`, `researcher.md`, `designer.md`,
  `engineer.md` - empty, with their headers
- `docs/research/`, `docs/design/`, `docs/decisions/` with the ADR template

Say in the pull request body that `bootstrap` has to be run by hand once this
merges, and why the two remaining steps are manual.

## 4. Labels

The labels are created by the `bootstrap` workflow rather than from here, and
its names are matched exactly by the agent-run preflight, so they are worth
getting from one place rather than retyping.

`workflow_dispatch` only sees workflows that are already on the default branch.
So the human merges the pull request from step 3 first, then:

> 1. Open `github.com/$1/actions/workflows/bootstrap.yml`
> 2. Tap **Run workflow**, then **Run workflow** again to confirm
> 3. When it finishes, open the run and read its summary

The summary lists the nine labels and, more usefully, the check names as they
were actually reported. Step 5 needs those.

Verify a sample rather than trusting the run: `mcp__github__get_label` for
`agent:queued` and `role:engineer`. If either is missing the run did not do what
it said.

## 5. Branch protection

Also a human step, and deliberately so. Setting it needs an administration
token, and an identity that can set a gate can remove one - which is the thing
this whole arrangement is built to prevent. It is worth the minute it costs.

Only after the checks have run at least once and reported their names. A
required check that has never run blocks every merge, including the pull
request that would fix it.

Give them the names from the step 4 summary, verbatim, then:

> 1. Open `github.com/$1/settings/branches`
> 2. **Add branch protection rule** (or **Add classic branch protection rule**)
> 3. Branch name pattern: the default branch name
> 4. Tick **Require status checks to pass before merging**
> 5. Tick **Require branches to be up to date before merging**
> 6. Search for each check name and select it
> 7. Leave **Require a pull request before merging** unticked, so you can still
>    commit directly when you need to
> 8. **Create**

## 6. Report

List what was created, what already existed, and anything that failed, with the
exact call that failed.

Then state plainly which of steps 1, 4, and 5 are waiting on the human, and the
two things that no part of this command can do for them:

- Add `CLAUDE_CODE_OAUTH_TOKEN` as a repository secret on this repository.
  Secrets are per repository, and nothing agent-side runs without it.
- Install the agent identity App on this repository, if they made one. Without
  it, every agent pull request needs an approval tap before its checks will run.
