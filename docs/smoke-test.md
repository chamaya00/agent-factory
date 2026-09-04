# Phase 8: smoke test the full loop

Run this on the throwaway repo from phase 7, only after that gate is boring.

## The objective

File this as an issue, titled "Favorites list", and label it `objective`:

> Users should be able to save items to a favorites list and see them on a
> separate page. Should survive a page refresh. No accounts - local storage is
> fine.

Nothing runs yet. `objective` alone does not start anything: the run label does,
and only a human applies it.

## The six steps, and what to watch for

**1. The orchestrator comments with a plan and creates its child issues.**

Label the objective `agent:queued`. The orchestrator should comment its plan
first, then create the children.

The count is not a pass condition. `orchestrator.md` allows between two and
five, and both real runs sat at the ends of that range with a stated reason -
five on #3 because the project had no UI framework, two on #11 because it
needed no schema or dependency decision. Judge the split by reading the
criteria, not by counting the issues.

Watch for: children with acceptance criteria that are checkable rather than
aspirational, exactly one role label each, and a link back to the parent. A
child reading "favorites work well" is a failure of this step even though an
issue got created - go and read the criteria, not just the count.

Watch for: grandchildren. There should be none. Anything needing a further split
should be labelled `needs-decomposition` and left alone.

**2. You label one child `agent:queued`.**

Pick the one with no dependencies. The plan comment should say which those are.

**3. The engineer opens a pull request, checks pass, a preview URL appears.**

Watch for: whether the tests it wrote actually map onto the acceptance criteria,
one to one. Tests that pass without testing the criteria is the failure mode
here, and it looks identical to success on the checks tab.

Watch for: the issue moving through `agent:running` to `agent:review` on its
own. If the labels do not move, the App token or the labels are wrong, not the
agent.

**4. You comment a revision, it pushes a fix.**

Comment on the pull request starting with `@claude`, asking for one specific
change - the empty state, say. Without the trigger phrase nothing happens, by
design.

Watch for: a new commit on the same branch, not a new pull request. And watch
the attempt counter - this is attempt 2 of 3 on that issue.

**5. You merge.**

**6. `/retro` proposes a one-line memory entry as a pull request.**

Run `/retro` from a Claude session against the repo. It should open a pull
request touching only `.claude/memory/`, with a line naming something specific
that happened during steps 1 to 5.

Watch for: a lesson with no incident behind it. "Write clear tests" is a
preference, not a lesson, and it should not survive. Watch for the file staying
inside 40 lines - `project-guard` fails the pull request if not.

## Reporting back

For each of the six: worked, or needed hand-holding and what exactly.

Then, separately, three things that are worth more than the pass or fail:

- **How many attempts did each issue take.** Anything hitting 3 means the
  orchestrator scoped it wrong, and the fix belongs in the orchestrator's
  role definition or in that repo's memory, not in trying again.
- **How much of the diff you had to actually read.** If you read all of it, the
  gate is not doing its job yet and phase 7 needs revisiting.
- **What you found yourself typing more than once.** That is the next command.

## The likely failure modes

Ranked by how often they bite, so you can recognise them rather than debug them:

1. `CLAUDE_CODE_OAUTH_TOKEN` missing from this repo. Every run fails
   immediately at auth. Secrets are per repo.
2. "Allow Actions to create and approve pull requests" off. The run succeeds and
   no pull request appears.
3. Acceptance criteria too vague, so the engineer builds the wrong thing and it
   passes its own tests. Fix the orchestrator's output, not the engineer.
4. The run label applied to the parent objective again after the split, which
   re-runs the orchestrator and produces duplicate children.
5. Required check names in branch protection drifting from the job names, so
   nothing is actually required any more.
