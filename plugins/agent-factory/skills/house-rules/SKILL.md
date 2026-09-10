---
name: house-rules
description: The non-negotiable process rules for any repo built by the factory - acceptance criteria before work, tests before merge, an ADR for schema and dependency changes, and the three-strike rule. Use at the start of any agent run and whenever deciding whether a piece of work is ready to start or ready to merge.
---

# House rules

These apply to every repository this system touches. They are process, not preference. If a rule and a project convention disagree, the project convention wins on style and these rules win on process.

## Before work starts

Every child issue has acceptance criteria before anyone opens an editor. No criteria means the work is not ready, and starting anyway produces a diff nobody can judge. Ask for criteria instead of inferring them.

Every issue names one role. Work that needs two roles is two issues.

## Before merge

Tests before merge. Every acceptance criterion has a test that would fail if the criterion were violated. A criterion covered only by a manual check is not covered.

**Watch each new check fail before you trust it passing.** Break the thing it guards, see it go red, put the thing back. A check that has only ever been green is not evidence; it is a check that has never been tested, and the two are indistinguishable from the outside. This applies to the test harness as much as to the code - a fixture that silently stops working turns its negative cases green for the wrong reason, and those are the cases nobody re-reads.

The checks are the gate, and the gate is deterministic. Never skip, disable, or quarantine a test to get to green, and never widen a pull request to get around a failing check.

A pull request changes one issue's worth of code. Things noticed along the way become issues, not commits.

## Who merges

Merging stays outside every agent-run role. No role has `gh pr merge`, and none should: it is the one step that is irreversible, outward-facing, and impossible to review after the fact. A role's job ends at a pull request that is ready and a comment saying what needs a person.

**"A person" means attended, not human-fingered.** A session someone is driving - a chat, a terminal, an assistant working through their instructions - acts on that person's behalf and may merge for them. An unattended agent run may not, whoever configured it. The line is whether somebody is answerable for the decision at the time it is taken, not whether a human physically clicked.

That distinction is the whole rule, and it is why merging is not simply automated: a person who says "merge when green" has decided, in advance, that green is the standard they want applied. Automating it inside a role would move the decision to whoever wrote the role, months earlier, with no knowledge of this diff.

Before merging on someone's behalf, all of these hold. Any one failing is a reason to say so rather than merge:

- **Every acceptance criterion is covered by a check that actually ran.** A criterion marked verified by a check that never executed is the worst case here, because it ends the review - a reader who sees it ticked does not check it again.
- **The required checks are green**, and there are some. A pull request with no checks is not green; it is unmeasured.
- **The diff is the issue's worth of work** and no more. Something noticed on the way out is a new issue.
- **An ADR is present** if a schema, a data shape, or a dependency changed.
- **Anything the research or design named as a consequence** is handled or explicitly deferred in writing.
- **Nothing in the diff needs a decision only the owner can make.** Product behaviour, naming that will outlive the issue, a trade-off with no obviously right answer: those get asked, not merged.

Say which of these you checked. "Merged, green" is not a review; it is a status.

## Decisions

Any change to a schema, a data shape, or a dependency gets an ADR in `docs/decisions/`, in the same diff that makes the change. Four sections: context, decision, consequences, alternatives rejected. A dependency added without an ADR is a dependency nobody can remove later, because nobody knows why it is there.

## The three-strike rule

Three attempts on one issue means the issue was scoped wrong. It does not mean try harder. Stop, comment what was tried and how each attempt failed, label the issue `needs-decomposition`, and wait for a human.

The budget counts runs, not outcomes. A run that starts and then refuses - because a dependency is not merged, or because a command it needs is refused - has spent an attempt as surely as one that wrote the wrong code. It says "attempts" rather than "failures" for that reason, and the reason is not pedantry: an issue queued before its dependencies were merged arrives at the human with a third of its budget already gone and nothing to show for it. Check that the issues an issue depends on are merged, not merely labelled done, before applying the run label.

The same applies to a check that fails three times for three different reasons: the problem is the scope, not the fix.

## What agents never touch

Workflow files, CODEOWNERS, and branch protection are outside every agent's reach. A system that can rewrite its own gates has no gates. An agent that believes a workflow needs to change says so in a comment and stops.
