---
name: driving-an-objective
description: How an interactive session drives an objective it filed or was pointed at - adopting the merge policy, reporting to the person, surfacing blockers they can answer, and knowing what only they can do. Use whenever an objective is in play, a child reaches review, a pull request is waiting, or a session is catching up on what happened while nobody was watching.
---

# Driving an objective

A session that files an objective, or is pointed at one, is that objective's
driver and the person's window into it. Nobody else is watching. The agents in
the repository do their own work and report on the parent issue; nothing else
turns that into something a person can act on.

This is a posture, not a procedure to run once. It holds until the objective is
met or the person says otherwise.

## Adopt the merge policy, do not re-ask it

Read the objective's body. A `Merge policy: green` line means merging that
objective's children is the job rather than a permission to request each time;
absent, or `ask`, means bring each one to them.

What a policy authorises, what it never covers, who may write one, and how
sceptical to be of a green check are in the `house-rules` skill. Read that
before acting on a policy rather than working from memory of this paragraph.

Two things follow that are easy to get wrong:

- **Do not ask again for something already answered.** Re-asking is the failure
  the policy exists to remove, and it reads as not having looked.
- **Do not treat the policy as covering failure.** It authorises merging. A
  child that blocks, a decision only the person can make, and everything in
  **What a revert does not undo** still come to them whatever it says.

## Report in prose, not in status

The orchestrator already maintains the status table on the parent issue.
Repeating it is not a report - a person who wanted the table would read the
issue.

Say what changed, what it means, and what happens next. When an objective is
met, say what they can now **open and use**: a URL, a page, a command, and what
is different from a user's point of view. A list of merged issues answers a
question nobody asked.

Assume they have not read the diff and will not. That is the normal case and
not a failure on their part - it is why the gate exists, and why what you say
about the work matters more than the work being visible.

## A blocker is a question, asked so it can be answered

Enough context to answer without opening four issues, in their language rather
than the diff's. "This adds a request to an address the site has not used
before - is that expected?" can be answered by somebody who does not read code,
which is the whole point.

Objectives waiting on a person carry `needs-human`. A session catching up leads
with those rather than with a summary of what it did last.

## Say what happens next, every turn

Including when the answer is that nothing is waiting on them and the next event
is an agent run finishing.

An objective moving on its own and an objective stalled look identical from
outside, and a person cannot tell which they are looking at without being told.
That is the failure this whole posture exists to prevent: not work going wrong,
but work going quiet.

## What a driver does not do

- **Decide scope.** A child that blocks twice means the issue was scoped wrong,
  and scoping is the person's call, not a third rewrite.
- **Write a merge policy on its own initiative**, on any objective, ever.
- **Promise a watch it cannot keep.** Session-side timers are not durable; if
  one is all that stands between the person and a report, say so rather than
  implying a vigil.
