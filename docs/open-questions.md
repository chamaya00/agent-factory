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
read-only. The branch `claude/agent-run-tool-allowlist` fixes that. These are
what the fix could not settle.

Reading that run log is the fastest way to get context on all of this. The
`SDK options:` block near the top prints the exact `allowedTools` array the
agent started with, which is how the problem was found in the first place.

---

## 1. Does `--allowedTools` merge with the action's defaults, or replace them?

**Why it matters.** The action needs its own tools to work: the sticky progress
comment, and the git commands it uses to land a commit. If our allowlist
replaces its defaults rather than adding to them, we have taken those away, and
the symptom is not an error - it is a run that does the work and then cannot
report or commit it.

**What was done.** The common set in `agent-run.yml` re-lists
`mcp__github_comment__update_claude_comment` and the git commands, so the
allowlist is safe either way. Redundant if it merges.

**How to answer it.** Trigger any agent run and read the `SDK options:` block in
the job log. If `allowedTools` contains our entries *and* entries we never
passed (`Glob`, `LS`, `mcp__github_ci__*`, the `git-push.sh` path), it merges.
If it contains only ours, it replaces.

**What changes.** If it merges, delete the re-listed common entries and the
comment above them - they are noise. If it replaces, the comment stays, and
check whether the action's `git-push.sh` wrapper is now unreachable; the plain
`Bash(git push:*)` grant is the fallback, but the wrapper may do something the
plain command does not.

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

## 3. Can the researcher reach the web at all?

**What is known.** The failed run's post-step environment showed
`DISALLOWED_TOOLS: WebSearch,WebFetch` - the action disallows both by default in
tag mode. `researcher` declares both, and `designer` declares `WebFetch`.

**What was done.** Both are in the allowlist for those roles. If the action's
disallow wins, they are absent - no worse than before, but the researcher is
then a role that can only read the repository it is already in.

**How to answer it.** Run the researcher on a real issue and see whether it
fetches anything, or read `DISALLOWED_TOOLS` in the post-step env of that run.

**What changes.** If disallow wins, the routes are the action's `settings`
input, which takes a Claude Code settings JSON with `permissions.allow` /
`permissions.deny`, or passing `--disallowedTools` explicitly in `claude_args`.
Prefer `settings`: overriding the disallow list wholesale would also drop
whatever else the action puts there for a reason. If neither works, say so in
`researcher.md` rather than leaving a role that declares tools it never gets.

---

## 4. A tooling failure should not burn an attempt

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

## 5. None of this is proven

The allowlist fix is unverified end to end. It was checked by running the shell
step for all four roles and by the guard in `scripts/validate_workflows.py`, but
no agent has actually run with it.

The proof is re-running the smoke test: label a child of #3 in
`new-project-agents` `agent:queued` and watch whether the engineer writes files,
runs the tests, and opens a pull request. Until that happens, treat step 3 of
`docs/smoke-test.md` as untested rather than passing.

---

## 6. Three children, or two to five?

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
