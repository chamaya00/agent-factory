---
description: Set up a repository so agents can work in it - the role, skill, and command files, the gate workflows, and the labels - then hand back the one or two settings only the person can change. No token, App, or secret is involved.
argument-hint: <owner/repo>
allowed-tools: Bash, Read, Write, Edit, Glob, mcp__github__get_file_contents, mcp__github__create_branch, mcp__github__push_files, mcp__github__create_pull_request, mcp__github__get_label, mcp__github__list_branches, mcp__github__actions_run_trigger, mcp__github__actions_list, mcp__github__actions_get, mcp__github__get_job_logs, mcp__github__issue_write, mcp__github__issue_read
---

Set up `$1` so agents can work in it.

If `$1` is empty, ask which repository before doing anything.

Most of this is file work you do yourself. What comes back to the person is
short, and say so before starting so nothing after it is a surprise: creating
the repository if it does not exist, one tap to run `bootstrap`, and - strongly
recommended - one settings page for branch protection. Nothing else. There is
no token to generate, no App to create, and no secret to paste: agents run in
Claude Code sessions, which already work as the person who opened them.

## Verify, do not take "done" for an answer

Most of what goes wrong here is a step somebody believes is finished. So every
handoff below gives the link, says what to do on that page, and names a check
to run afterwards. Run it. A person's "done" and the repository's actual state
disagree often enough to be worth one call, and when they disagree, say so and
hand the link back rather than letting it surface three steps later somewhere
unrelated.

Branch protection cannot be read from a session at all. It is reported as taken
on trust rather than confirmed, and the first pull request confirms it in
passing.

## Where the factory comes from

You need a checkout of the factory to copy from. Either:

- **This session is on the factory.** Use the checkout you are in.
- **This session is on `$1` itself**, and the person pointed you at a factory -
  `github.com/<owner>/agent-factory`, by default the one in their message. Clone
  it at its newest release tag, outside this repository's working tree:

  ```
  git ls-remote --tags --sort=-v:refname https://github.com/<owner>/agent-factory 'v*' | head -1
  git clone --depth 1 --branch <that tag> https://github.com/<owner>/agent-factory <scratch dir>/factory
  ```

  A public factory needs nothing attached to clone. If the clone is refused,
  say so and stop rather than copying files from memory.

Either way, read `plugins/agent-factory/.claude-plugin/plugin.json` in that
checkout before anything else. Two values come out of it and go in several
places below:

- `version` is the release this repository gets pinned to. A tag `v<version>`
  must exist in the factory, or every check in `$1` fails as an invalid
  workflow reference. On a clone of a tag it does by construction; on the
  factory's own checkout, check the tags and stop if it is missing - cutting
  one is the factory owner's step, from its Actions tab.
- `repository` is which factory this is. Take the `owner/repo` out of the URL.
  That is what every caller in `$1` will name, so a person who did not fork the
  factory gets upstream's releases through `/update-agents`, and a fork gets its
  own.

## What this session cannot do, and why

A session reaches GitHub through an App installed on the repositories it was
granted. It can act inside those, and it holds nothing at the account level and
nothing over their settings. So creating a repository, starting a workflow on
some installations, and setting branch protection come back `403 Resource not
accessible by integration`, which names no permission and suggests no fix.
Read it as "this needs a person", not as a bug to route around, and do not fake
progress on a step you cannot perform: a step reported as done that was not is
worse than one reported as blocked, because what it breaks surfaces later
somewhere unrelated.

## 1. Make sure the repository exists and has a commit

Read the repository root with `mcp__github__get_file_contents`.

**Missing entirely.** Hand it over - creating a repository is an account-level
permission no installation carries, and trying first only produces a failure
that looks identical to a repository that exists but is out of reach. Give them
exactly this, and wait:

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
is outside whatever the session was granted when it started. If reads fail, say
so and ask them to give Claude access to it (the Claude GitHub App's repository
list, `github.com/settings/installations`) rather than reporting it missing.

Note the default branch name from `mcp__github__list_branches` and use it
everywhere below rather than assuming it is `main`.

## 2. Write the files

Where the files land depends on what is already in the repository. Decide that
before you write anything.

**A fresh repository** - nothing in it but the README from step 1, or nothing
at all. Push every file in a single commit straight to the default branch. No
branch, no pull request.

There is nothing to review against on an empty repository. The diff is the
whole tree, the alternative to merging it is a repository that does nothing,
and a pull request nobody can meaningfully reject costs a merge tap and a wait.
It also removes an ordering trap: `workflow_dispatch` only sees workflows that
are already on the default branch, so with a pull request in the way step 3
cannot start until a human comes back and merges. Pushed directly,
`bootstrap.yml` is runnable the moment this step finishes. Branch protection is
not set until step 4, so this is not routing around a gate - it is arriving
before there is one.

**A repository with anything else in it** - existing code, existing workflows,
a second provisioning attempt. One branch, one pull request: push the commit to
a branch named `provision/<version>`, then `mcp__github__create_pull_request`.
Not `claude/...`: these files are the gates themselves, and where a
`project-guard` caller is already in place it refuses them from an agent
branch whoever opened it. Here the diff is a real question.
These files land next to work somebody already did, and `ci.yml` in particular
may be about to replace a gate that is doing its job.

Check rather than assume: read the tree with `mcp__github__get_file_contents`.
Anything beyond a README, a LICENSE, or a `.gitignore` puts you on the pull
request path. If you cannot tell, take the pull request path - it is the one
that is wrong in the recoverable direction.

Either way it is one commit, and the rest of this step is what goes in it.

**Write that commit through a clone and `git`, whichever path you are on.**
`mcp__github__push_files` sends content and no file mode, so everything it
writes lands unexecutable - and four of the files below have to carry the bit.
Nothing reports that at the time, in the way nothing ever reports a missing
execute bit: the hook is wired and silent, the three scripts are present and
refuse, and the first thing to notice is `ci.yml`'s own placeholder gate, which
checks `test -x scripts/...` and so fails the first run on a repository that
was otherwise provisioned perfectly. Clone the target, write the files,
`chmod +x` the hook and the three scripts, commit, push. When this session is
on the repository being set up, its own working tree is that clone. The API
tools are still right for reading the tree and for everything in steps 3 and 4.

Everything you copy below comes out of the factory checkout from **Where the
factory comes from**: its `plugins/agent-factory/` directory is the factory
root, and every path below resolves against it.

Read each file out of `<factory root>/templates/project/` and send its contents
through, replacing both placeholders with the two values from the manifest:

- `__FACTORY_VERSION__` becomes `v` plus the version - for example `v1.2.0`.
- `__FACTORY_REPO__` becomes that `owner/repo`, verbatim.

A placeholder that survives into the repository fails as an invalid workflow
reference on the first run, which is loud and easy to fix.

The owner is read rather than typed because this command runs from forks too,
and a fork's projects have to call the fork. A hardcoded account here would
provision repositories that run somebody else's workflows: every check green, every run
succeeding, none of it the code anybody here can edit. That is silent rather
than loud, so it is the one worth being careful about.
`docs/decisions/0001-factory-repo-is-declared-in-the-manifest.md` in the factory
has the reasoning. If the manifest declares no repository, stop and ask - do not
guess an owner.

What goes in:

- `.github/workflows/ci.yml`, `guard.yml`, `bootstrap.yml` - thin callers,
  each pinned to that release, and the last two declaring the permissions their
  workflows ask for, so they start on a repository whose default token is
  read-only - which a new one is. `ci.yml` ships a placeholder gate
  rather than the four scripts, because a repository being provisioned usually
  has no stack yet, and the Node path fails a named script that is not there
  rather than skipping it - which would make this very pull request red. If the
  repository already has `typecheck`, `lint`, `test`, and `build`, switch to the
  Node path now; the comment at the top of the template says how. Otherwise
  leave it alone and say in the pull request body that the gate is a placeholder,
  what it does check, and that it fails the moment product code lands.

  **Do not ask what publishes this repository.** It used to be asked here, and
  the question is a good one - a gate runs the commands the project chose while
  production runs whatever the hosting platform chose, and nothing measures the
  distance between them unless somebody looks. A repository once had a gate that
  was green on every pull request for nineteen hours while the thing that
  publishes it failed on all eight merges.

  But it cannot be answered here. A repository being provisioned has no stack,
  so it has no deploy target either, and the answer at this moment is reliably
  "not sure yet" - which trains everyone to skip the question the next time it
  is asked, including the time it would have mattered. It now lives in the
  header comment of the `ci.yml` the project receives, addressed to whoever
  replaces the placeholder gate, which is both the first person who knows the
  answer and the one person who has to read that comment to do their job.

  If the repository being provisioned *does* already publish somewhere - it has
  a stack, so you are on the Node path anyway - then say in the pull request
  body whether the gate runs that build. There the question is answerable, so
  ask it.
- `.github/CODEOWNERS` - replace every `__PROJECT_OWNER__` with the handle that
  owns the repository. It is a placeholder for the same reason the pin is: a
  literal handle in the template is one a session can forget to change, and
  what lands then is a gate file naming an account with no relationship to the
  repository - which reviews nothing and looks exactly like a configured one
- `CLAUDE.md` - one line to fill in, and two sections to leave alone unless the
  repository answers them.

  The bracketed line under "What this is" is the one question worth asking a
  person: only they know it, it is one sentence, and every objective filed here
  afterwards is read against it. Ask it.

  The stack and the commands are **read, not asked**. A manifest, a lockfile,
  or code already in the tree answers them - and if you are reading those to
  choose the gate path above, you have the answer already. When nothing answers
  them, the template's "not chosen yet" text is the answer: leave it standing.
  Do not ask a greenfield repository for its stack. It does not have one, the
  reply is reliably "the first objective decides", and the question spends a
  turn of somebody's attention to learn nothing - while the flow this command
  sits in has already promised them that the manual steps come back as a
  checklist at the end rather than as blockers now.

  What must not survive is the bracket. A bracketed line left in a provisioned
  `CLAUDE.md` fails `project-guard`, deliberately: it reads as prose, it is the
  first thing every agent run loads, and unfilled it is an instruction
  addressed to a session that is no longer in the room.
- `docs/memory/orchestrator.md`, `researcher.md`, `analyst.md`,
  `designer.md`, `engineer.md` - empty, with their headers. Under `docs/` and
  not under `.claude/`: a run cannot write a file under `.claude/` at all, so
  memory kept there is a protocol nothing can follow. The memory-protocol skill
  carries the whole reason
- `.claude/agent-factory.json` - the record of which release this repository
  took, with the version filled in
- `docs/research/`, `docs/measurement/`, `docs/design/`, `docs/decisions/`
  with the ADR template
- `scripts/design-render`, `scripts/app-render`, `scripts/contrast` - from the
  template, and **executable**, for the same reason the hook is: without the bit
  they are present, silent, and refuse. These are the commands the roles are
  told the name of, and the contract each has to honour is in its own header:
  one renders a mock, one builds and serves this repository and photographs a
  route of it, one prints a contrast ratio. The defaults add no dependency -
  they use a headless browser and a static server the image is asked for rather
  than given - and `app-render` needs two lines filled in before it can build
  anything, because what builds this repository is not the plugin's to know. Say
  in the pull request body which of the three are working here and which are
  not, rather than leaving it to be discovered by the first run that needs one,
  and treat replacing any of them as this repository's decision to record.

Then the roles and the commands themselves, copied rather than referenced:

- `.claude/hooks/session-start.sh` - from the template, and **executable**;
  a hook without the execute bit is wired, silent, and looks like it ran
- `.claude/settings.json` - from the template, which wires that hook and
  carries nothing else. Permissions and env are the project's to add later
- `.claude/agents/*.md` - every file in `<factory root>/agents/`
- `.claude/skills/*/SKILL.md` - every skill in `<factory root>/skills/`
- `.claude/commands/objective.md`, `retro.md`, `decompose.md`, `update-agents.md`,
  `ship.md`, `check-in.md`, `self-driving.md`, `dispatch.md` - from
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

On the pull request path, say in the body that `bootstrap` has to be run once
this merges. On the direct push path there is no body to say it in, so it moves
to the report in step 5, and that report is then the only place it is said - so
do not let it fall out.

## 3. Labels

The labels are created by the `bootstrap` workflow rather than from here, and
the roles and `/dispatch` match their names exactly, so they are worth getting
from one place rather than retyping.

`workflow_dispatch` only sees workflows already on the default branch. On the
direct push path they are there now; on the pull request path the person merges
step 2 first.

**Try to start it, and expect to hand it over.**
`mcp__github__actions_run_trigger` on `bootstrap.yml` against the default
branch. Where the session's installation lacks `actions: write` - usually - it
comes back `403`. Do not retry it and do not report it as a fault in the
repository; it is a permission of the App the session runs as, not a setting
anybody can switch on for you. Hand it over:

> 1. Open `github.com/$1/actions/workflows/bootstrap.yml`
> 2. Tap **Run workflow**, then **Run workflow** again to confirm

**Read its summary yourself, whoever started it.** Starting a run and reading
one are different permissions, and only the first is refused. Once it exists,
`mcp__github__actions_list` finds it, `mcp__github__actions_get` waits for it,
and `mcp__github__get_job_logs` reads its summary, which carries the check names
as they actually reported. Step 4 needs those, and asking a person to open the
run and transcribe them on a phone is how a typo gets into a protection rule.

**The check.** Sample rather than trust the summary: `mcp__github__get_label`
for `agent:queued` and `role:engineer`. If either is missing, the run did not do
what it said.

## 4. Branch protection

Recommended, and the person's: setting it needs an administration token, and an
identity that can set a gate can remove one. It is what makes "merge when green"
mean something, and it costs a minute.

Only after both gates have reported at least once - a required check that has
never run blocks every merge, including the pull request that would fix it.
Give them the names you read in step 3, verbatim. On a freshly set-up
repository they are `ci / checks` and `guard / memory cap and protected paths`,
but quote what actually reported.

> 1. Open `github.com/$1/settings/branches`
> 2. **Add branch protection rule** (or **Add classic branch protection rule**)
> 3. Branch name pattern: the default branch name
> 4. Tick **Require status checks to pass before merging**
> 5. Tick **Require branches to be up to date before merging**
> 6. Search for each check name and select it
> 7. Leave **Require a pull request before merging** unticked, so you can still
>    commit directly when you need to
> 8. **Create**

Set once. The gate's job name stays `checks` whether it runs the placeholder
commands or the project's real ones, so the rule is never re-pointed.

**The check.** Reading a rule needs the same administration permission as
setting it, so this session cannot tell "no rule" from "cannot see the rule".
Do not report it as verified. The first pull request's merge box shows its
required checks, which confirms it.

## 5. Report

Three parts.

First, plainly: what was created, whether it went to the default branch or a
pull request, what already existed, and anything that failed - with the exact
call that failed.

Then **what you verified, separated from what you were told**:

> Confirmed: the files on `<branch>`, the labels, the bootstrap run and its
> check names.
>
> Taken on your word, because I cannot read it: branch protection. The first
> pull request's merge box confirms it.

Then whatever is still waiting on the person, in order, each as the URL that
does it, leaving out anything already done. If the gate went in as a
placeholder, say so and what replaces it - it is the one outstanding item that
looks like nothing is wrong, because every check is green and none of them is
testing the product.

Then what happens next, because otherwise the report is a list of chores with
no end. In a Claude Code session on `$1`:

- `/objective <the idea>`, or a message starting `obj`, starts the first piece
  of work. The session refines it with them, files it, and drives it -
  starting each role itself, as `/dispatch` describes.
- `/check-in` catches up after time away and starts whatever is queued.
- Asking it, in plain words, to keep the work going while they are away -
  overnight, or for days - starts a self-driving stretch, which schedules
  sessions of its own until it ends. Without one, agents run only while a
  session on `$1` is open.

## Optional: the provisioning run

A factory owner who sets up many repositories can hand steps 3 and 4 to one
approved run of the factory's `provision.yml`: it starts `bootstrap`, waits for
both gates to report, sets branch protection from the names they reported, and
comments the result. It holds a fine-grained token with admin over the owner's
repositories, released only when they approve the run - ADR 0003 has the trade,
and the factory's `docs/checkpoint.md` has the setup.

It only applies where `$1` belongs to the same account as the factory, and only
where the factory carries a `provision` label (`mcp__github__get_label`).
Otherwise skip this section entirely. Where it applies, file it right after
step 1, before writing anything: `mcp__github__issue_write` on the factory,
creating an issue titled `provision $1` with the label `provision`. Tell the
person GitHub will ask them to approve a deployment, and that the tap is the
whole of what is left to them. The run waits for step 2's files itself.

Read the result back from the issue's comments: the one carrying
`<!-- agent-factory:provision-report -->`. Each ticked line was read back from
the repository, so it goes in step 5's confirmed line - branch protection
included - and each unticked line goes in the remaining list as written. If
there is no comment yet, say which wait it is in: an approval nobody has tapped
looks exactly like a run that has not started. Re-running is safe: every step
re-sets or skips what is already done.
