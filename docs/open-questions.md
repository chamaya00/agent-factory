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

The `SDK options:` block near the top of a run log prints the exact
`allowedTools` array the agent started with, and the `"type": "result"` block
near the bottom prints turns, cost, denials, and the models actually used.
Between them they have settled most of the questions that used to be on this
page.

---

## 1. What are the four permission denials?

Every successful run so far reports `permission_denials_count: 4`. The
researcher on #4 reported four. The orchestrator on #11 reported four. Nothing
in either run failed, and the log does not say which tools were refused,
because the action hides the agent's turns unless `show_full_output` is on.

**What the second data point rules out.** This page used to guess the
researcher was reaching for `gh pr create`, which only the engineer is granted.
That cannot be the explanation any more: the orchestrator has no `gh pr` grant
of any kind, does a completely different job with a different allowlist, and
landed on the same number. Two roles with different grants producing an
identical count points at something systematic - the action's own harness
probing a fixed set of tools each run - rather than at either role reaching
past itself.

**Why it is still worth knowing.** If it is the harness, the number is noise
and should be written down as noise so nobody investigates it a third time. If
it is not, then something is being refused in every run regardless of role, and
that is worth more attention than a per-role slip would have been.

**How to answer it.** Re-run any role with `show_full_output: true` and read
which calls were refused. One run answers it for good.

**What changes.** Either this entry gets deleted and a sentence goes into
`agent-run.yml` next to the allowlist saying the four denials are expected, or
the allowlist gains whatever is actually being refused.

---

## 2. `gh` commands, or the GitHub MCP server?

**The situation.** Every role definition names `mcp__github__*` tools. The
action does not start a GitHub MCP server, so those names do not resolve in a
run. The fix grants the same capability as scoped `gh` commands instead.

**Why `gh` was chosen.** It uses the CLI and the App token this workflow already
proves work in three other steps, and it adds nothing to the critical path of a
plan with a fixed budget. The alternative - a `--mcp-config` pointing at
`ghcr.io/github/github-mcp-server` - would make the run match the role
definitions exactly, but it adds a container pull to every run, and the hosted
server at `api.githubcopilot.com/mcp/` documents PAT and OAuth only, not App
installation tokens.

**The cost that turned out not to exist.** This entry used to say `gh` has no
sub-issue command, so children would link to their parent by body reference
rather than as real GitHub sub-issues, and that native linking would need
`gh api graphql` and reopen everything the scoped allowlist closes. Run
33843275814 disproves that. #12 and #13 both came out of it carrying a real
`parent_issue_url` pointing at #11, and #13 carries a native `blocked_by` of 2.
Real hierarchy and real dependencies, from the scoped allowlist as it stands.

**What is genuinely unresolved.** Only the vocabulary argument is left: the
role definitions name tools that do not exist in a run, and a reader has to
know that the prompt translates them. That is a real cost, just a much smaller
one than a missing feature. Closing it means either starting the MCP server or
rewriting the `tools:` lines to name what a run actually gets - and the second
breaks the same files' use as interactive subagents, where the MCP names are
the correct ones.

**What would change the answer.** Wanting one tool vocabulary across the
interactive and Actions contexts, badly enough to pay a container pull per run.
Do not reopen it for sub-issues; that part works.

---

## 3. A tooling failure should not burn an attempt

**What happened.** Run 33787451101 failed for a configuration reason, and the
`Hand back to a human` step labelled the issue `agent:blocked` on `job.status`
alone. The attempt marker comment counts toward the three-attempt cap, so a run
that never got to attempt anything consumed a third of the issue's budget. The
agent said as much in its own comment and was right.

**Why it was not fixed with the allowlist.** The three-strike rule is a design
decision, not a bug: "three failed attempts means the issue was scoped wrong" is
load-bearing, and making the workflow judge *why* a run failed is exactly the
kind of cleverness that ends with a system that never refuses anything.

**The shape of a fix, if you want one.** Distinguish "the agent ran and did not
succeed" from "the run never started properly" - a preflight or setup failure
could remove its own attempt marker rather than leaving it. Keep the default
biased toward counting the attempt: a rule that is easy to talk your way out of
is not a rule.

**Still live.** #3 carries one spent attempt for a run that never did anything,
and will hit the cap after two real ones.

---

## 4. Some roles have still never run

`researcher` and `orchestrator` are both proven under `v1.4.0`, on runs
33792437707 and 33843275814 respectively.

`analyst` has not run at all: it was added in `v1.29.0` and no objective has
yet been split in a way that queues one, so every claim its role file makes
about what a run produces is untested.

`designer` and `engineer` have not run. The engineer is the one to watch,
because it is the only role that needs `Bash(npm run:*)` to work and the only
one whose output has to pass the gate rather than just exist. A role that
writes files nobody runs is a much easier thing to get right than one that has
to make `npm run test` green.

Until an engineer run lands a pull request that passes CI, treat the engineer
step of `docs/smoke-test.md` as untested rather than passing.

**How to answer it.** Both roles run in phase 8 as it now stands: the objectives
there produce a design document and a published site, so a full pass exercises
three of the four roles rather than one. That is deliberate - a runbook that
only ever ran the orchestrator was not testing the loop, it was testing the
first step of it.

---

## 5. Is 40 turns enough for the engineer?

**What is known.** The cap was raised from 15 to 40 in `v1.4.0` because 15 was
below the floor. Both roles that have run since finished close to the new cap:
the researcher took 35, the orchestrator took 33. Neither writes code, runs a
test, or reacts to a failing check.

**Why that is uncomfortable.** The engineer does all three, and a run that hits
`--max-turns` fails the whole job even if the work itself was finished - which
then labels the issue `agent:blocked` and spends one of its three attempts on
something that was not a scoping problem at all. That is question 3 arriving by
a second route.

**How to answer it.** Run the engineer on the smallest child of phase 8's first
objective and read `num_turns` in the result block. `docs/smoke-test.md` asks
for that number in its report, and asks for the smallest child to be queued
first for exactly this reason: the answer is wanted before a larger child spends
an attempt discovering it.

**What changes.** If it lands near 40, raise the cap in the template and in
`agent-run.yml`'s default. Do not raise it pre-emptively: the cap exists
because a Pro subscription is a fixed budget, and a cap nobody has hit is not
evidence of anything.

---

## 6. Is a pinned model worth its cost for the other four roles?

**What is settled.** A run resolves its model per role, in the `Resolve the
model for this role` step of `agent-run.yml`, beside the allowlist for the same
role. The researcher is pinned to Opus there; the other four take the action's
default, which is a choice rather than an omission. The caller's `model` input
still overrides all of it for a whole repository.

That replaces the arrangement this entry used to describe, where the roles
carried a `model: opus` line that did nothing in an Actions run and the caller's
input was never set by anything. The reasoning for the researcher's pin is in
the comment on that step, at the length it deserves.

**What is still open, and it is the same measurement.** The pin is a bet. It was
argued from the shape of the role - the only one whose output is judgement all
the way down, and the only one whose failure mode is a document that reads fine
- and not from two runs anybody compared. The other four were left on the
default by the same untested reasoning running the other way.

**How to answer it.** Run one objective twice, once with the caller's `model`
input set and once without, and read the two sets of artifacts side by side. The
orchestrator is the cheapest role to test this on, because a decomposition is
small, and the analyst is the most interesting, because its contract is the
thing a later measurement is built on and a weak one fails silently in exactly
the way the researcher's does.

**What changes.** Either another role joins the researcher in the case block
with its own comment saying what the comparison showed, or this entry is
deleted and a line goes into that step saying the default was tested and kept.
Do not widen the pin without the comparison: "judgement matters here too" is an
argument that fits every role, which is why it cannot be the reason for any of
them.

---

## 7. One pending run, and a wave of two loses one

**What is known.** A concurrency group holds exactly one pending entry, and a
third arrival cancels the one already waiting. `agent-run.yml` puts that group
on the agent job, so preflight always runs and only real runs contend - but two
*real* runs still contend, and the older pending one is cancelled while pending,
having executed no step. The issue keeps `agent:queued` and nothing runs it,
with nothing in any log to say so.

**What was done about it.** The orchestrator queues exactly one child at a time,
which removes the only automated source of a two-at-once wave. That is a
convention in the role definition, not a mechanism: a human labelling two issues
`agent:queued` in the same minute still loses one, and so would any future caller
that queues a wave.

**Why it was left.** Fixing it properly means either giving up the repo-wide
one-at-a-time guarantee that protects a fixed subscription, or adding a retry for
the queued-but-idle state - a second path through the one place in this system
where a bug spends the subscription. Neither is obviously right, and the
automated path that used to hit this no longer does.

**How to answer it.** Label two ready issues `agent:queued` within a few seconds
and watch whether both run. That confirms the shape; the decision after it is a
judgement, not an observation.

**What was done about it, and what is left.** The second option, halfway. A
`stale-queue` job now ticks on a schedule and comments on any issue carrying the
run label with nothing running it. It does not re-raise anything: re-queueing
from a watchdog is a second path into the one place where a bug spends the
subscription, and that risk has not changed. So the loss is no longer silent,
which was the part that made it dangerous, and recovery is still a human
removing and re-adding a label.

What is genuinely still open is whether that is enough. If the report turns out
to fire often, the answer is to loosen the group - per-issue rather than
per-repo, with the budget protected some other way - rather than to let a
watchdog start spending. If it never fires, this entry can go.

---

## 8. Do `app-render` and `contrast` work inside a run?

**What is known.** Both ship in the project template, both are named in the
role files, and both were exercised by hand before they shipped: `contrast`
against six known pairs including the WCAG boundary cases, `app-render` against
a built page whose stylesheet and script load from root-absolute paths - the
exact case that made `design-render` useless for a built page, photographed
correctly over a served origin and incorrectly over `file://`.

**What is not known.** Whether a role can run them. Nothing in this repository
runs an agent, so the allowlist entry that grants them - `Bash(./scripts/*)`,
which both roles already held - has never been exercised against these two
names, and `app-render` additionally runs whatever `BUILD_CMD` a project puts
in it. That inner command is checked against the role's allowlist rather than
the script's grant, and a project that fills it in with something no role may
run has a script that works by hand and refuses in a run. The script's own
header says so; nothing enforces it.

**How to answer it.** Provision or update a repository, fill in `BUILD_CMD` and
`SERVE_DIR`, and give the designer a visual issue. One run answers both: the
pull request either carries pictures of the built page or names the refusal.

**What changes.** Either this entry is deleted and the fact goes into the
smoke-test runbook as a step that has been seen to pass, or the allowlist gains
whatever the inner build command needs and the script's header stops being the
only thing saying so.

---
