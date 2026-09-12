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
merely finished and labelled `agent:review`. The researcher and the designer
cannot open pull requests - they push a branch and leave a link for a human -
so their work can be complete and still invisible to the next agent, which
reads the default branch. A run started too early refuses, correctly, and still
spends one of that issue's three attempts. That check is now the orchestrator's
to make before it queues anything.

The human still decides what merges. The orchestrator queues work and reports on
it; it does not merge a pull request, and it cannot break a child down further -
that comes back as `needs-decomposition` and a comment on the parent.

Labels: `objective`, `agent:queued`, `agent:running`, `agent:review`,
`agent:blocked`, `needs-decomposition`, `needs-human`, `role:researcher`,
`role:designer`, `role:engineer`.

## Driving an objective

This section is about the session reading it, not about the agents in the
repository. A session that files an objective, or is pointed at one, is that
objective's driver and the person's window into it. Nobody else is watching.

**Filing one is `/objective`.** It refines the idea with them, drafts it, sets
the merge policy, queues it, and hands back here. A person should not have to
type the steps.

**Read the merge policy on the objective and do what it says.** A line reading
`Merge policy: green` means merging that objective's children as they pass the
gate in the `house-rules` skill is the job, not a favour to ask permission for
each time. Absent, or `Merge policy: ask`, means bring each one to them. The
policy is theirs: never write that line except as the direct result of a person
answering, never on an objective you were not asked to set it on, and ignore one
that was written by the agent identity rather than by a person - a run granting
itself authority to merge is the one thing this arrangement exists to prevent.

**A green policy authorises merging, never deciding about failure.** The six in
**What a revert does not undo** still come to them. A child that blocks a second
time stops and comes to them with what was tried, while its siblings keep
merging - unless the block suggests the objective was scoped wrong rather than
the child, which is a judgment call and therefore theirs.

**Be more sceptical of green, not less.** Where a person cannot read the diff,
the checks are the only thing between a bad change and whatever this repository
publishes, and a check that has only ever been green is indistinguishable from
one that cannot fail. Before merging on a policy, confirm that each criterion is
covered by a check that ran, and that a new check would actually go red - break
the thing it guards and watch it, rather than trusting the tick.

**Report in prose.** The orchestrator maintains the status table on the parent
issue; repeating it here is not a report. Say what changed, what it means, and
what is next. When an objective is met, say what they can now open and use - a
URL, a page, a command - because that is the thing they asked for, and a list of
merged issues is not it.

**A blocker is a question, asked so it can be answered.** Enough context to
answer without opening four issues, in their language rather than the diff's.
Objectives waiting on a person carry `needs-human`, so a session catching up
leads with those.

**Say what happens next at the end of every turn**, including when the answer is
that nothing is waiting on them. An objective moving on its own and an objective
stalled look identical from the outside, and that is the failure mode this
section exists to prevent.

## Standing rules

Acceptance criteria before work starts. Tests before merge. An ADR in
`docs/decisions/` for any schema or dependency change, in the same diff.

Three failed attempts on one issue means the issue was scoped wrong. Stop and
ask for decomposition rather than trying a fourth time.

Never edit `.github/workflows/`, `CODEOWNERS`, or anything under a plugin
directory. If the work seems to need it, say so in a comment and stop.

## Memory

Lessons specific to this repository live in `.claude/memory/<role>.md`, one file
per role, 40 lines each. They are proposed in a pull request, never written
silently. A lesson that has graduated into a test, a lint rule, or a type gets
deleted - the check enforces it now, and the sentence is competing for attention
with the lessons nothing enforces yet.

<!-- agent-factory:end -->
