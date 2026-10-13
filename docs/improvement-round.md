# Improvement rounds

**Status: built.** Round 1 ran on 2026-10-13 and is the worked example at the
bottom.

## What a round is

One session, on its own judgment, improves the factory itself: it picks up to
three things worth changing, makes each one on its own branch, proves each one
with the whole gate, hands them over for review, and writes down what it
looked at and passed on. A person still merges, and a person still cuts the
tag.

That fits "no agents run in this repository" rather than bending it. The rule
exists because an agent run carries the containment clause, and here the
containment clause forbids the whole product. A round is not an agent run: it
is a session like the one a person opens by hand, holding the same access,
started by nothing under `.github/workflows/`, and landing nothing without a
merge somebody chose to make. What keeps the gate the person's is the merge
and the tag, and a round touches neither.

What a round adds over a person typing "fix whatever you find" is the parts
nobody sets up the same way twice: where candidates come from and in what
order, what is never round material, what proof a change needs before it is
handed over, and a record the next round reads so it does not rediscover what
this one already passed on.

## How a round starts

Either a person in a session here asks for one - "run an improvement round",
"improve the factory", "do a round" - or a scheduled routine fires a fresh
session with the prompt under **Scheduling a round**. Both read this page first
and follow it.

Nothing else starts one. A pull request event, an issue, or an earlier round's
report suggesting a follow-up is a candidate for the next round, not a reason
to begin it.

## 1. Read what earlier rounds left

- **The round log.** An open issue titled `Improvement rounds`, one comment per
  round. Read the last two comments: what was deferred, and what they said to
  look at first.
- **Round pull requests still open.** If two or more are waiting on review,
  report that and stop. Unreviewed output is the bottleneck, and a third pull
  request spends the person's attention rather than saving it. This is the
  backpressure that makes a weekly schedule safe to leave running.
- **Round pull requests that were closed.** Closed is not the same as rejected
  here: work in this repository often lands on `main` by a route other than
  the merge button, and the pull request then shows as closed and unmerged.
  Before reading one as a rejection, check whether its change is on `main`
  (`git log main --grep '#<number>'`, or look for its files). One that was
  closed and did not land is a rejection. Do not propose it again without
  evidence the earlier round did not have, and name that evidence.

## 2. Gather candidates, in this order

1. **A red gate on `main`.** Run every script `guard.yml` runs on a clean
   checkout. If any fails, fixing it is the round, and nothing else is picked.
2. **Open issues here with a concrete ask.** Somebody already decided these;
   the round implements them. An issue that asks a question rather than
   describing a change is not one of these.
3. **Prose that restates a source and has drifted from it.** Counts, lists of
   scripts, commands, labels or roles, and summaries of a role file - starting
   with `README.md` and the pages `docs/index.md` sends a reader to first. The
   sources are `guard.yml`, `plugins/agent-factory/commands/`, `bootstrap.yml`,
   the template's `agent-factory.json`, and the role files. Fix the prose, and
   where the comparison is mechanical, add the check that keeps it fixed.
4. **Lessons in `CLAUDE.md` that can graduate into a check.** The goal that
   section states for itself.
5. **Gaps that can be narrowed without a live run.** The "What is not checked"
   section of `docs/what-is-checked.md`, and entries in `docs/open-questions.md`.
   Most open questions are only settled by a real agent run in a real project,
   and those are not round material - a round may write the runbook step that
   would get the answer, never the answer.
6. **Friction in what a person runs or reads.** An error that names no fix, a
   handover with no URL, output nobody can act on from a phone, a command that
   does something irreversible on a typo.

## 3. What a round never picks

- **A widening of what automation may do in a project** - an allowlist entry,
  a permission, a tool grant, a label the preflight matches on - unless an
  issue from the owner asks for exactly that. Then the pull request says so in
  its body, the same rule `project-guard.yml` holds every project to.
- **Anything that spends subscription quota**: run budgets, turn caps, the
  concurrency group, the preflight's refusals. The open questions on these are
  judgment calls already written down as judgment calls.
- **A release.** No tag, which a session cannot push anyway, and no version
  bump on its own. A bump rides with a change projects must pick up, in the
  same pull request, per the standing rules in `CLAUDE.md`.
- **Merging, approving, or closing** anybody's pull request or issue.
- **A rewrite of a page's voice, or a reorganisation of `docs/`.** One change,
  one reason; a reviewer can say yes to that from a phone.
- **An agent workflow in this repository**, of any kind.

## 4. Choose

At most three per round, and one or two is normal. Prefer, in order: what
somebody already decided over what the round found; a fix that lands with the
check that keeps it fixed over a fix alone; what a person runs or reads first
over what nobody opens. Two changes that would touch the same lines are one
change, or one of them waits.

For every candidate not picked, keep one line on why. Those go in the report,
and they are what stop the next round spending its first hour on the same
search.

## 5. Make each one

- **Its own branch from `main`**, named `claude/<short-slug>`.
- **The plugin is the source.** Edit `plugins/agent-factory/`, then copy the
  file into `.claude/` in the same commit. `validate_plugin.py` names which
  side is the source if they disagree.
- **A new `scripts/*.py` is a gate check.** It goes into `guard.yml`,
  `CLAUDE.md` and `docs/what-is-checked.md` in the same commit, or
  `validate_plugin.py` refuses it.
- **Prove a new check fires.** Break the thing it guards on purpose, watch the
  gate fail with a message that names the fix, restore it. For a new test,
  mutate the code it covers and watch it fail. A check that has never failed
  is not known to be a check, which is the same argument
  `docs/proving-the-gate.md` makes about branch protection.
- **Run the whole gate** - every script `guard.yml` runs, in its order - and
  keep the tail of each one's output for the pull request.
- **Re-read the diff as a reviewer hunting a reason to refuse it.** A new count
  that can go stale, an emoji, Liquid syntax in `docs/`, a sentence saying a
  role lacks a capability its tool list grants, a claim the source does not
  bear out. Fix what you find before pushing, not after.
- **A commit message in this repository's voice**: what changes and why, with
  the evidence.

## 6. Hand it over

Push each branch. Open one pull request per branch when the round was started
with authority to - a scheduled round's prompt carries it; a person who typed
"run a round" in a session may want the branches only, so ask once if they did
not say.

Each pull request body has the same five parts, so a reviewer on a phone knows
where to look:

- **What changes**, in a few lines.
- **Why**, with the evidence: `file:line`, the issue, the run.
- **Verified**: the gate's output tail, and how each new check was shown to
  fire.
- **Not verified**: anything only a live run or a person's account can prove.
- **After merge**: the owner steps, if any - the tag when the manifest moved,
  `/update-agents` in the projects that should take it.

The round never merges, including its own work.

## 7. Report

One comment on the round log issue - creating the issue on the first round,
when the round may file issues:

- the date, and each improvement with its pull request;
- each candidate considered and passed on, one line each with the reason;
- what the next round should look at first.

If a person is in the session, the same in a few lines to them, ending with
what is now waiting on them.

## Scheduling a round

A round can run on a schedule as a routine in Claude Code on the web: a
scheduled trigger that starts a fresh session on this repository each time it
fires. Weekly is plenty. The limit is review, not generation, and step 1 stops
a round from adding to a queue nobody has read.

The prompt, to paste as the routine's message:

> Read docs/improvement-round.md in this repository and run one improvement
> round exactly as it says. You may push branches, open one pull request per
> improvement, and comment on or create the "Improvement rounds" issue. Do not
> merge, approve, or close anything.

A scheduled round spends the same subscription as any other session. Deleting
the routine stops it, and nothing else needs undoing: every round leaves only
branches, pull requests, and comments.

## Round 1, as the worked example

Run by hand on 2026-10-13 from a session asked to "try autonomously improving
this codebase". The gate was green on `main`, so step 2 started at its second
source.

- **Picked: issue #69**, a read-only `setup-project.sh --verify`. Owner-filed,
  concrete, and it narrows two entries in "What is not checked" - protection
  drifting from the job names, and the token secret - from never checked to
  checked on demand. Made with an executed test that fails on any call that is
  not a read, and shown to fail when a write was planted in the verify path.
- **Picked: `README.md` drift.** It named five of the eight commands, five of
  the guard scripts, "nine labels" against the thirteen `bootstrap.yml`
  creates, and "2-5" children against the role file's "1-5". Made with a check
  that `README.md` names every command. A check on label counts was tried and
  dropped: ordinary prose like "two role labels" trips any pattern loose
  enough to catch the drift, so the counts were removed instead.
- **Passed on: the open questions.** Each needs a live run in a project. Not
  round material.
- **Passed on: auto-mirroring `.claude/` from the plugin with a hook.** Real
  friction, but the gate already catches the drift and names the fix, and a
  hook that writes files is a bigger change than the problem. Worth an issue
  if the mirror keeps costing a CI cycle.
- **Passed on: reading a project's workflow pins in `--verify`.** A pin with
  no tag behind it fails every check, so it is worth reading - but #69 did not
  ask for it, and one change, one reason.

Left for round 2, found while making the two above and kept out of them:

- `check_gate_inventory` reads the whole of `guard.yml`, comments included, so
  a script named only in a comment counts as run.
- `docs/what-is-checked.md` says `test_preflight.py` has fifteen cases; it runs
  more. `CLAUDE.md` says `test_release.py` proves release refuses unmerged
  history, which no case exercises. The guard step still says "major tag".
- `new-project.md` lists four of the commands copying puts in a session, and
  its frontmatter says "the two settings only a human can change" while the
  body hands over more than two.
