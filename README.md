# agent-factory

A reusable toolbox that turns high-level objectives into working code across projects.

Three separable layers, and the separation is the point:

| Layer | Lives in | How it travels |
|---|---|---|
| Agent roles and process | the `agent-factory` plugin | enabled once on the Claude account, loads in every session |
| Automation | this repo's reusable workflows | each project calls them in one line |
| Project-specific learning | each project's own repo, under `.claude/memory/` | never leaves that repo |

The third row is what keeps the first two reusable. Agents get smarter inside a project without contaminating any other project.

## Layout

```
.claude-plugin/marketplace.json      marketplace manifest
plugins/agent-factory/
  .claude-plugin/plugin.json         plugin manifest (explicit name, always)
  agents/                            the four roles
  skills/                            the process instructions
  commands/                          slash commands
  templates/project/                 what /new-project drops into a fresh repo
.github/workflows/                   reusable workflows plus the factory's own guard
scripts/                             the guard's checks
```

Everything except the two manifests sits at the plugin root, not inside `.claude-plugin/`.

## The four roles

- `orchestrator` - reads an objective, produces 2-5 child issues with acceptance criteria. No file writes, no grandchildren.
- `researcher` - investigates options and constraints, writes to `docs/research/`. No source access.
- `designer` - produces flows, states, and component specs, writes to `docs/design/`. No source access.
- `engineer` - implements against the acceptance criteria, writes the tests, opens the pull request.

## Commands

- `/new-project <owner/repo>` - provisions a fresh repo: caller workflows, `CLAUDE.md`, memory files, and the labels. Three of its steps are handed to a human rather than scripted - see below.
- `/decompose <issue>` - runs the orchestrator on one issue by hand.
- `/retro` - proposes memory updates for the current repo as a pull request.

## Workflows

All the logic lives here; projects get thin callers that point at `@v1`.

`v1` is a tag on `main`, and it is load-bearing. A caller holds an address, not
a copy: GitHub resolves `@v1` fresh on every run, so moving the tag changes what
every project executes immediately, with no pull request in any of them. That is
what makes one edit here reach every project at once, and it is the same reason
a stale tag is invisible - a project fails with an invalid workflow reference,
naming nothing about a tag in another repo.

Move it with the `release` workflow rather than by hand, and cut `v2` instead
when a change should not reach existing projects on its own.

| Workflow | Called as | What it does |
|---|---|---|
| `ci.yml` | `workflow_call` | typecheck, lint, test, build. No model involved. This is the gate. |
| `agent-run.yml` | `workflow_call` | one agent run: repo-wide concurrency, queued not cancelled, capped turns and minutes, refuses a fourth attempt on the same issue. |
| `project-guard.yml` | `workflow_call` | in each project: memory files stay inside the 40-line cap, and nobody but a maintainer edits the files that gate the repo. |
| `bootstrap.yml` | `workflow_call` | run once per project, by hand: creates the nine labels and reports the check names branch protection needs. |
| `guard.yml` | this repo only | the checks below. |
| `release.yml` | this repo only, by hand | moves a major tag to a merged commit, once the checks pass on it. |

## Guard

`guard.yml` runs on this repo on every push and pull request. It checks that the manifests parse, that each role carries the memory and containment clause verbatim, and that no plugin file names a stack, a vendor, or a product. Run it locally with:

```
python3 scripts/validate_plugin.py
python3 scripts/validate_workflows.py
python3 scripts/test_preflight.py
python3 scripts/test_release.py
```

The last two execute a workflow's own shell rather than reading it, because
those are the two places a bug is expensive: the preflight spends subscription
quota, and `release` decides what every project runs.

## Releasing

`release.yml` is `workflow_dispatch` only, from the Actions tab. Leave the
inputs alone to move `v1` to the tip of `main`; pass an older merged commit to
roll back, or a different `v<n>` to cut a new major.

It refuses a tag name that is not `v<number>`, a commit that is not already on
the default branch, and any commit the guard checks do not pass on. The run
summary lists what every project just picked up and which workflows are callable
at the tag, which is the thing worth reading after a move.

## What a session cannot do for you

A cloud session reaches this account's repositories through tools, not a shell,
and there is no tool for a repository setting. Three things in provisioning are
therefore always handed back, and `/new-project` asks for each in place rather
than pretending:

- **Allow Actions to create and approve pull requests.** Off by default on
  personal accounts. With it off, every agent run appears to work and no pull
  request ever appears.
- **Merging the provisioning pull request, then running `bootstrap`.**
  `workflow_dispatch` only sees workflows already on the default branch, so the
  labels cannot be created before that merge.
- **Branch protection.** Not automated on purpose, not only for lack of a tool:
  setting it needs an administration token, and an identity that can set a gate
  can remove one.

## Install

```
/plugin marketplace add chamaya00/agent-factory
/plugin install agent-factory@agent-factory
```

Both lines are needed. Adding the marketplace without installing the plugin is the usual reason the commands do not appear.

## Standing up a project

In order, and the order is the point:

1. `docs/checkpoint.md` - the things only a human can do: the subscription token, the secrets, the agent identity App, the plugin install, the preview provider. Written for an iPhone, since that is the only device involved.
2. `docs/proving-the-gate.md` - prove a red check blocks a merge, by hand, on a throwaway repo, before any agent is pointed at it. An agent aimed at a gate you do not trust produces work you have to read line by line, which is the thing the system exists to avoid.
3. `docs/smoke-test.md` - one objective through the whole loop, with what to watch for at each of the six steps and the five failure modes worth recognising on sight.
