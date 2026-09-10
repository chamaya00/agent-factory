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

**And read what the sabotage actually printed, not what your harness said about it.** The run that proves a check has teeth can itself be broken, and it breaks quietly: a patch string the shell expanded before the patcher saw it, a pattern matched against output that indents differently, a substitution that found nothing and reported nothing. Every one of those prints a clean verdict about a check it never exercised. Twice in one sitting a sabotage sweep here reported that nothing was caught, and both times the checks were working and the sweep was not.

The tell is that a broken harness looks exactly like diligence - a tidy table of results, produced by a program that did nothing. So on any sweep, open one case's real output and confirm the failure says what you expect. One is enough; the failure modes are shared across the sweep, so the one you read vouches for the others.

The checks are the gate, and the gate is deterministic. Never skip, disable, or quarantine a test to get to green, and never widen a pull request to get around a failing check.

A pull request changes one issue's worth of code. Things noticed along the way become issues, not commits.

## Who merges

Merging stays outside every agent-run role. No role is granted `gh pr merge`, and none should be: it is the one step that is irreversible, outward-facing, and impossible to review after the fact. A role's job ends at a pull request that is ready and a comment saying what needs a person.

**A session carrying someone's instruction merges on their behalf.** A person who says "merge when green" has decided, in advance, that green is the standard they want applied to this work. That decision holds while the session that received it is working, whether or not they are reading it happen. Watching is not what makes the merge legitimate - the instruction is, and so is being able to revoke it, and so is a merge that points back at the session that made it.

Do not confuse being unwatched with being self-directed. What must not happen is the loop closing on itself: the factory splitting an objective, building it, merging it, and choosing what comes next with no decision from a person anywhere in the chain. That is why roles do not merge - not because someone should be looking, but because a role's instruction comes from the factory rather than from an owner. The rule lives in the tool grant rather than here, so a run that talks itself into merging still cannot.

The difference an absent owner does make is that you cannot ask them anything. So anything that would have been a question becomes a pull request left open with the question written on it. That is a better outcome than a guess, and it is waiting for them when they come back.

Before merging on someone's behalf, all of these hold. Any one failing is a reason to say so rather than merge:

- **Every acceptance criterion is covered by a check that actually ran.** A criterion marked verified by a check that never executed is the worst case here, because it ends the review - a reader who sees it ticked does not check it again.
- **The required checks are green**, and there are some. A pull request with no checks is not green; it is unmeasured. Know what green covers, too: structural checks say the shape is right, never that the behaviour is correct.
- **The diff is the issue's worth of work** and no more. Something noticed on the way out is a new issue. Read the diff, not the description of the diff - they are different acts, and only one of them catches a change nobody wrote down.
- **An ADR is present** if a schema, a data shape, or a dependency changed.
- **Anything the research or design named as a consequence** is handled or explicitly deferred in writing.
- **Nothing in the diff needs a decision only the owner can make.** Product behaviour, naming that will outlive the issue, a trade-off with no obviously right answer: those get asked, not merged.

Say which of these you checked. "Merged, green" is not a review; it is a status.

**A merge is not finished when the pull request closes.** Every check in that list is scoped to the pull request, and a pull request's checks stop being true the moment it merges - they ran on a commit that no longer exists anywhere except in the merge. What runs afterwards is what decides whether the work reached anyone: a deployment, a publish, a post-merge suite. Watch the merge commit until that settles, and say what it did.

Where it cannot be watched to the end - a pipeline measured in hours, an environment that promotes on its own schedule - say what you expect and where the answer will appear, and look at the next time you touch the repository. The point is that somebody is carrying the question, not that it is answered inside the minute.

A project once ran nineteen hours and eight merges on a failing deployment, serving a build from before any of them, while every pull request in that window was honestly green. Nobody was wrong about anything they checked. Nobody had checked the thing that mattered.

### What a revert does not undo

The gate above is mostly about whether the work is finished. It is not about whether the work is safe, and a diff can be exactly the issue's worth of work and still do something that outlives being reverted. Read every diff for these six. Any one of them means stop and ask, not merge - even under a standing instruction, because the standing instruction was about green, and this is not that.

1. **A credential.** A key, token, password, or connection string, in product code or a fixture either way. Reverting does not unpublish it; it has to be rotated.
2. **Anything that widens what the automation may do.** A `permissions:` block, a new secret reference, a trigger that runs against a fork's code, a third-party action, an action pinned to a tag that can move. This one has a check behind it: the project guard fails a pull request whose diff widens any of these unless the body carries a line starting `Privilege change:` saying what and why. It does not forbid the change, only doing it quietly - and it exempts nobody, because a pull request merged under a standing instruction is authored by a maintainer and that is the case it is for.
3. **A new outbound destination.** A request, form action, script source, or embedded resource pointing at a host the project does not already use. This one ships to real readers the moment it merges.
4. **Destruction.** Deleted data, deleted files the issue did not name, rewritten history, a force-push.
5. **A dependency from outside the ecosystem already in use.** Adding the first one of anything is a category change, not a feature, and the ADR that documents it is not a substitute for asking.
6. **A change the pull request does not mention.** Unexplained work is the tell for an honest mistake and for an agent that read an instruction from somewhere it should not have. Roles take their input from issue text, and issue text is written by whoever can comment.

Ask about these in the owner's language, not the diff's. "This adds a request to an address the site has not used before - is that expected?" can be answered by someone who does not read code, which is the point: the check exists to turn a rare risky change into a question they can actually answer, not to make them review the patch.

## Decisions

Any change to a schema, a data shape, or a dependency gets an ADR in `docs/decisions/`, in the same diff that makes the change. Four sections: context, decision, consequences, alternatives rejected. A dependency added without an ADR is a dependency nobody can remove later, because nobody knows why it is there.

## The three-strike rule

Three attempts on one issue means the issue was scoped wrong. It does not mean try harder. Stop, comment what was tried and how each attempt failed, label the issue `needs-decomposition`, and wait for a human.

The budget counts runs, not outcomes. A run that starts and then refuses - because a dependency is not merged, or because a command it needs is refused - has spent an attempt as surely as one that wrote the wrong code. It says "attempts" rather than "failures" for that reason, and the reason is not pedantry: an issue queued before its dependencies were merged arrives at the human with a third of its budget already gone and nothing to show for it. Check that the issues an issue depends on are merged, not merely labelled done, before applying the run label.

The same applies to a check that fails three times for three different reasons: the problem is the scope, not the fix.

## What agents never touch

Workflow files, CODEOWNERS, and branch protection are outside every agent's reach. A system that can rewrite its own gates has no gates. An agent that believes a workflow needs to change says so in a comment and stops.
