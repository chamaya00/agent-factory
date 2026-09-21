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

The factory's own CI, and the closest thing here to a test suite. All Python,
all pass or fail without interpretation. No count is given here: this table
once said five while `guard.yml` ran seven, so `validate_plugin.py` now checks
that the table, `CLAUDE.md`, and `guard.yml` name the same scripts.

| Script | Proves |
|---|---|
| `validate_plugin.py` | the plugin is structurally intact, still portable, and its prose agrees with each role's tool list |
| `validate_workflows.py` | every workflow parses, stays inside its limits, and grants each role the tools it declares |
| `test_ci.py` | the gate fails what it is supposed to fail |
| `test_preflight.py` | agent-run refuses the runs it is supposed to refuse |
| `test_handback.py` | a finished child wakes its parent, and silence gets reported |
| `test_project_guard.py` | a privilege change cannot arrive undeclared |
| `test_capability_claims.py` | the capability checks fire on drift and stay quiet on prose |
| `test_release.py` | a release tag cannot move or disagree with the manifest |

Most of the `test_` scripts do not read the workflows as data. They lift the
`run:` block straight out of the YAML and execute it, substituting only
the workflow expressions the runner would. So a test cannot drift away from what
ships: change the shell and the tests run the change.

### validate_plugin.py

Structural checks, in groups. No count is given: this section said thirteen
while `main()` ran sixteen, which is the same way the table above once said
five. The ones with a reason behind them rather than a convention:

- **Roles carry the containment clause.** Every role file the manifest lists must exist, have
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
- **Templates name the factory by placeholder, twice.** A caller template
  addresses the factory as `__FACTORY_REPO__` at `__FACTORY_VERSION__`, never a
  literal owner and never a literal ref. A hardcoded ref ships to every
  repository provisioned afterwards; a hardcoded owner means a fork provisions
  repositories that call upstream's workflows, green and silent. The check used
  to hold the owner inside its own pattern, so in a fork it matched nothing and
  went quiet rather than failing - it is now anchored on the shape of a reusable
  workflow reference and reads every owner.
- **The factory declares which repository it is.** `plugin.json`'s `repository`
  is what provisioning substitutes for `__FACTORY_REPO__`, and it is
  cross-checked against the checkout's `origin` where one is readable. The
  remote is a witness, not the source, so a fork that forgets to edit the field
  hears about it at its own first build instead of from a provisioned
  repository running somebody else's code. ADR 0001 has the reasoning.
- **The CODEOWNERS template names no handle.** Same reasoning one step further:
  it carries `__PROJECT_OWNER__` and no literal account. It used to ship a real
  handle with prose telling the session to replace it, and a skipped
  replacement is invisible - what lands is a perfectly formed gate file naming
  somebody who owns nothing in that repository, so it reviews nothing and looks
  configured.
- **The runbooks name every command a project gets.** `new-project.md` and
  `update-agents.md` both have to name all of `PROJECT_COMMANDS` in their own
  prose. They had drifted to five and three against a list of six, and the one
  both had lost was `check-in` - which the project template's CLAUDE.md tells
  every provisioned repository to run by name. A session following either
  runbook shipped a repository pointing at a command nobody had copied.
- **The manifest matches disk.** The roles, skills, and commands named in
  `agent-factory.json` have to be the ones actually present, or provisioning
  copies nothing and succeeds.
- **Prose agrees with the tool list.** No file in the repository may say a role
  cannot do something its own frontmatter grants a tool for, and no role file
  may ask for something it holds no tool to do. Both directions have shipped:
  the researcher and the designer were granted `create_pull_request` and told to
  open one, and four places kept saying they could not - one of them the shared
  block in the project template's CLAUDE.md, which `/update-agents` rewrites, so
  a human correcting it downstream lost the correction on the next update. The
  mirror check could not catch it, because both copies were equally wrong. It
  catches the assertion, not the insinuation: prose that merely implies the
  limit matches nothing, and separating that from true prose needs judgment.
  `test_capability_claims.py` pins both directions.
- **Prose agrees with what a run is actually granted.** The second half of the
  same check, and the half that was missing until a near miss. Frontmatter is
  not what gates a command inside a workflow run: `agent-run.yml` builds a
  separate per-role allowlist and the action enforces that one. The designer
  was given `Bash` in frontmatter and four steps telling it to build a page and
  open it, while its runtime allowlist held `gh` and `git` and nothing that
  runs anything - every check passed, and a run would have been refused and
  spent an attempt reporting it. So the capability table now also names, per
  capability, the allowlist entries that satisfy it in a run, matched as exact
  strings rather than by reimplementing the action's prefix matcher. What it
  deliberately does not do is read loose prose like "run the repo's own checks"
  against command prefixes: that is inference, and a check that fires on prose
  it should not is worse than no check. The loose end is handled by naming
  commands instead - see the entry-point check below.
- **The template ships one memory file per role.** A missing one reads exactly
  like an empty one, which is how the analyst went without for several
  releases.
- **The docs folder carries no Liquid.** `docs/` is a Pages site, built by
  Jekyll on every push to the default branch by a program this gate does not
  run. Jekyll renders Liquid before Markdown, so backticks protect nothing: a
  workflow expression written into a page collapses to a bare dollar sign, and
  an unclosed tag fails the build. The first had already happened and was green
  for as long as the sentence existed. A raw tag is the escape hatch, and ADR
  0002 records what this covers of that gap and what it leaves.
- **The gate names itself consistently.** Every `scripts/*.py` must be run by
  `guard.yml` and named in both `CLAUDE.md` and this file. A script nobody runs
  proves nothing, and an inventory that omits one sends a reader looking for a
  check that is there.
- **A command a role is told to run is a command the template ships, and one
  the role may run.** Where a role file names `./scripts/<thing>`,
  `templates/project/scripts/<thing>` must exist and be executable, the role's
  frontmatter must grant `Bash`, and the role's branch of the runtime allowlist
  must grant `Bash(./scripts/*)`. Three files have to agree, and until the last
  two were checked, two of them could disagree quietly. This one is a graduated lesson. The designer held a
  shell grant for rendering mocks through a whole objective and never rendered
  one: the grant was real, the role was told to render, no project shipped
  anything to call, and the role had no name to reach for. Nothing went red,
  because the failure mode of a missing capability is silence - the design was
  specified, built, and merged with no eye on a rendered page. Role files and
  the template ship in the same release, so a disagreement here is a
  disagreement in every repository provisioned afterwards.
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

Then the check that exists because that one was not enough: no `Bash(...:*)`
entry may end its prefix mid-argument. `Bash(x:*)` is shorthand for `Bash(x *)`
and the space is part of the rule, so `Bash(bash tests/:*)` asks for a command
ending at `bash tests/` and matches nothing at all. Six entries were written
that way and every one of them granted exactly nothing. Both checks above
passed the whole time they were there: one confirms a role is granted Bash, the
other that a runner needing no package.json is listed, and neither asks whether
what is listed can match a command. Run 34200686220 is what the gap cost.

Then the check that exists because neither of those asks what a role can reach:
every role must be granted `git fetch` and `git checkout`. A revision round is
told to work on the branch and the pull request that already exist, and the run
starts on a fresh branch holding neither. Reading the real branch is possible
without them - `git show origin/<ref>:<path>` is not refused - but writing to it
is not, because both push paths send a local branch and nothing else permitted
builds a local ref at the pull request's history. Those four commands sat in the
engineer's branch of the `case` alone, so the revision path was dead for the
other four roles from the day `agent:revise` shipped. A researcher sent back on
a review read it, worked out the whole fix, was refused every command that could
reach its branch, and stopped. Nothing reported it: the label applied, the run
started, the budget was spent, and the diff never moved, which is what a working
round looks like from outside. The same gap costs an interrupted run its work -
a second attempt cannot resume the first one's branch either.

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

**`project-guard.yml`** enforces what an agent could otherwise undo quietly.
Memory files stay inside a 40 non-blank-line cap, so a retro rewrites rather
than appends. A pull request from a non-maintainer touching
`.github/workflows/`, `CODEOWNERS`, `.claude/agents/`, `.claude/skills/`,
`.claude/commands/`, or `agent-factory.json` fails. It reads the pull request
author, which is why a maintainer's pull request passes it and an agent's would
not. A diff that widens what the automation may do has to say so in the body.

Two things it checks about the project's own `CLAUDE.md`, both for the same
reason - that file is the first thing every agent run loads, so a defect in it
is read by every role before it reads anything else. The managed block's
markers have to be present exactly once each or absent entirely, because
`/update-agents` cannot replace a block it cannot locate. And no line may be a
bracketed placeholder left over from the template: provisioning fills one in,
and one that survives reads as configured while saying nothing. Only a bracket
that is the whole line counts, so ordinary prose with links in it passes;
`validate_plugin.py` holds the template to that same shape, which is what keeps
the pair honest in both directions.

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

- **Most roles have never completed a run.** Only the researcher
  has run successfully under the current allowlist. The engineer is the one to
  watch: it is the only role that needs `Bash(npm run:*)` and the only one
  whose output has to pass the gate rather than merely exist. It has now been
  tried once, on new-project-agents-v3#18, and it failed in exactly the place
  this bullet points at - refused by its own test-runner grants, which is the
  failure the check above now catches. Until an engineer run lands a pull
  request that passes CI, treat step 3 of the smoke test as untested rather
  than passing.
- **Nothing builds the docs site, and nothing would report it failing.** The
  check above reads the source for the one hazard that has actually bitten;
  the build itself - theme, the three Pages plugins, link rewriting between
  `.md` files - is verified by a person opening the page and by nothing else.
  A project gets a bound here that this repository does not: the scheduled
  sweep in `agent-run.yml` names a red default branch and says so on the open
  objective, and no agents run here. ADR 0002.
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

They all run locally, in seconds, with no credentials:

```
python -m pip install pyyaml
python scripts/validate_plugin.py
python scripts/validate_workflows.py
python scripts/test_ci.py
python scripts/test_preflight.py
python scripts/test_handback.py
python scripts/test_project_guard.py
python scripts/test_capability_claims.py
python scripts/test_release.py
```

Run them before opening a pull request here. They are the same commands
`guard.yml` runs, in the same order.
