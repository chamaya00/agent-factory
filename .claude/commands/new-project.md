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
work with the `mcp__github__*` tools named in each step. Four things cannot be
done from there at all: creating the repository, the Actions permission, the
labels, and branch protection. Those are steps 2, 1, 4, and 5, and each is
handed over in place.

The first two of those fail for the same reason, and it is worth knowing which
kind of failure to expect. A session token is a GitHub App installation on a
set of repositories. It can act inside them, within the permissions granted,
and it holds nothing at the account level - so creating a repository and
changing a repository setting both come back `403 Resource not accessible by
integration`. That message names no permission and no fix. Read it as "this
needs a human", not as a bug to route around.

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

**Missing entirely.** Hand it over. A session token is installed on the
repositories it was granted, and creating a new one is an account-level
permission no installation carries, so `mcp__github__create_repository` returns
`403 Resource not accessible by integration` rather than creating anything. Do
not try it first to see: the failure looks identical to a repository that
exists but is unreachable, and guessing between the two wastes a turn.

Give them exactly this, and wait:

> 1. Open `github.com/new`
> 2. Repository name: the name in `$1`
> 3. **Public**. A private repository cannot call the factory's reusable
>    workflows, so every check fails before it starts.
> 4. Tick **Add a README file**. Without a first commit there is no default
>    branch, and every step below needs one to branch from.
> 5. **Create repository**

**Present but empty.** Same missing first commit, one tap: ask them to add a
README from the web UI.

Once it exists, the session may still not be able to see it - a new repository
is outside whatever the token was granted at the start of the session. If reads
fail, say so and ask them to grant access to it rather than reporting the
repository as missing.

Note the default branch name from `mcp__github__list_branches` and use it
everywhere below rather than assuming it is `main`.

## 3. Caller workflows and project files

One branch, one pull request. Create the branch with `mcp__github__create_branch`,
push every file in a single commit with `mcp__github__push_files`, then open the
pull request with `mcp__github__create_pull_request`.

Everything you copy below comes out of the factory itself.
`${CLAUDE_PLUGIN_ROOT}` is set only when the factory is installed as a plugin,
which does not happen in a cloud session, so use it if it is set and otherwise
use `plugins/agent-factory/` in the checkout you are running in. Call that
directory the factory root and resolve every path below against it. If neither
exists you are not in the factory - stop and say so.

Read the version out of `<factory root>/.claude-plugin/plugin.json`
first. That is the release this repository gets pinned to, and it goes in
several places below, so read it once and use the same value everywhere.

Read each file out of `<factory root>/templates/project/` and send its
contents through. Every `__FACTORY_VERSION__` in a template is replaced with
`v` plus that version - for example `v1.2.0`. A placeholder that survives into
the repository fails as an invalid workflow reference on the first run.

What goes in:

- `.github/workflows/ci.yml`, `agent-run.yml`, `guard.yml`, `bootstrap.yml` -
  thin callers, each pinned to that release. `ci.yml` ships a placeholder gate
  rather than the four scripts, because a repository being provisioned usually
  has no stack yet, and the Node path fails a named script that is not there
  rather than skipping it - which would make this very pull request red. If the
  repository already has `typecheck`, `lint`, `test`, and `build`, switch to the
  Node path now; the comment at the top of the template says how. Otherwise
  leave it alone and say in the pull request body that the gate is a placeholder,
  what it does check, and that it fails the moment product code lands.
- `.github/CODEOWNERS` - set the owner to the repository owner
- `CLAUDE.md` - fill in the product sentence, the stack, and the commands from
  what is actually in the repository. Do not leave a bracketed placeholder
  behind; if you cannot tell what belongs in one, ask rather than guess.
- `.claude/memory/orchestrator.md`, `researcher.md`, `designer.md`,
  `engineer.md` - empty, with their headers
- `.claude/agent-factory.json` - the record of which release this repository
  took, with the version filled in
- `docs/research/`, `docs/design/`, `docs/decisions/` with the ADR template

Then the roles and the commands themselves, copied rather than referenced:

- `.claude/agents/*.md` - every file in `<factory root>/agents/`
- `.claude/skills/*/SKILL.md` - every skill in `<factory root>/skills/`
- `.claude/commands/retro.md`, `decompose.md`, `update-agents.md` - from
  `<factory root>/commands/`. Not `new-project.md`: provisioning is the
  factory's job, and a project that can provision another project is a way to
  get a second factory nobody is maintaining.

Copy them verbatim. These are the same definitions an agent run reads, and the
agent job refuses to start without them.

The commands are copied for the same reason as everything else here, and it is
the only thing that works: a session reads commands, agents, and skills out of
the repository it cloned, and installs no plugin. A marketplace declared in
`.claude/settings.json` is dropped unless the folder has been trusted, and a
cloud session has nobody to answer the trust prompt, so a project that relied
on one would open with none of these commands. Copying is what puts `/retro`,
`/decompose`, and `/update-agents` in a session opened on this repository.

Copying rather than fetching is the whole design. It means this repository's
agents keep behaving the way they behaved on the day it was provisioned, no
matter what happens in the factory afterwards, and it means the roles are
visible in the diff here rather than resolved from somewhere else at run time.
`/update-agents` is how a later release gets in, one reviewed pull request at
a time.

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

Notice which names those are. On the placeholder gate the ci job reports as
`scaffolding` rather than as the four scripts, and it changes the day somebody
restores the Node path. That is why the template says to re-point this rule in
the same sitting: a required check that no longer reports blocks every merge
instead of gating them.

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

If the gate went in as a placeholder, say so here too, and say what replaces it.
It is the one outstanding item that looks like nothing is wrong: every check is
green, and none of them is testing the product.
