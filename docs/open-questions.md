# Open questions

Things the factory does not know yet, written for whoever picks them up next -
including a Claude session starting cold.

Each entry says what is known, what was done about it, how to get the answer,
and what changes once you have it. An entry that gets answered is deleted, not
annotated: the answer belongs in the code or in a comment next to the thing it
explains, and a register of settled questions is just another place to go
stale.

Nothing here is a task list. These are the places where the system is running
on an assumption that has not been tested.

---

## Where these came from

The first agent run the factory ever made - `orchestrator` on issue #3
("Favorites list") in `chamaya00/new-project-agents`, step 1 of
`docs/smoke-test.md`. [Run
33787451101](https://github.com/chamaya00/new-project-agents/actions/runs/33787451101).

It posted a correct decomposition and then could not create the child issues,
because `agent-run.yml` passed no tool allowlist and the action's default set is
read-only. `v1.4.0` fixes that, and [run
33792437707](https://github.com/chamaya00/new-project-agents/actions/runs/33792437707)
- `researcher` on #4 - is the first run to work under it. These are what is
still open after that.

Reading either run log is the fastest way to get context. The `SDK options:`
block near the top prints the exact `allowedTools` array the agent started
with, which is how the original problem was found and how two of the questions
that used to be on this page were settled.

---

## 1. What were the four permission denials?

Run 33792437707 succeeded and reported `permission_denials_count: 4`. Nothing
in it failed, and the log does not say which tools were refused, because the
action hides the agent's turns unless `show_full_output` is on.

**The likeliest explanation** is the researcher reaching for `gh pr create`,
which only the engineer is granted. Its own checklist ticked off "commit, push,
open PR" when what it actually produced was the action's Create-PR link, so it
may have tried the command first. That is a harmless denial if so.

**Why it is still worth knowing.** Four silent refusals per run is either a role
asking for something it should have, or a role asking for something it should
not - and the two look identical from here. A count with no names is not a
signal anyone can act on.

**How to answer it.** Re-run any role with `show_full_output: true` and read
which calls were refused.

**What changes.** If a role is being refused something its own definition
declares, the allowlist is wrong. If it is reaching past its role, the prompt
is. If it is `gh pr create` from a docs role, nothing changes except this entry
being deleted.

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

**The cost of the choice.** `gh` has no sub-issue command, so children link to
their parent by body reference rather than as real GitHub sub-issues. Native
linking needs `gh api graphql`, and granting that reopens everything the scoped
allowlist closes.

**What would change the answer.** Wanting real sub-issue hierarchy, or wanting
one tool vocabulary across the interactive and Actions contexts. If you switch,
the role definitions stop being aspirational and the `gh` grants come out.

---

## 3. A tooling failure should not burn an attempt

**What happened.** The run failed for a configuration reason, and the
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

---

## 4. Three of the four roles have still never run

The `researcher` is proven: run 33792437707 on `new-project-agents` #4 wrote two
ADRs and a research doc, reached the web, verified its own acceptance criteria
with `git diff`, and handed back at `agent:review`. It took 35 turns, which is
also why the cap is 40 and not 15.

`orchestrator`, `designer` and `engineer` have not run under this allowlist. The
engineer is the one to watch, because it is the only role that needs `Bash(npm
run:*)` to work and the only one whose output has to pass the gate rather than
just exist. A role that writes files nobody runs is a much easier thing to get
right than one that has to make `npm run test` green.

Until an engineer run lands a pull request that passes CI, treat step 3 of
`docs/smoke-test.md` as untested rather than passing.

---

## 5. Three children, or two to five?

`docs/smoke-test.md` step 1 says the orchestrator "creates 3 child issues".
`orchestrator.md` allows two to five, and the real run produced five, with a
stated reason: the project had no UI framework, router, or `dev` script, so "a
separate page" contained a framework decision that could not be folded into a
feature issue without producing criteria nobody could check.

So the doc and the role disagree, and the run followed the role. Decide which is
wrong. If the count in the doc is just an illustration, say so there, because as
written it reads like a pass condition and invites judging a decomposition by
counting it rather than by reading the criteria - which is the failure the same
paragraph warns against.
