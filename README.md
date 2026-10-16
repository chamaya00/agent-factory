# agent-factory

Sets a GitHub repository up so a team of AI agents can turn objectives into
merged, tested code. You describe what you want in a Claude Code session - from
a phone if you like - and the session runs an orchestrator and four specialist
roles, reviews what they deliver against the repository's own checks, and
merges what passes or brings it to you.

No API key, token, secret, or GitHub App of your own: a session works as you.

## Get started

You need a Claude plan with Claude Code and GitHub connected to Claude. Then,
for a public repository with at least one commit, start a Claude Code session
on it and send:

> Set this repository up with the agent factory: clone
> https://github.com/chamaya00/agent-factory at its latest release and follow
> plugins/agent-factory/commands/new-project.md from that clone, for this
> repository.

It writes everything itself and hands back two small steps - one tap to run
`bootstrap`, and one settings page for branch protection. Then type
`obj <what you want>` to start the first piece of work.

[`docs/getting-started.md`](docs/getting-started.md) has the whole of it,
including setting up from a fork of this repository and moving a project off an
older release.

## How it is built

Three separable layers, and the separation is the point:

| Layer | Lives in | How it travels |
|---|---|---|
| Agent roles and process | the `agent-factory` plugin | copied into each repo's `.claude/`, loads from the clone |
| Automation | this repo's reusable workflows | each project calls them in one line |
| Project-specific learning | each project's own repo, under `docs/memory/` | never leaves that repo |

The third row is what keeps the first two reusable. Agents get smarter inside a project without contaminating any other project.

## Layout

```
.claude-plugin/marketplace.json      marketplace manifest
plugins/agent-factory/
  .claude-plugin/plugin.json         plugin manifest (explicit name, always)
  agents/                            the roles
  skills/                            the process instructions
  commands/                          slash commands
  templates/project/                 what /new-project drops into a fresh repo
.claude/                             a copy of the three directories above, which
                                     is what a session on this repo actually loads
.github/workflows/                   reusable workflows plus the factory's own guard
scripts/                             the guard's checks
docs/                                the operating documentation, also a Pages site
```

Everything except the two manifests sits at the plugin root, not inside `.claude-plugin/`.

## The roles

- `orchestrator` - reads an objective, splits it into 1-5 child issues sized to the work, with acceptance criteria. One child is right when the work is genuinely one role's, and it says which roles it skipped and why. No file writes, no grandchildren.
- `researcher` - investigates options and constraints, writes to `docs/research/`. No writes to source code.
- `analyst` - specifies the event contract, the exposure event, and the metrics a result is read with, writes to `docs/measurement/`. No writes to source code.
- `designer` - produces flows, states, and component specs, plus a rendered mock when the issue is visual, writes to `docs/design/`. No writes to source code.
- `engineer` - implements against the acceptance criteria, writes the tests, opens the pull request.

## Commands

Roughly in the order a project meets them, so `/objective` - where every piece of work starts, and what `/new-project`'s closing report tells the person to type next - comes straight after provisioning. `/new-project` is the one that stays in the factory; the rest are copied into every project it provisions, and that is where they run.

- `/new-project <owner/repo>` - sets a repository up: caller workflows, `CLAUDE.md`, memory files, its own copy of the roles, skills, and commands, and the labels. Runs from a session on the factory, or from a session on the repository itself with the factory cloned. The two steps a session cannot perform - running `bootstrap` and branch protection - are handed to the person with links, never faked.
- `/objective <rough idea>` - the one command that starts a piece of work. Refines the idea with the person, drafts the objective, asks its merge policy once, files and queues it on a yes, and then drives it.
- `/check-in [objective]` - runs the driving posture now, the same way whether a person typed it, a scheduled wake fired it, or a pull request's activity woke the session: what is waiting on the person first, then the state of every child, then the merge policy applied to whatever is waiting. With no objective named, takes every open one.
- `/ship [objective]` - the explicit form of "merge when green". Judges each pull request the objective is waiting on against the house rules' merge gate, merges what passes where the merge policy is `green` and reports it where it is not, and says on the pull request why for any that fail.
- `/self-driving [objectives] [until ...]` - starts a long autonomous run, day or night: one round of questions, then the session drives the named objectives to done on delegated judgment, logging every call it makes on the person's behalf, until they close, the stated end arrives, or the person says stop. Asking for the same thing in plain words starts it too, and a stretch meant to outlast the session schedules fresh sessions to carry it on.
- `/dispatch <issue>` - how every agent run starts: checks the issue may run, books the run on it against the attempt budget, runs the role with a fixed brief, and hands the result back. In this session as a subagent by default; in a child session when the driver judges a run worth one. `/check-in` calls it for whatever is queued.
- `/decompose <issue>` - runs the orchestrator on one issue by hand.
- `/retro` - proposes memory updates for the current repo as a pull request.
- `/update-agents [version]` - brings one repo's copy of the roles, skills, and workflow pins up to a release, as one reviewable pull request. Nothing else moves.

## Workflows

All the logic lives here; projects get thin callers pinned to a release tag,
for example `@v1.1.0`.

The pin is the contract. A merge here reaches no project on its own, ever. A
project moves when somebody runs `/update-agents` there and merges the pull
request it opens, which bumps the pins and refreshes the vendored roles
together. Repositories you never run it in stay where they are indefinitely.

Release tags are immutable - `release.yml` refuses one that already exists.
`docs/versioning.md` is the full model.

| Workflow | Called as | What it does |
|---|---|---|
| `ci.yml` | `workflow_call` | the gate. No model involved. Runs `package.json` scripts by default, or the caller's own shell commands when it passes `commands`, which is how a non-Node project gets a gate. |
| `project-guard.yml` | `workflow_call` | in each project: memory files stay inside the 40-line cap, and nobody but a maintainer edits the files that gate the repo - with a pull request from an agent branch (`claude/*`) checked whoever opened it, because a session-run role opens its pull requests as the person. |
| `bootstrap.yml` | `workflow_call` | run once per project, by hand: creates the labels the loop runs on, and reports the check names branch protection needs. |
| `provision.yml` | this repo only, optional | for an owner setting up many repositories: one approved run starts `bootstrap` and sets branch protection. See `docs/checkpoint.md`. |
| `guard.yml` | this repo only | the checks below. |
| `release.yml` | this repo only, by hand | cuts an immutable release tag on the tip of `main`, named by the plugin manifest, once the checks pass on it. |

## A project that is not Node

`ci.yml` runs `package.json` scripts by default. A project on any other stack
passes `commands` instead, and the whole Node path - lockfile detection,
install, script check - is skipped:

```yaml
jobs:
  ci:
    uses: chamaya00/agent-factory/.github/workflows/ci.yml@v1.1.0
    with:
      check-name: 'typecheck, lint, test'
      commands: |
        uv sync --frozen
        uv run mypy .
        uv run ruff check .
        uv run pytest
```

Every line runs in order, under `bash -euo pipefail`, and the first non-zero
exit fails the run there rather than continuing to report the rest. Blank lines
and `#` comments are ignored; a value with no runnable line in it fails, since
a gate that runs nothing is not a gate.

`check-name` is the string branch protection matches on, so it defaults to the
Node job's name and existing rules keep working untouched. Changing it means
re-pointing the protection rule in the same sitting - a required check that no
longer reports blocks every merge, including the one that would fix it.

## Guard

`guard.yml` runs on this repo on every push and pull request. It checks that the manifests parse, that each role carries the memory and containment clause verbatim, that no plugin file names a stack, a vendor, or a product, and that the shell the factory ships does what it claims. `docs/what-is-checked.md` has what each script asserts.

Every Python file in `scripts/` is one of those checks - `validate_plugin.py`
fails the build if one is not run by `guard.yml` - and none of them reads
another's output, so the order they run in does not matter. Run them all
locally with:

```
python3 -m pip install --quiet pyyaml
for check in scripts/*.py; do python3 "$check" || echo "FAILED: $check"; done
```

A list of the scripts used to stand here instead, and it named five while the
gate ran eight. A glob cannot fall behind.

Most of the `test_` scripts execute a workflow's own shell rather than reading
it: each lifts a `run:` block straight out of the YAML and runs it, so a test
cannot drift from what ships. That is spent where a bug is expensive and quiet.
`ci` decides what may merge in every project; `project-guard` decides whether
a widened permission or a gate edit can arrive without the pull request saying
so; `provision` holds an admin token; and `release` decides what a project can
pin to. `ci`
is the worst of them to get wrong - a gate that fails a good pull request is
noticed within the minute, and one that passes a bad one is not noticed at all.

## Releasing

A release starts with a merged pull request bumping `version` in
`plugins/agent-factory/.claude-plugin/plugin.json`. Then `release.yml`, from
the Actions tab, input left empty.

The tag name is read from that manifest rather than typed. An installed plugin
decides whether to update by comparing versions, so a tag that got ahead of the
manifest would ship new files and then be declined as already up to date; tying
the two together makes that unrepresentable.

It refuses a tag that already exists, a name that is not `vMAJOR.MINOR.PATCH`,
one that disagrees with the manifest, and any commit the guard checks do not
pass on. The run summary says plainly that no project picked anything up, and
lists the workflows callable at the tag.

Nothing rolls back, because nothing rolled forward. A project on a bad release
stays on it until somebody moves it, and a project on a good one is unaffected
by the bad one existing.

Moving the tag is a human step, and it stays one. A session can neither start
the workflow nor push the tag by hand: dispatching needs `actions: write`,
which no workflow here grants and which is exactly the permission an agent
would need to run its own gates, and the App token is not allowed to write
refs under `refs/tags/`. Both come back `403`. So this is three taps in the
Actions tab, by you, after any merge that projects should pick up - and a
session that says it moved the tag did not.

## What a session cannot do for you

A session reaches GitHub through the Claude GitHub App installed on the
repositories it was granted. It can act inside those, and it holds nothing at
the account level and nothing over their settings, so three things in setting
up a repository are the person's, and `/new-project` hands each back with a
link rather than pretending:

- **Creating the repository.** Public, with a README, from `github.com/new`.
- **Running `bootstrap` once,** which creates the labels. Starting a workflow
  usually needs a permission the session's installation lacks; reading the run
  does not, so the session still reads the check names out of it itself.
- **Branch protection.** Setting it needs an administration token, and an
  identity that can set a gate can remove one.

An owner who sets up many repositories can hand the last two to one approved
run of `provision.yml` - `docs/checkpoint.md` has the setup, and ADR 0003 the
trade. Both refusals read `403 Resource not accessible by integration`, which
names no permission and suggests no fix, which is why this list exists.

## How the commands get loaded

Nothing to type, and nothing to install. This repository carries its own copy of the commands, roles, and skills under `.claude/`, and a session loads them straight out of the clone. `/new-project` copies the same files into each project repository, and `/update-agents` refreshes them from a named release alongside the workflow pins.

Copying is not decoration, and it is not the first thing that was tried. `/plugin install` writes to the machine that ran it, and the machine that runs these sessions is a container that did not exist an hour ago and will not exist tomorrow. Declaring the marketplace in `.claude/settings.json` was the next attempt and it fails more quietly: Claude Code ignores a marketplace declared by a repository until the folder is trusted for project plugins, and a web session has nobody to answer the trust prompt, so it never is. Files in the clone are the only form of this that a phone can actually use.

The cost of copying is drift, so `scripts/validate_plugin.py` fails the build if `.claude/` and `plugins/agent-factory/` disagree by a byte.

## Standing up a project

1. [`docs/getting-started.md`](docs/getting-started.md) - setting a repository up and using it. The whole of it, for anybody.
2. `docs/checkpoint.md` - what only the factory's owner does: cutting a release after a version bump, cleaning up what older releases needed, and two optional conveniences.
3. `docs/proving-the-gate.md` - prove a red check blocks a merge, by hand, on a throwaway repo, before trusting agents with it.
4. `docs/smoke-test.md` - two objectives through the whole loop, building a site the repository publishes so the result is judged by opening a URL rather than by reading a diff.

`docs/what-is-checked.md` is the answer to "how do we know any of this works": every script `guard.yml` runs and what each one asserts, the gates a project receives, what `/dispatch` refuses, and the parts nothing verifies yet.

`docs/open-questions.md` is the register of assumptions this system runs on that have not been tested yet, each with how to settle it and what changes once you do.

## The documentation site

`docs/` is a GitHub Pages site as well as a folder, served from `main` at the `/docs` source with `docs/_config.yml` and `docs/index.md` as its entry point. Nothing built it: the source is a repository setting under Settings, Pages, and there is no deploy workflow on purpose. Building from a branch needs nothing added to `.github/workflows/`, and a system whose agents must never touch those files should not grow a workflow it does not need.

Every page renders as plain Markdown with no front matter, and links between `.md` files work in both places, so a document is edited once and reads correctly on github.com and on the site.

That build is the one thing here the gate does not run, so `docs/` is held to one rule the rest of the repository is not: no Liquid syntax, because Jekyll renders it before Markdown and backticks do not protect it. `validate_plugin.py` refuses it, and ADR 0002 records what that covers of the gap and what it leaves to somebody opening the page.
