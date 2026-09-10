---
description: Review the pull requests an objective is waiting on, merge the ones that pass the house rules' merge gate, and say plainly why for any that do not. The explicit form of "merge when green".
---

Merge what is ready, on the owner's behalf.

`$1` is the objective issue to work, for example `#49`. If it is empty, take
every open pull request opened by an agent run and treat them as one batch.

This command exists because "merge when green" is a real standing instruction
and was being carried in conversation rather than anywhere a later session
could find it. A person driving a session may merge for them - see **Who
merges** in the house-rules skill - and this is the shape that decision takes,
so that what was checked is written down next to what was merged.

## 1. Find what is waiting

Read the objective and its children. For each child at `agent:review`, find its
pull request. A child with no pull request is not waiting on you - it is
waiting on a run, and that is a different problem.

If nothing is waiting, say so in one line and stop. Do not go looking for
something to merge.

## 2. Judge each one against the gate

The gate is the list in the house-rules skill under **Who merges**, and it is
not a formality. Read the diff. Read the criteria. Check that the checks ran.

The one that catches people is a criterion marked verified by a check that
never executed - `tests/check.sh` green does not mean the criterion has a check
in it, only that the checks it does have passed. Open the file. Find the check
the issue names. Confirm it exists and would fail if the behaviour regressed.

Anything the research or design named as a consequence, rather than a feature,
is worth looking for specifically. That is the failure mode that ships: every
criterion satisfied and the hole still there, because the criteria were written
before the consequence was known.

## 3. Merge, or say why not

Merge the ones that pass. For each, say which parts of the gate you checked -
not "green", which is a status rather than a review.

For any that do not pass, leave it open and say exactly what is missing, on the
pull request. A pull request left open with no comment is indistinguishable
from one nobody looked at.

Where a diff needs a decision only the owner can make - product behaviour, a
name that will outlive the issue, a trade-off with no obviously right answer -
put the question to them and merge nothing. Being driven by someone is not the
same as being able to answer for them.

## 4. Say what happens next

A merge is an event: it wakes the objective, which queues whatever the merge
made ready. So finish by saying what you expect to happen, and whether the
objective is now met or waiting on another child.

If you merged the last child, the objective is finished but not closed -
closing a parent objective is the owner's, and the orchestrator will say so
too.
