# Open questions

Things the factory does not know yet, written for whoever picks them up next -
including a Claude session starting cold.

Each entry says what is known, what was done about it, how to get the answer,
and what changes once you have it. An entry that gets answered is deleted, not
annotated: the answer belongs in the code or in a comment next to the thing it
explains, and a register of settled questions is just another place to go
stale.

Deleting it is only half the move, and the half that goes wrong on its own. An
answer that lands nowhere is lost the moment the entry goes, and the next
session re-derives it from the same run logs a month later. So an entry is not
settled until its answer exists in one of three places, and the commit that
deletes the entry says which one it was:

- A check in `scripts/`, when the answer is mechanical. Always the best of the
  three, because it is the only one that stays true without anyone reading it.
- A comment next to the thing it explains, when the answer is a reason someone
  editing that file needs at the moment they edit it.
- A line in the Lessons section of `CLAUDE.md`, when it is neither. The weakest
  of the three, and the one to revisit later for whether it can graduate into
  the first.

Nothing here is a task list. These are the places where the system is running
on an assumption that has not been tested.

---

## Where these came from

Three runs in `chamaya00/new-project-agents`, all worth reading before picking
anything up here:

- [33787451101](https://github.com/chamaya00/new-project-agents/actions/runs/33787451101)
  - `orchestrator` on #3, the first run the factory ever made. Posted a correct
  decomposition and then could not create the children, because `agent-run.yml`
  passed no tool allowlist and the action's default set is read-only. `v1.4.0`
  fixes that.
- [33792437707](https://github.com/chamaya00/new-project-agents/actions/runs/33792437707)
  - `researcher` on #4, the first run to work under `v1.4.0`. Wrote two ADRs and
  a research doc, reached the web, verified its own criteria with `git diff`.
  35 turns.
- [33843275814](https://github.com/chamaya00/new-project-agents/actions/runs/33843275814)
  - `orchestrator` on #11, the run that proves issue creation from inside a
  workflow. Commented a plan, then created #12 and #13 with checkable criteria,
  one role label each, and a recorded dependency on the sibling objective's
  open framework issue rather than a duplicate of it. 33 turns, $0.63.

Those were runs of the `agent-run` workflow, which ADR 0005 retired. Several
entries that used to be here were questions about that workflow - its tool
allowlist, its turn cap, its single pending slot - and were deleted with it:
the thing each one asked about no longer exists. Runs now start from a session
through `/dispatch`, and what a run did is in its report and on its issue.

---

## A failed start should not burn an attempt

**What happened.** Run 33787451101 failed for a configuration reason and was
labelled `agent:blocked`. The attempt marker counts toward the three-attempt
cap, so a run that never got to attempt anything consumed a third of the
issue's budget.

**Where it stands now.** `/dispatch` books a run - label and marker comment -
before the role starts, on purpose: a booking that survives a dead run is what
lets the next session hand it back. The same ordering means a session that dies
before the role does anything still spent the attempt.

**Why it was not simply fixed.** The three-strike rule is load-bearing - "three
failed attempts means the issue was scoped wrong" - and making the dispatcher
judge *why* a run failed is the kind of cleverness that ends with a system that
never refuses anything.

**The shape of a fix, if you want one.** Distinguish "the role ran and did not
succeed" from "the run never started" - `/dispatch` could strike its own marker
when the subagent or child session errored before its first tool call. Keep the
default biased toward counting the attempt.

---

## No objective has run end to end in sessions

`researcher` and `orchestrator` were proven under the workflow runner, on runs
33792437707 and 33843275814. Under sessions, the pieces were checked one at a
time on 2026-10-15 - a role subagent reaches the GitHub tools, a child session
reaches GitHub and git, and session pull requests are authored by the owner -
but no objective has yet gone from `/objective` to merged.

`analyst`, `designer` and `engineer` have not completed a run under either
runner. The engineer is the one to watch: it is the only role whose output has
to pass the gate rather than merely exist.

**How to answer it.** Phase 8, `docs/smoke-test.md`, as it now stands: its
objectives produce a design document and a published site, so a full pass
exercises three of the roles rather than one.

---

## Is a pinned model worth its cost for the other four roles?

**What is settled.** `/dispatch` runs the researcher on `opus` and every other
role on the dispatching session's own model, and says so in its **Model**
paragraph.

**What is open.** The pin is a bet, argued from the shape of the role - the
only one whose output is judgment all the way down, and whose failure mode is a
document that reads fine - and not from two runs anybody compared. The other
four were left on the default by the same untested reasoning running the other
way.

**How to answer it.** Run one objective twice, with and without a role pinned,
and read the two sets of artifacts side by side. The orchestrator is the
cheapest to test, because a decomposition is small; the analyst is the most
interesting, because its contract is what a later measurement is built on.

**What changes.** Another role joins the researcher in that paragraph with a
line saying what the comparison showed, or this entry is deleted and the
paragraph says the default was tested and kept.

---

## Do `app-render` and `contrast` work inside a run?

**What is known.** Both ship in the project template, both are named in the
role files, and both were exercised by hand before they shipped: `contrast`
against six known pairs including the WCAG boundary cases, `app-render` against
a built page whose stylesheet and script load from root-absolute paths -
photographed correctly over a served origin and incorrectly over `file://`.

**What is not known.** Whether they work in the container a session's role runs
in. `app-render` needs a headless browser and a static server the image is asked
for rather than given, and runs whatever `BUILD_CMD` a project puts in it.

**How to answer it.** Set up a repository, fill in `BUILD_CMD` and
`SERVE_DIR`, and give the designer a visual issue. One run answers both: the
pull request either carries pictures of the built page or names what refused.

**What changes.** Either this entry is deleted and the fact goes into the
smoke-test runbook as a step seen to pass, or the scripts' headers say what a
session's container lacks and how a project supplies it.
