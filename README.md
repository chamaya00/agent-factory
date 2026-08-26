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
.github/workflows/                   reusable workflows plus the factory's own guard
scripts/                             the guard's checks
```

Everything except the two manifests sits at the plugin root, not inside `.claude-plugin/`.

## The four roles

- `orchestrator` - reads an objective, produces 2-5 child issues with acceptance criteria. No file writes, no grandchildren.
- `researcher` - investigates options and constraints, writes to `docs/research/`. No source access.
- `designer` - produces flows, states, and component specs, writes to `docs/design/`. No source access.
- `engineer` - implements against the acceptance criteria, writes the tests, opens the pull request.

## Guard

`guard.yml` runs on this repo on every push and pull request. It checks that the manifests parse, that each role carries the memory and containment clause verbatim, and that no plugin file names a stack, a vendor, or a product. Run it locally with:

```
python3 scripts/validate_plugin.py
python3 scripts/validate_workflows.py
```

## Install

```
/plugin marketplace add chamaya00/agent-factory
/plugin install agent-factory@agent-factory
```
