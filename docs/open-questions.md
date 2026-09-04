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

## 4. Two of the four roles have still never run

`researcher` and `orchestrator` are both proven under `v1.4.0`, on runs
33792437707 and 33843275814 respectively.

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

## 6. Should a run pin the model?

**What changed.** Every role file used to carry `model: opus` in its
frontmatter. In an Actions run that line does nothing: the agent is started by
a prompt telling it to follow the role definition, not through the subagent
mechanism that reads the frontmatter, so the action's own default applies. Run
33843275814 ran the "opus" orchestrator on `claude-sonnet-5` and
`claude-haiku-4-5`. The line has been deleted rather than left to describe
something that was not happening.

**What is unresolved.** Deleting it settles the honesty problem and leaves the
policy one: the caller has a `model` input that is passed through to
`--model`, and nothing sets it. So every role in every project runs on whatever
the action defaults to, and that default can change under you between runs
without anything in this repository moving.

The same deletion also gives up Opus for the roles used as interactive
subagents, where the frontmatter did work. Whether that matters depends on
whether `/decompose` run by hand should be a more careful thing than the same
role run in Actions - which is a real question and not obviously "no".

**How to answer it.** Compare a decomposition from a pinned run against an
unpinned one on the same objective, and see whether the difference is worth a
fixed cost per run.

**What changes.** Either the caller starts passing `model:` and the roles are
pinned in one place where a reader can see it, or this entry is deleted and the
default is documented as deliberate in `agent-run.yml`.
