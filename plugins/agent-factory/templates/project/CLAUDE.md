# Project context

<!-- Replace the bracketed lines. Everything else is the standing arrangement. -->

## What this is

[One sentence: what this product does and for whom.]

## Stack

[Language, framework, data store, hosting. Name the versions that matter.]

## Commands

- Install: [command]
- Dev: [command]
- Checks CI runs: [one line per check, naming the command. On a Node project
  that is `npm run typecheck`, `npm run lint`, `npm run test`, `npm run build`.
  On a project with no package manager it might be a single `bash
  tests/check.sh`, and one check is a complete answer - name what this project
  has rather than the four a Node project would have.]

The checks above are what CI runs once the gate is real. Until then it is
not: `.github/workflows/ci.yml` ships a placeholder that checks the scaffolding
is intact and fails the moment product code lands, because a project gets its
gate before it gets its stack and a gate that goes green on untested code is
worse than no gate. Replacing it is a step in building this project, not a
chore to do later - the comment at the top of that file says how.

Whatever the gate runs, the rule is the same. If a check is renamed here,
rename it in `.github/workflows/ci.yml` in the same commit, and re-point the
branch protection rule in the same sitting, or the gate silently stops checking
that thing.

<!-- agent-factory:begin -->
<!-- Everything from here to the agent-factory:end marker describes the shared
     process rather than this project, and /update-agents replaces the whole
     block when this repository moves to a new factory release. An edit inside
     it is lost on the next update: put anything specific to this repository
     outside the block, where nothing will overwrite it. -->

## How work moves

Objectives become issues labelled `objective`. A human labels the objective
`agent:queued`; nothing else needs labelling by hand. The orchestrator splits it
into 2-5 child issues, each with acceptance criteria and one role label, and
then queues them itself as each one becomes ready.

It stays with the objective after the split. A child reaching `agent:review` or
`agent:blocked` wakes it: it reads the state of every child, queues whatever the
merge has just unblocked, rewrites and re-queues a child that blocked on its own
scoping, and replaces the status picture on the parent issue. The parent issue
is the whole surface - a human reads that and nothing else, and hears from the
orchestrator when a decision is genuinely theirs.

Ready means the issues a child depends on are merged to the default branch, not
merely finished and labelled `agent:review`. Every role opens a pull request
for its own work, the researcher and the designer included, so the usual gap is
an open pull request nobody has merged yet rather than a branch with no pull
request behind it - and either way the work is invisible to the next agent,
which reads the default branch. A run started too early refuses, correctly, and
still spends one of that issue's three attempts. That check is now the
orchestrator's to make before it queues anything.

The human still decides what merges. The orchestrator queues work and reports on
it; it does not merge a pull request, and it cannot break a child down further -
that comes back as `needs-decomposition` and a comment on the parent.

Labels: `objective`, `agent:queued`, `agent:running`, `agent:review`,
`agent:blocked`, `needs-decomposition`, `needs-human`, `role:researcher`,
`role:designer`, `role:engineer`.

## Driving an objective

A session that files an objective, or is pointed at one, is that objective's
driver and the person's window into it. Nobody else is watching. Filing one is
`/objective`, which refines the idea, sets the merge policy, queues it, and
hands back to the session to drive.

**Read `.claude/skills/driving-an-objective/` whenever an objective is in play**
- what to do with its merge policy, how to report, how to put a blocker so it
can be answered, and what only the person can decide. This paragraph exists to
say the role is yours; the skill says how to hold it.

## The rules

Not restated here. Two sections used to summarise them and every line had a
fuller source a click away, so the summaries could only ever drift out of
agreement with the thing they summarised - which is worse than not having them,
because a reader who finds a rule here stops looking for the real one.

- `.claude/skills/house-rules/` - what must be true before work starts and
  before anything merges, who may merge, the three-strike rule, and what no
  agent may touch.
- `.claude/skills/memory-protocol/` - how this repository's lessons are stored,
  capped, proposed, and retired.
- `.claude/skills/acceptance-criteria/` - what a criterion has to look like to
  gate anything.
- `.claude/skills/driving-an-objective/` - what the session in front of a person
  does once an objective is running.

Every agent run is told to follow the first three by name. The fourth is for the
session driving, which is why the section above names it rather than leaving it
to be discovered.

<!-- agent-factory:end -->
