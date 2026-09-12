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

Where the files land depends on what is already in the repository. Decide that
before you write anything.

**A fresh repository** - nothing in it but the README from step 2, or nothing
at all. Push every file in a single commit straight to the default branch with
`mcp__github__push_files`. No branch, no pull request.

There is nothing to review against on an empty repository. The diff is the
whole tree, the alternative to merging it is a repository that does nothing,
and a pull request nobody can meaningfully reject costs a merge tap and a wait.
It also removes an ordering trap: `workflow_dispatch` only sees workflows that
are already on the default branch, so with a pull request in the way step 4
cannot start until a human comes back and merges. Pushed directly,
`bootstrap.yml` is runnable the moment this step finishes. Branch protection is
not set until step 5, so this is not routing around a gate - it is arriving
before there is one.

**A repository with anything else in it** - existing code, existing workflows,
a second provisioning attempt. One branch, one pull request:
`mcp__github__create_branch`, then `mcp__github__push_files` onto that branch,
then `mcp__github__create_pull_request`. Here the diff is a real question.
These files land next to work somebody already did, and `ci.yml` in particular
may be about to replace a gate that is doing its job.

Check rather than assume: read the tree with `mcp__github__get_file_contents`.
Anything beyond a README, a LICENSE, or a `.gitignore` puts you on the pull
request path. If you cannot tell, take the pull request path - it is the one
that is wrong in the recoverable direction.

Either way it is one commit, and the rest of this step is what goes in it.

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

  **Then ask what publishes this repository, and whether the gate runs it.**
  A gate runs the commands the project chose; production runs whatever the
  hosting platform chose. Those are two programs, and nothing measures the
  distance between them unless somebody looks now. A repository once had a gate
  that was green on every pull request for nineteen hours while the thing that
  publishes it failed on all eight merges, because the two builds did not agree
  on what the site even consisted of.

  Three honest answers, in order of preference. The gate already runs what
  publishes it - say so in the pull request body, and it is settled. It does
  not, but it can - change the `commands` so it does. It cannot, because the
  platform builds somewhere this gate cannot reach - then say so in an ADR:
  what publishes it, how that differs from the gate, and what covers the gap.
  The scheduled sweep reports a red default branch, so the gap is bounded in
  time rather than unbounded, and the ADR is what tells the next reader that
  bound is the whole of the protection.

  What is not acceptable is not answering. An unstated assumption here is
  invisible until it has been wrong for a day.
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

- `.claude/hooks/session-start.sh` - from the template, and **executable**;
  a hook without the execute bit is wired, silent, and looks like it ran
- `.claude/settings.json` - from the template, which wires that hook and
  carries nothing else. Permissions and env are the project's to add later
- `.claude/agents/*.md` - every file in `<factory root>/agents/`
- `.claude/skills/*/SKILL.md` - every skill in `<factory root>/skills/`
- `.claude/commands/objective.md`, `retro.md`, `decompose.md`, `update-agents.md`,
  `ship.md` - from
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
`/decompose`, `/update-agents`, and `/ship` in a session opened on this
repository.

Copying rather than fetching is the whole design. It means this repository's
agents keep behaving the way they behaved on the day it was provisioned, no
matter what happens in the factory afterwards, and it means the roles are
visible in the diff here rather than resolved from somewhere else at run time.
`/update-agents` is how a later release gets in, one reviewed pull request at
a time.

On the pull request path, say in the body that `bootstrap` has to be run by
hand once this merges, and why the remaining steps are manual. On the direct
push path there is no body to say it in, which is the one thing the pull
request was doing that this gives up. It moves to the report in step 6, and
that report is then the only place it is said - so do not let it fall out.

## 4. Labels

The labels are created by the `bootstrap` workflow rather than from here, and
its names are matched exactly by the agent-run preflight, so they are worth
getting from one place rather than retyping.

`workflow_dispatch` only sees workflows that are already on the default branch.
On the direct push path they are already there and this can be run at once. On
the pull request path the human merges step 3 first. Then:

> 1. Open `github.com/$1/actions/workflows/bootstrap.yml`
> 2. Tap **Run workflow**, then **Run workflow** again to confirm
> 3. When it finishes, open the run and read its summary

The summary lists the ten labels and, more usefully, the check names as they
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

Two parts, and the second one is the deliverable.

First, plainly: what was created, whether it went to the default branch or to a
pull request, what already existed, and anything that failed - with the exact
call that failed.

Then everything still waiting on the human, in the order it has to happen, each
one as the URL that does it. Substitute `$1` and the default branch name. A
reader assembling a settings URL by hand is a reader who ends up on the wrong
page, and this is the whole reason the list is here rather than in prose:

> 1. **Run bootstrap** - `github.com/$1/actions/workflows/bootstrap.yml`
>    Run workflow, then read the run summary for the check names. On the pull
>    request path, merge that pull request first or this page will not offer
>    the workflow.
> 2. **Add the secrets** - `github.com/$1/settings/secrets/actions/new`
>    `CLAUDE_CODE_OAUTH_TOKEN`, and `AGENT_APP_ID` with
>    `AGENT_APP_PRIVATE_KEY` if the agent identity App exists.
> 3. **Install the App here** - `github.com/settings/installations`
>    Nothing to do if there is no App. Without it every agent pull request
>    lands needing an approval tap before its checks will run.
> 4. **Branch protection** - `github.com/$1/settings/branches`
>    Using the check names from the step 1 summary, not guessed ones.

Say why the ones that are blocked are blocked, rather than leaving them looking
like things you forgot: the secrets because secrets are per repository and
nothing agent-side runs without them, the protection rule because setting it
needs an administration token and an identity that can set a gate can remove
one.

If the gate went in as a placeholder, say so here too, and say what replaces it.
It is the one outstanding item that looks like nothing is wrong: every check is
green, and none of them is testing the product.
