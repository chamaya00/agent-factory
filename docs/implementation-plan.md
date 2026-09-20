# Implementation plan: `agent-factory`

Paste this whole document into Claude Code as your first message. Work through it in order.

---

## Read this first

**Who I am and what I have**

- GitHub handle: `chamaya00`
- I work entirely from an iPhone. No Mac, no local terminal. You are running as a Claude Code cloud session.
- I am on a **Claude Pro** subscription. This system must run on my subscription, not on API credits.
- I know product analytics and data science well. I ship indie apps. I am not looking for a lecture on git.

**Rules for you during this build**

1. **Verify before you write.** Plugin and skill file schemas change. Before writing any manifest, fetch and read:
   - `https://code.claude.com/docs/en/plugins-reference`
   - `https://code.claude.com/docs/en/sub-agents`
   If what you read contradicts anything in this plan, follow the docs and tell me what changed.
2. **Stop at every `CHECKPOINT`.** Those are steps only I can do. Do not continue past one until I confirm.
3. **Do not invent config.** If a field is unclear, ask me rather than guessing.
4. **Commit in small, labelled commits.** One per phase.
5. **No emoji in any file you create.**

**What we are building**

A reusable toolbox repo that turns high-level objectives into working code across any of my future projects. Three separable layers:

| Layer | Lives in | How it travels |
|---|---|---|
| Agent roles and process | `agent-factory` plugin | Enabled once on my Claude account, loads in every session |
| Automation | `agent-factory` reusable workflows | Each project calls them in one line |
| Project-specific learning | Each project's own repo | Never leaves that repo |

The third row is the important one. Agents get smarter inside a project without contaminating other projects.

---

## Phase 1 - Scaffold the factory repo

Create a **public** repo `chamaya00/agent-factory`. Public because private-repo workflows cannot be called from public repos, and it will contain no secrets.

Target structure:

```
agent-factory/
  .claude-plugin/
    marketplace.json
  plugins/
    agent-factory/
      .claude-plugin/
        plugin.json
      agents/
        orchestrator.md
        researcher.md
        designer.md
        engineer.md
      skills/
        house-rules/SKILL.md
        memory-protocol/SKILL.md
        acceptance-criteria/SKILL.md
      commands/
        new-project.md
        decompose.md
        retro.md
  .github/workflows/
    ci.yml
    agent-run.yml
    guard.yml
  README.md
```

Two things to get right:

- `plugin.json` **must** include an explicit `name` field. Without it the plugin identity falls back to the install directory name, which is a version string that changes on every update.
- Everything except the manifests goes at the **plugin root**, not inside `.claude-plugin/`.

Commit. Then tag `v1`.

---

## Phase 2 - Write the four agent roles

Each is a markdown file with frontmatter (`name`, `description`, `tools`) and a system prompt body.

Keep each body under ~40 lines. These describe **how we work**, never **what any specific project contains**. If you catch yourself writing a stack name, a product name, or a domain concept, delete it - that belongs in a project repo.

**`orchestrator`**
Reads an objective issue. Produces 2-5 child issues, each with explicit acceptance criteria. Assigns each a role label. May not create grandchildren - anything needing further breakdown gets labelled `needs-decomposition` and waits for me. Tools: issue read/write, repo read. No file writes.

**`researcher`**
Investigates options, prior art, constraints. Output goes to `docs/research/` as markdown. Tools: read, search, web. **No** write access to `src/`.

**`designer`**
Produces flows, states, and component specs. Output goes to `docs/design/`. Same write restriction.

**`engineer`**
Implements against acceptance criteria, writes tests, opens a PR. Tools: full read/write on source, plus git and PR creation.

Every one of the four ends with this exact clause:

```
Before starting, read `.claude/memory/<your-role>.md` if it exists.
It contains lessons specific to this repository.

Never write to files under the plugin directory.
Never modify anything under .github/workflows/ or CODEOWNERS.
```

---

## Phase 3 - Write the skills

Plugins cannot ship a `CLAUDE.md` - a `CLAUDE.md` at the plugin root is not loaded as project context. Instructions must live in skills. Each skill is a `SKILL.md` with `name` and `description` frontmatter.

**`house-rules`** - Every child issue needs acceptance criteria before work starts. Tests before merge. An ADR in `docs/decisions/` for any schema or dependency change. Three failed attempts on one issue means the issue was scoped wrong; stop and ask for decomposition.

**`memory-protocol`** - This is the containment mechanism, so be precise:
- Repo learning lives at `.claude/memory/<role>.md`, one file per role.
- Agents never edit their own definitions. Only these files.
- New lessons are proposed as part of a PR diff, never written silently.
- Each file caps at 40 lines. Past the cap, the retro **rewrites** rather than appends - merge or drop entries to make room.
- Delete any lesson that has graduated into a test, a lint rule, or a type. The check enforces it now; the sentence is dead weight.

**`acceptance-criteria`** - The format the orchestrator uses. Observable and checkable, not aspirational. "Favorites persist across a tab switch, verified by a test" not "favorites work well."

---

## Phase 4 - Write the commands

**`/new-project`** - Provisions a fresh repo end to end:
- Creates labels: `objective`, `agent:queued`, `agent:running`, `agent:review`, `agent:blocked`, `needs-decomposition`, plus role labels
- Drops in the three thin caller workflows (Phase 5)
- Creates `CLAUDE.md` and empty `.claude/memory/` files
- Sets branch protection on `main` with the CI checks required
- **Enables "Allow GitHub Actions to create and approve pull requests."** This is off by default on personal-account repos and everything silently fails without it. Put it first in the script.

**`/decompose`** - Manually invoke the orchestrator on an issue.

**`/retro`** - Propose memory updates for the current repo as a PR.

---

## Phase 5 - Workflows

All real logic lives here in the factory. Project repos get thin callers that just point at `@v1`.

> Superseded. `@v1` was a moving tag, so a merge here changed what every project ran with no pull request in any of them. Callers now pin to an immutable release tag, and roles are copied into each project rather than fetched at run time. See `docs/versioning.md`.

**`ci.yml`** (`workflow_call`) - typecheck, lint, test, build. No model involved. This is the gate, and it must stay deterministic: if a check requires judgment, it is not a gate.

**`agent-run.yml`** (`workflow_call`) - wraps `anthropics/claude-code-action@v1`. Triggers on `issues: labeled`, `issue_comment`, `workflow_dispatch`.

Pro-plan settings, non-negotiable:
- `concurrency` group scoped to the **whole repo** with `cancel-in-progress: false`. One agent at a time, queued. Parallel agents will exhaust Pro.
- `timeout-minutes: 20`
- `--max-turns` capped in `claude_args`
- Path filters so doc and lockfile changes do not trigger runs
- Job fails if the issue already has 3 agent runs - that means bad scoping, not bad luck
- Permissions: `contents: write`, `pull-requests: write`, `issues: write`, `id-token: write`. **Never** `actions: write`.

**`guard.yml`** - runs on the factory itself. Validates the manifests parse, and greps plugin files for project-specific nouns. This check is what keeps portability honest a year from now.

---

## Phase 6 - CHECKPOINT: things only I can do

Stop here. Give me this as a numbered list with exact clicks, and wait.

1. **Generate the subscription token.** Pro and Max users can run `claude setup-token` to produce an OAuth token. I have no terminal - tell me to open a GitHub Codespace in mobile Safari, run it there, and copy the `sk-ant-oat01-...` value. One time only.
2. **Store it** as a repository secret named exactly `CLAUDE_CODE_OAUTH_TOKEN`. This is what makes runs bill against my Pro subscription instead of API credits.
3. **Create a GitHub App** for the agent identity. Explain why in one sentence: PRs opened with the default token land in an approval-required state and I would have to tap "Approve workflows to run" on every single one from my phone. An App token skips that.
4. **Enable the plugin on my Claude account** - `/plugin marketplace add chamaya00/agent-factory`, then install. Confirm it loads in cloud sessions.

   > Superseded twice. `/plugin` does not exist in a web session, and a user-level install would not reach one anyway. Declaring the marketplace in `.claude/settings.json` does not work either - Claude Code drops a repository-declared marketplace until the folder is trusted for project plugins, and a web session never trusts one. The commands, roles, and skills are copied into `.claude/` and read from the clone. See `docs/checkpoint.md` step 4.
5. **Connect Vercel** for preview deploys.

---

## Phase 7 - Prove the gate before wiring agents

Do not skip this ordering. Agents pointed at a gate I do not trust produce work I have to read line by line, which defeats the whole point.

1. Create a throwaway repo with `/new-project`.
2. Add one trivial component and one test.
3. Open a PR **by hand**. Confirm: checks run, preview link appears, protection blocks merge on red.
4. Only when that is boring and reliable, enable `agent-run.yml`.

---

## Phase 8 - Smoke test the full loop

Superseded. Phase 8 was rewritten around two objectives that build a site the
repository publishes, so the loop is judged by opening a URL rather than by
reading the diff - `docs/smoke-test.md` is the runbook, and this section is
kept for the reasoning that led to it. What follows is the original.

On the throwaway repo, file this objective and let it run:

> Users should be able to save items to a favorites list and see them on a separate page. Should survive a page refresh. No accounts - local storage is fine.

Label it `objective`. I expect:

1. Orchestrator comments with a plan, creates 3 child issues with acceptance criteria
2. I label one `agent:queued`
3. Engineer opens a PR, checks pass, preview link appears
4. I comment a revision, it pushes a fix
5. I merge
6. `/retro` proposes a one-line memory entry as a PR

Report back on which of those six steps worked and which needed hand-holding. That list is the real backlog.

---

## What I do not want

- Do not build a dashboard, a CLI, or a web UI. GitHub is the interface.
- Do not add Jira, Notion, or any external tracker. GitHub Issues is the tracker; the repo is the storage.
- Do not add an AI code-review step. My tests are the gate, and review costs Pro quota I need for building.
- Do not let any agent modify workflow files. A system that can rewrite its own gates has no gates.
