---
name: driving-an-objective
description: How an interactive session drives an objective it filed or was pointed at - adopting the merge policy, reporting to the person, surfacing blockers they can answer, and knowing what only they can do. Use whenever an objective is in play, a child reaches review, a pull request is waiting, or a session is catching up on what happened while nobody was watching.
---

# Driving an objective

A session that files an objective, or is pointed at one, is that objective's
driver and the person's window into it. Nobody else is watching. The agents in
the repository do their own work and report on the parent issue; nothing else
turns that into something a person can act on.

Being the window is mostly not a watching job. Most turns it means reviewing a
child's pull request and merging it under the objective's policy - see **Adopt
the merge policy** - which is unblocking the next agent run, not a favour done
for the person. The one thing that policy never covers, and that driving never
delegates to the person's absence, is a hard blocker: a decision only they can
make. See **A blocker is a question** for how to raise one so it cannot be
dropped, and **How to wake** for making sure the driver is there to raise it.

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

**Say it on the issue, not only in this turn.** A blocker spoken only in chat
is real for as long as someone is reading that turn; the label and a comment on
the issue are what outlive the session, and what a later one - this one
resumed, a fresh one, or one woken by `/check-in` - actually reads first. A
hard blocker sitting only in scrollback is indistinguishable, from outside,
from one that was never raised.

## How to wake

Session-side timers are not durable - see **What a driver does not do** - so
what a driver is waiting on decides how it gets woken, not whether to set a
reminder.

- **Waiting on a pull request.** Subscribe to it as soon as it exists, for
  every child of the objective still open - whatever the session's environment
  calls that (a `subscribe_pr_activity` tool, where there is one). A fresh
  session has no memory of an earlier one's subscriptions, so re-subscribing on
  every check-in costs nothing. This is what turns a CI failure or a review
  comment into a wake, instead of a fact that sits unread until someone happens
  to look.
- **Waiting on the person.** There is nothing to schedule. Write the blocker
  down per **Say it on the issue, not only in this turn**, and stop - the wake
  is them reading it.
- **Waiting on something nothing here can tell you about** - a deploy on its
  own clock, a third-party pipeline, an environment that promotes on a
  schedule - is the only case where a durable reminder is legitimate, and even
  then it should wake a session that re-reads the objective's actual state
  rather than trusting the reminder's own text. Say plainly that a timer is
  standing in for a person, per **Promise a watch it cannot keep**.

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
  implying a vigil. See **How to wake** for what to use instead.
