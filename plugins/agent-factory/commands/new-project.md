---
description: Provision a fresh repository end to end - caller workflows, project files, labels, and the two settings only a human can change.
argument-hint: <owner/repo>
allowed-tools: Bash, Read, Write, Edit, Glob, mcp__github__get_file_contents, mcp__github__create_repository, mcp__github__create_branch, mcp__github__push_files, mcp__github__create_pull_request, mcp__github__get_label, mcp__github__list_branches, mcp__github__actions_run_trigger, mcp__github__actions_list, mcp__github__actions_get, mcp__github__get_job_logs
---

Provision `$1` so agents can work in it.

If `$1` is empty, ask which repository before doing anything.

## Verify, do not take "done" for an answer

Most of what goes wrong here is a step somebody believes is finished. So every
handoff below gives the link, says what to do on that page, and names a check
to run afterwards. Run it. A person's "done" and the repository's actual state
disagree often enough to be worth one call, and when they disagree, say so and
hand the link back rather than letting it surface three steps later somewhere
unrelated.

Two settings cannot be read from here at all. Those are marked, and they are
reported as taken on trust rather than confirmed.

## Handing over: the list first, then the offer

Reach this point once step 3 has pushed the files. Before offering anything,
**write out every remaining step, in the order the dependencies force, each
with its URL and what to click on that page.**

This page used to lead with the script instead, and that was wrong twice over.
A person cannot weigh an offer of help against an alternative nobody has shown
them, so leading with it reads as "the rest is too tedious to describe" - and
it is not even true, because the script does not cover all of it.

**Rank the list rather than merely enumerating it.** A wall of settings steps
is where attention dies, and the `briefing` skill states the failure exactly:
the reader acts on the first three and the fourth was the one that mattered.
Say which step gates the others, and say which can wait - an agent identity App
that does not exist yet costs an approval tap per pull request and nothing else,
which is a thing somebody may reasonably choose to live with for a week.

**Keep the dependency order, and say that it is one.** Branch protection is
last because it needs check names that do not exist until `ci` and `guard` have
each reported once, and a rule requiring a check that never reports blocks every
merge including the one that would remove the rule. Bootstrap comes before it
for the same reason. A flat checklist invites working through it in the order it
happens to be written.

Then make two offers, separately, and let them take either, both, or neither:

- **Going deeper on any one step.** Some are a single tick and some are not, and
  nobody can tell which from a URL.
- **The script, for the specific steps it covers.** Name them:
  `scripts/setup-project.sh` does the Actions permission, the
  `CLAUDE_CODE_OAUTH_TOKEN` secret, the labels by running bootstrap, and branch
  protection - reading each one back after setting it. It does not do the agent
  identity App, because creating a GitHub App has no API, so the id, the private
  key and the installation stay with the person whatever they choose here.

**Offer it per step, never as all or nothing.** Presented whole it reads as
though taking it finishes the job, and a person who runs it and stops has a
repository where every agent pull request needs an approval tap and nothing
tells them why.

Running it is a Codespace on this factory and one paste. Substitute this
factory's own `owner/repo` into the URL, read from `git config --get
remote.origin.url` in the checkout you are running in rather than assumed - a
fork that sends people to the upstream Codespace has them run somebody else's
scripts against their repository:

> 1. Open `github.com/codespaces/new?repo=<this factory's owner/repo>`
> 2. In its terminal: `bash scripts/setup-project.sh $1`

**Default to the manual path, and price both rather than recommending one.**
Manual is the more transparent: the person watches each setting land, which is
worth something on the steps that decide what automation may do in their
repository. What it costs is verification. The Actions permission and branch
protection sit behind the same administration permission that stops this session
writing them, so it cannot read them back either - done by hand they stay taken
on trust in the report at step 6 and nothing ever checks them, and done by the
script they are confirmed. Seeing it happen and having it proved are different
goods, and which one matters more is the person's call, not this page's.

Any of it is available at all because the reason these steps are handed over is
narrower than it looks: they are not inherently manual, only unavailable to
*this* session. A session token is a GitHub App installation holding nothing at
the account level, so changing a repository setting is `403 Resource not
accessible by integration` however it is asked for. `gh` in a Codespace is the
person.

One symptom worth recognising while the Actions permission is still unset: a
`guard` run that comes back `startup_failure` on the provisioning push, with no
jobs and no log. The likeliest cause is that same setting - `project-guard.yml`
declares `pull-requests: read` and a restricted default token cannot grant it,
so the run refuses to start rather than failing inside a job. That has not been
confirmed from a log, because a startup failure produces none, so treat it as
the first thing to check rather than as settled. `ci` is unaffected, which is
why the two can disagree on an otherwise correct repository.

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

Give them exactly this:

> 1. Open `github.com/$1/settings/actions`
> 2. Scroll to **Workflow permissions**
> 3. Select **Read and write permissions**
> 4. Tick **Allow GitHub Actions to create and approve pull requests**
> 5. **Save**

**The check.** There is none from here: the setting sits behind the same
administration permission that stops you writing it, so `403` is the answer
either way. Say that rather than implying you confirmed it, and record it in
the report as taken on trust. The fast-path script does read it back. Failing
that it surfaces on the first agent run, as a green run that opens no pull
request - so if that ever happens, come back here before debugging anything
else.

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

**Write that commit through a clone and `git`, whichever path you are on.**
`mcp__github__push_files` sends content and no file mode, so everything it
writes lands unexecutable - and four of the files below have to carry the bit.
Nothing reports that at the time, in the way nothing ever reports a missing
execute bit: the hook is wired and silent, the three scripts are present and
refuse, and the first thing to notice is `ci.yml`'s own placeholder gate, which
checks `test -x scripts/...` and so fails the first run on a repository that
was otherwise provisioned perfectly. Clone the target, write the files,
`chmod +x` the hook and the three scripts, commit, push. The API tools are
still right for reading the tree and for everything in steps 4 and 5.

Everything you copy below comes out of the factory itself.
`${CLAUDE_PLUGIN_ROOT}` is set only when the factory is installed as a plugin,
which does not happen in a cloud session, so use it if it is set and otherwise
use `plugins/agent-factory/` in the checkout you are running in. Call that
directory the factory root and resolve every path below against it. If neither
exists you are not in the factory - stop and say so.

Read `<factory root>/.claude-plugin/plugin.json` first. Two values come out of
it and both go in several places below, so read it once and use the same
answers everywhere.

- `version` is the release this repository gets pinned to.
- `repository` is which factory this is. Take the `owner/repo` out of the URL -
  `https://github.com/example/agent-factory` gives `example/agent-factory`.

Read each file out of `<factory root>/templates/project/` and send its contents
through, replacing both placeholders:

- `__FACTORY_VERSION__` becomes `v` plus the version - for example `v1.2.0`.
- `__FACTORY_REPO__` becomes that `owner/repo`, verbatim.

A placeholder that survives into the repository fails as an invalid workflow
reference on the first run, which is loud and easy to fix.

The owner is read rather than typed because this command runs in forks too, and
a fork's projects have to call the fork. A hardcoded account here would provision
repositories that run somebody else's workflows: every check green, every run
succeeding, none of it the code anybody here can edit. That is silent rather
than loud, so it is the one worth being careful about.
`docs/decisions/0001-factory-repo-is-declared-in-the-manifest.md` in the factory
has the reasoning. If the manifest declares no repository, stop and ask - do not
guess an owner.

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
  `ship.md`, `check-in.md` - from
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
the pull request path the human merges step 3 first.

**Starting it is usually a handoff, and this page used to say otherwise.** It
claimed a dispatch was an ordinary repository action inside what a session
token can do, and treated the handoff as the exception. On a real provisioning
run it came back:

```
POST /repos/<owner>/<repo>/actions/workflows/bootstrap.yml/dispatches
403 Resource not accessible by integration
```

on a public repository, freshly provisioned, with all four callers already on
the default branch - neither of the two conditions the page called exceptional.
That error is the App installation lacking `actions: write`. It is **not** the
Workflow permissions setting from step 1: that governs what `GITHUB_TOKEN` may
do *inside* a run, not what an external App may do to the repository. Granting
one does nothing for the other, so do not send anybody to that settings page
over this.

Nothing you can do from here changes it, and it is not something the person
can switch on for you either - the permission belongs to the App the session
runs as, not to the repository. So try the dispatch, because it costs one call
and succeeds where an installation does have the permission, and expect to hand
it over:

`mcp__github__actions_run_trigger` on `bootstrap.yml` against the default
branch. If it returns 403, do not retry it and do not report it as a failure of
the repository - go straight to the handoff below and say which of the two it
was.

> 1. Open `github.com/$1/actions/workflows/bootstrap.yml`
> 2. Tap **Run workflow**, then **Run workflow** again to confirm

The script does not have this problem. It runs `gh` as the person, so
`gh workflow run bootstrap.yml` works there - which is worth saying when this
step is the one they are deciding about, per "Handing over: the list first,
then the offer" above.

**Read its summary yourself, whoever started it.** This is the part that must
not go with the dispatch, and on the run above it did: the handoff went out
with nothing concrete in it, and step 5 went with it.

Starting a run and reading one are different permissions, and only the first is
refused. Once the run exists - however it was started - `mcp__github__actions_list`
finds it, `mcp__github__actions_get` waits for it, and `mcp__github__get_job_logs`
reads its summary. That summary carries the check names as they actually
reported, which step 5 needs. Asking a person to open the run and read them
back to you turns a call you can make into a page they have to find, on a
phone, and transcribe without a typo - and a guessed check name is worse than
no branch protection rule at all.

So the handoff is four taps and a "tell me when it is done", not a research
task. Wait, then read.

**The check.** Verify a sample rather than trusting the run:
`mcp__github__get_label` for `agent:queued` and `role:engineer`. If either is
missing the run did not do what it said, whatever its summary claims.

## 5. Branch protection

Also a human step, and deliberately so. Setting it needs an administration
token, and an identity that can set a gate can remove one - which is the thing
this whole arrangement is built to prevent. It is worth the minute it costs.

Only after the checks have run at least once and reported their names. A
required check that has never run blocks every merge, including the pull
request that would fix it.

Give them the names you read in step 4, verbatim, spelled out in the handoff
rather than described - "the names from the summary" is a page they have to go
back and find. They will be `ci / checks` and
`guard / memory cap and protected paths` on a freshly provisioned repository,
but quote what actually reported rather than these, because a project that
changed `check-name` reports something else.

Set once, and that is the whole point of the name. The gate's job name stays
`checks` whether it is running the placeholder commands or the project's real
ones, so this rule is never re-pointed: swapping the gate later changes what
runs, not what protection matches on. A required check that stops reporting
blocks every merge instead of gating them, including the pull request that
would put it back, and keeping one stable name is what makes that impossible
rather than merely documented.

> 1. Open `github.com/$1/settings/branches`
> 2. **Add branch protection rule** (or **Add classic branch protection rule**)
> 3. Branch name pattern: the default branch name
> 4. Tick **Require status checks to pass before merging**
> 5. Tick **Require branches to be up to date before merging**
> 6. Search for each check name and select it
> 7. Leave **Require a pull request before merging** unticked, so you can still
>    commit directly when you need to
> 8. **Create**

**The check.** Reading a protection rule needs the same administration
permission that setting it does, so this session gets `403` or `404` either
way and cannot tell "no rule" from "cannot see the rule". Do not report it as
verified. What does verify it, in order of what is available: the fast-path
script reads the rule back and prints the contexts it now requires, and failing
that, the next pull request shows its required checks in the merge box - so the
first agent pull request confirms it in passing.

## 6. Report

Three parts, and the last two are the deliverable.

First, plainly: what was created, whether it went to the default branch or to a
pull request, what already existed, and anything that failed - with the exact
call that failed.

Then **what you verified, separated from what you were told**. A report listing
eight finished steps, three of them finished only because somebody said so, is
how a repository reaches its first agent run with the Actions permission still
off. Two lines:

> Confirmed: the files on `<branch>`, the labels, the bootstrap run and its
> check names.
>
> Taken on your word, because I cannot read them: the Actions permission and
> branch protection. The first agent pull request confirms both - it appears
> at all only if the permission is on, and its merge box lists the required
> checks.

If the fast-path script ran, move what it read back into the first line.

Then everything still waiting on the human, in the order it has to happen, each
one as the URL that does it. Substitute `$1` and the default branch name. A
reader assembling a settings URL by hand is a reader who ends up on the wrong
page, and this is the whole reason the list is here rather than in prose:

Leave out anything you already did or already confirmed. A checklist that
re-lists finished work is one nobody reads to the bottom, and the bottom is
where the item that actually blocks them usually is.

> 1. **Add the secrets** - `github.com/$1/settings/secrets/actions/new`
>    `CLAUDE_CODE_OAUTH_TOKEN`, and `AGENT_APP_ID` with
>    `AGENT_APP_PRIVATE_KEY` if the agent identity App exists.
> 2. **Install the App here** - `github.com/settings/installations`
>    Nothing to do if there is no App. Without it every agent pull request
>    lands needing an approval tap before its checks will run, and an
>    orchestrator cannot queue its own children at all.
> 3. **Branch protection** - `github.com/$1/settings/branches`
>    Requiring the check names quoted in step 5, not guessed ones.

Say why the ones that are blocked are blocked, rather than leaving them looking
like things you forgot: the secrets because secrets are per repository and
nothing agent-side runs without them, the protection rule because setting it
needs an administration token and an identity that can set a gate can remove
one.

If the gate went in as a placeholder, say so here too, and say what replaces it.
It is the one outstanding item that looks like nothing is wrong: every check is
green, and none of them is testing the product. Say also what replacing it does
*not* require - the protection rule stays as it is, because the gate's job name
does not change when its commands do.

Then say what happens next, because the report is otherwise a list of chores
with no end: once the secrets are in, `/objective` in a session on that
repository is how the first piece of work starts.
