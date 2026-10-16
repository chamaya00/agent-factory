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
| 3. `/dispatch` preconditions | every agent run | the session running it | a run that should not start is refused, and every run is booked on its issue |
| 4. the two runbooks | by hand, once per setup | a throwaway repo | the loop end to end |

Layers 1 and 2 are deterministic: each one passes or fails with nothing to
interpret, and no model decides any of it. Layer 3 is a procedure a session
follows, so it is as reliable as the session following it - which is why the
checks that matter most in a project are the ones in layer 2, which no session
can talk its way past. Layer 4 is the only one that exercises a real agent, and
the only one a human has to sit through.

## Layer 1: guard.yml

The factory's own CI, and the closest thing here to a test suite. All Python,
all pass or fail without interpretation. No count is given here: this table
once said five while `guard.yml` ran seven, so `validate_plugin.py` now checks
that the table, `CLAUDE.md`, and `guard.yml` name the same scripts.

| Script | Proves |
|---|---|
| `validate_plugin.py` | the plugin is structurally intact, still portable, and its prose agrees with each role's tool list |
| `validate_workflows.py` | every workflow parses and stays inside its limits |
| `test_ci.py` | the gate fails what it is supposed to fail |
| `test_project_guard.py` | a privilege change cannot arrive undeclared, and a gate edit from an agent branch is stopped whoever opened it |
| `test_capability_claims.py` | the capability checks fire on drift and stay quiet on prose |
| `test_release.py` | a release tag cannot move or disagree with the manifest |
| `test_provision.py` | provisioning refuses a bad request or a missing approval gate, and requires only the gates' check names |

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
- **The README names every command.** `README.md` has to name each file in
  `plugins/agent-factory/commands/` as `/<name>`. It is the first page a human
  reads and it restates the list by hand, and it had drifted to five against
  eight. The three it lost were `/objective`, `/check-in`, and `/ship`: the
  command every piece of work starts from, and the two that carry it to a
  merge. So the first page never mentioned the command `/new-project`'s closing
  report sends the person to type next. Only presence is checked: each line
  says what its command is for, which a list generated from filenames would
  drop, and whether that sentence is still true needs a reader.
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
  `guard.yml` and named in both `CLAUDE.md` and this file, and every other
  workflow that runs a script must name one that exists. A script nobody runs
  proves nothing, an inventory that omits one sends a reader looking for a
  check that is there, and `release.yml` once kept running a deleted script
  with every check green - the first sign would have been a failed release.
- **A command a role is told to run is a command the template ships, and one
  the role may run.** Where a role file names `./scripts/<thing>`,
  `templates/project/scripts/<thing>` must exist and be executable, and the
  role's frontmatter must grant `Bash`. This one is a graduated lesson. The designer held a
  shell grant for rendering mocks through a whole objective and never rendered
  one: the grant was real, the role was told to render, no project shipped
  anything to call, and the role had no name to reach for. Nothing went red,
  because the failure mode of a missing capability is silence - the design was
  specified, built, and merged with no eye on a rendered page. Role files and
  the template ship in the same release, so a disagreement here is a
  disagreement in every repository provisioned afterwards.
- No emoji in any `.md`, `.json`, `.yml`, or `.py` file in the repository.

### validate_workflows.py

Every workflow, factory and templates, must parse as YAML, declare an `on:`
block, give every job that is not a `uses:` call a `timeout-minutes`, and never
request `actions: write`. A system that can rewrite its own gates has no gates.

Then two checks on the project's own gates. `project-guard`'s privilege step
must keep running with no maintainer exemption, because the case it exists for
is a pull request merged on the owner's behalf under a standing policy, whose
author is a maintainer. And the guard caller a project receives must re-run
when a pull request body is edited, because the body is what that step reads.
Last, the `ci` job's check name must be the same in the reusable workflow's
default and the template's caller, because it is the name branch protection
matches on, and a required check that stops reporting blocks every merge.

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

### test_provision.py

Thirty-four cases against a fake `gh`, on three steps of `provision.yml`. It is
the one workflow here that holds an admin token for every repository the person
owns, so what it refuses is the whole of its safety, and each refusal is
executed rather than read.

The request: a repository name typed into an issue title or a dispatch box is
the one untrusted input, and it reaches a shell and `GITHUB_OUTPUT`. A plain
`owner/repo` on the person's own account is accepted and trimmed; another
account, the factory itself, a dot, a path, and five shapes that would run
something or write a second output line are refused, and every refusal has to
say why on the request. None of it may call `gh`, because that job holds no
token and needs none.

The approval gate: the run goes no further unless the `provision` environment
exists, has a required-reviewer rule - a wait timer is a rule and approves
nothing - and limits which branches may use it. A run started from another
branch is refused before any call.

Branch protection: only the two gates' check names, as they reported on a push
to the default branch, are required - not another push workflow on the same
commit. A guard that failed at startup is re-run once and no more. A gate that
never reported, is still running, or still failed after its one re-run sets no
rule at all, rather than a rule requiring the other gate alone. An existing rule
is added to and never replaced, and a rule that does not read back is reported
as not set.

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
not - and the head branch, because a role dispatched from a session opens its
pull request as the person, so the author alone cannot tell them apart. A
maintainer-authored pull request from a branch matching `agent-branches`
(`claude/*` by default) is checked as the automation's, with no author or
sender exemption; ADR 0004 says why that is a tripwire rather than a wall. A
diff that widens what the automation may do has to say so in the body.

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

**`bootstrap.yml`** is one-shot and manual. It creates the labels - whose
names are load-bearing, since `/dispatch` and the roles match them exactly - and reads
back the check names actually reported on the default branch, for pasting into
branch protection. Reading them back rather than assuming them is the point: a
renamed job silently stops being a required check, which reads as green when it
is really absent.

Every caller a project receives declares the permissions its reusable workflow
asks for. GitHub gives a new repository a read-only default token, and a called
workflow that asks for more than its caller was given never starts - no job, no
log, just `startup_failure` - so a caller that left this to the repository
setting needed a person to change that setting first.

## Layer 3: what `/dispatch` refuses

Agents run from sessions, so the preconditions on a run are steps in
`/dispatch` rather than a workflow. A session follows them; nothing executes
them for it.

- **One run per issue at a time.** `agent:running` is the lock, re-read
  immediately before booking, because another session may have started the
  issue a minute ago.
- **A person's stop is honoured.** `needs-decomposition` and `agent:blocked`
  refuse; so does an issue carrying two role labels, which is two issues.
- **The budgets are counted, not remembered.** Three attempts, two revision
  rounds, twenty supervision runs, each counted from its own marker comment on
  the issue, so a fresh session counts the same number the last one did.
- **Every run is booked before it starts** - the label and the marker comment
  go on first - so a run that dies still left a trace, and the next session
  hands it back rather than finding an issue that looks busy forever.
- **Hard limits restated in the brief**: never touch the workflow files, the
  role copies, `.claude/commands/`, or `CODEOWNERS`; never skip or disable a
  test to get a check green; stay inside the one issue; merge nothing. What
  backs the first of those with a machine is `project-guard`, in layer 2.

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
2. Every label the `bootstrap` workflow creates, which is the list under
   `labels` in the project's `.claude/agent-factory.json`.
3. Branch protection using the check names that run reported.
4. A release tag matching the version in the plugin manifest. The callers are
   pinned to it, and a pin with no tag behind it fails as an invalid workflow
   reference naming nothing about a tag in another repository.
5. Publishing configured on that repository, serving the default branch from
   its root. It is a repository setting, so no agent can turn it on, and the
   objectives are not acceptable until something is visible at the published
   URL. Set it before filing anything, so its 404 is expected rather than
   discovered halfway through.

Then two objectives go through eight steps each: the orchestrator splits one,
the session dispatches the children in dependency order, the engineer opens a
pull request, you merge and open the site, you send one back for a revision,
and `/retro` proposes a memory entry. What to watch for at each step, and the eight
failure modes worth recognising on sight, are in that file.

## What is not checked

Everything automated tests form. Nothing automated tests behaviour, by design -
no model runs in `guard.yml`, because a check that needs judgment is not a gate.
That leaves real gaps, and they are worth naming.

- **The session runner has not yet carried an objective end to end.** Each
  piece was checked on its own on 2026-10-15 - a role subagent reaches the
  GitHub tools, a child session reaches GitHub and git, and session pull
  requests are authored by the owner - but no objective has gone from
  `/objective` to merged under it yet. Treat the smoke test as untested under
  sessions until one has.
- **Nothing builds the docs site, and nothing would report it failing.** The
  check above reads the source for the one hazard that has actually bitten;
  the build itself - theme, the three Pages plugins, link rewriting between
  `.md` files - is verified by a person opening the page and by nothing else.
  ADR 0002.
- **Nothing confirms branch protection still matches the job names.**
  `bootstrap` reports the names; keeping the rule pointed at them is manual,
  and the drift reads as green.
- **A run that dies for a configuration reason still burns an attempt.** The
  attempt marker is written before the role starts, so a run that never got to
  attempt anything consumes a third of the issue's budget.
- **Nothing executes `/dispatch`'s refusals.** They are a procedure a session
  follows, not a script; a session that skipped one would not be caught by
  anything but the labels and marker comments it left, or failed to leave.

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
python scripts/test_project_guard.py
python scripts/test_capability_claims.py
python scripts/test_release.py
python scripts/test_provision.py
```

Run them before opening a pull request here. They are the same commands
`guard.yml` runs, in the same order.
