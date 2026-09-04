# What is checked

Four different things get called "checking that the agent system works", and
they cover different ground. This page says which is which, what each one
actually asserts, and - the part worth reading first - what nothing asserts
yet.

## There is no smoke-test workflow

`docs/smoke-test.md` is a runbook for a person, not an Action. Nothing under
`.github/workflows/` is named smoke, and no job invokes it. It is phase 8 of
standing the system up: you file two objectives by hand and watch the loop carry
each one, judging the result yourself.

That matters because its pass conditions are not mechanical. "The children have
checkable acceptance criteria" and "the tests map onto those criteria one to
one" are the conditions, and a script cannot decide either. It is a manual
check because the thing it checks needs judgment, not because nobody got round
to automating it.

What the judgment is spent on changed, though, and that was the point of the
rewrite. The objectives build a website that publishes from the repository, so
the top-level question is answered by opening the published URL and looking at
it rather than by reading the diff. How much of the diff you had to read is the
number that phase reports back, because a phase 8 that needs a careful line-by-
line read has demonstrated the opposite of what it set out to.

The automated checking is elsewhere.

## The four layers

| Layer | Runs | Where | Proves |
|---|---|---|---|
| 1. `guard.yml` | every push and pull request | this repository | the factory is well formed and its shell does what it claims |
| 2. `ci.yml`, `project-guard.yml` | every push and pull request | each project | the project's own gate holds, and agents stay out of it |
| 3. agent-run preconditions | every agent run | each project | a run that cannot work refuses to start |
| 4. the two runbooks | by hand, once per setup | a throwaway repo | the loop end to end |

Layers 1 to 3 are deterministic: each one passes or fails with nothing to
interpret, and no model decides any of it. Layer 4 is the only one that
exercises a real agent, and the only one a human has to sit through.

## Layer 1: guard.yml

The factory's own CI, and the closest thing here to a test suite. Five scripts,
all Python, all pass or fail without interpretation.

| Script | Proves |
|---|---|
| `validate_plugin.py` | the plugin is structurally intact and still portable |
| `validate_workflows.py` | every workflow parses, stays inside its limits, and grants each role the tools it declares |
| `test_ci.py` | the gate fails what it is supposed to fail |
| `test_preflight.py` | agent-run refuses the runs it is supposed to refuse |
| `test_release.py` | a release tag cannot move or disagree with the manifest |

The last three do not read the workflows. They lift the `run:` block straight
out of the YAML and execute it, substituting only the `${{ }}` expressions the
runner would. So a test cannot drift away from what ships: change the shell and
the tests run the change.

### validate_plugin.py

Eleven groups of structural checks. The ones with a reason behind them rather
than a convention:

- **Roles carry the containment clause.** All four role files must exist, have
  `name` and `description` frontmatter matching the filename, keep the body
  under 45 lines, and end with the memory-and-containment paragraph verbatim. A
  role missing it can read the wrong memory file or write where it must not.
- **Portability.** 68 nouns that tie a file to one stack, vendor, or product
  fail the build if they appear anywhere in the plugin. The plugin describes
  how we work, not what any one project is built from, and this is the check
  that keeps that true a year from now.
- **The vendored copy matches.** `.claude/` in this repository must be byte
  identical to `plugins/agent-factory/`. Those copies are what a session
  actually loads, so drift between them means the factory runs different rules
  than it ships.
- **No marketplace declaration.** Nothing may declare `extraKnownMarketplaces`
  or `enabledPlugins` to load these commands. It reads like it works and does
  nothing in an untrusted folder, which is how it survived two releases.
- **Templates pin the placeholder.** A caller template must address the factory
  at `__FACTORY_VERSION__`, never a literal ref. A hardcoded ref ships to every
  repository provisioned afterwards.
- **The manifest matches disk.** The roles, skills, and commands named in
  `agent-factory.json` have to be the ones actually present, or provisioning
  copies nothing and succeeds.
- No emoji in any `.md`, `.json`, `.yml`, or `.py` file in the repository.

### validate_workflows.py

All ten workflows, factory and templates, must parse as YAML, declare an `on:`
block, give every job that is not a `uses:` call a `timeout-minutes`, and never
request `actions: write`. A system that can rewrite its own gates has no gates.

Then the check that exists because of a real failure: it parses the `case`
statement in agent-run's allowlist step and confirms every role is granted the
tools its own definition declares. The first agent run this system ever made
posted a correct decomposition and then could not create the child issues,
because no allowlist was passed and the action's default set is read only. The
orchestrator surfaced it first because it runs first; the engineer would have
been worse off, unable to write a line of code.

### test_ci.py

Sixteen cases, run under the same `bash -e -o pipefail` GitHub uses for a `run:`
block. The gate's commands path is hand-written shell, and a bug in it does not
fail loudly - it passes a run that should have failed, which is the one failure
mode a gate cannot have.

Every command runs in order; the first failure stops the run there; a missing
binary fails rather than being skipped; blank lines and comments are not
commands; leading and trailing whitespace is trimmed; nothing runnable is a
failure rather than a pass; `false && x` still fails the line; a failure
mid-pipeline is not hidden by the last command; an unset variable is an error
rather than an empty string.

Then six cases on the placeholder gate the project template ships, run against
real temporary git repositories. They pull the `commands` block straight out of
`templates/project/.github/workflows/ci.yml`, so they cannot drift from what a
provisioned repository actually receives. A freshly provisioned repository
passes; research writing an ADR and design writing a document still pass,
because those two roles produce prose and there is nothing yet to test; product
code at the root, product code in a subdirectory, and a package manifest each
fail, and the error has to name the file that tripped it.

That last group exists for a failure nothing else catches. A project gets its
gate before it gets its stack, so the gate it is provisioned with cannot test a
product that does not exist yet. The danger is not that the placeholder is
inadequate on day one - it is that nobody remembers to replace it, and every
pull request goes green on work no check ever read. The tripwire turns that from
silence into a red check with the instruction attached. Switching the template
to the Node path makes `test_ci.py` stop with an explanation rather than
quietly skipping this group.

### test_preflight.py

Fifteen cases against a fake `gh`. This is the only place in the repository
where a bug spends money, so the preflight gets executed rather than read.

An objective runs the orchestrator; one role label runs that role; no role
label does not run; two role labels refuse rather than guess;
`needs-decomposition` and `agent:blocked` refuse; a label that is not the run
label does nothing; a comment without the trigger phrase does nothing and a
comment with it runs; the third attempt still runs and the fourth fails the
job; a docs-only pull request is not worth a run and one touching source is;
`workflow_dispatch` takes the number from its input.

The fifteenth is not a decision but a trace: refusing a fourth attempt has to
label the issue `agent:blocked` and comment why, or the refusal reads as a
flake.

### test_release.py

Fifteen cases against real temporary git repositories. A bug here is either a
tag that disagrees with the plugin manifest, which installs as the version
already cached and updates nothing, or a release tag that moves, which silently
changes what a project resolves after its author reviewed and pinned it.

The tag name comes from the manifest; a version disagreeing with it is refused;
an existing tag is refused rather than moved; an unrelated tag does not block;
a missing manifest or a manifest with no version is refused. Then eight
malformed versions, including the moving pointers `v1`, `v1.2` and `main`, and
`v1.2.0; rm -rf /`, because the step writes a ref.

## Layer 2: the gates every project receives

Three reusable workflows, called from each project in one line and pinned to a
release.

**`ci.yml`** runs `typecheck`, `lint`, `test`, `build`. A named script that
does not exist fails the run rather than being skipped, which is the whole
difference between a gate and a decoration. Projects that are not Node pass a
`commands` input instead, and that path is what `test_ci.py` covers.

**`project-guard.yml`** enforces the two things an agent could otherwise undo
quietly. Memory files stay inside a 40 non-blank-line cap, so a retro rewrites
rather than appends. And a pull request from a non-maintainer touching
`.github/workflows/`, `CODEOWNERS`, `.claude/agents/`, `.claude/skills/`,
`.claude/commands/`, or `agent-factory.json` fails. It reads the pull request
author, which is why a maintainer's pull request passes it and an agent's would
not.

**`bootstrap.yml`** is one-shot and manual. It creates the nine labels - whose
names are load-bearing, since the preflight matches them exactly - and reads
back the check names actually reported on the default branch, for pasting into
branch protection. Reading them back rather than assuming them is the point: a
renamed job silently stops being a required check, which reads as green when it
is really absent.

## Layer 3: the refusals inside a run

Not tests, but preconditions checked on every agent run, each one turning a
silent failure into a loud one.

- **The roles are in the repository.** If `.claude/agents/` is empty the job
  errors out. An agent that starts with no roles does not fail, it improvises,
  and that produces a pull request that looks like work and follows none of the
  rules.
- **Every role has an allowlist branch.** A role with no branch is a hard
  error rather than a run with the read-only default.
- **One run at a time, queued, never cancelled.** A cancelled run has already
  spent its tokens and leaves the issue half finished.
- **`actions: write` is never granted**, at any level, in any workflow.
- **Hard limits restated in the prompt**: never touch the workflow files, the
  role copies, or `CODEOWNERS`; never skip or disable a test to get a check
  green; stay inside the one issue.

## Layer 4: the two runbooks

`docs/proving-the-gate.md` (phase 7) and `docs/smoke-test.md` (phase 8) are the
only checks that cover the loop end to end.

Phase 7 proves the gate before any agent is pointed at it, and its fourth step
is the one that actually proves something: open a pull request that breaks a
test on purpose and confirm the merge button is disabled. A gate that has never
refused anything is not known to be a gate.

Phase 8 needs all of this in place before it can start, and each item is a
separate way for it to fail confusingly:

1. A repository provisioned by `/new-project`, from phase 7.
2. `CLAUDE_CODE_OAUTH_TOKEN` on that repository. Secrets are per repository,
   and without it every run fails immediately at auth.
3. Both Actions settings ticked: read and write permissions, and "Allow GitHub
   Actions to create and approve pull requests". With the second one off the
   run succeeds and no pull request ever appears.
4. The nine labels, from the `bootstrap` workflow.
5. Branch protection using the check names that run reported.
6. A release tag matching the version in the plugin manifest. The callers are
   pinned to it, and a pin with no tag behind it fails as an invalid workflow
   reference naming nothing about a tag in another repository.
7. Publishing configured on that repository, serving the default branch from
   its root. It is a repository setting, so no agent can turn it on, and the
   objectives are not acceptable until something is visible at the published
   URL. Set it before filing anything, so its 404 is expected rather than
   discovered halfway through.

Then two objectives go through eight steps each: the orchestrator splits one,
you queue the children in dependency order, the engineer opens a pull request,
you merge and open the site, you ask for a revision with the trigger phrase, and
`/retro` proposes a memory entry. What to watch for at each step, and the eight
failure modes worth recognising on sight, are in that file.

## What is not checked

Everything automated tests form. Nothing automated tests behaviour, by design -
no model runs in `guard.yml`, because a check that needs judgment is not a gate.
That leaves real gaps, and they are worth naming.

- **Three of the four roles have never completed a run.** Only the researcher
  has run successfully under the current allowlist. The engineer is the one to
  watch: it is the only role that needs `Bash(npm run:*)` and the only one
  whose output has to pass the gate rather than merely exist. Until an engineer
  run lands a pull request that passes CI, treat step 3 of the smoke test as
  untested rather than passing.
- **Nothing confirms branch protection still matches the job names.**
  `bootstrap` reports the names; keeping the rule pointed at them is manual,
  and the drift reads as green.
- **Nothing confirms the OAuth secret exists** until a run fails at auth.
- **A run that dies for a configuration reason still burns an attempt.** The
  attempt marker is written before the agent starts, so a run that never got to
  attempt anything consumes a third of the issue's budget.

`docs/open-questions.md` is the live register of these, each with how to settle
it and what changes once you do. This section is a summary of it; that file is
the source.

## Running the checks yourself

All five run locally, in seconds, with no credentials:

```
python -m pip install pyyaml
python scripts/validate_plugin.py
python scripts/validate_workflows.py
python scripts/test_ci.py
python scripts/test_preflight.py
python scripts/test_release.py
```

Run them before opening a pull request here. They are the same five commands
`guard.yml` runs, in the same order.
