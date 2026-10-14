# Improvement rounds

**Status: built.** Round 1 ran on 2026-10-13 and is the worked example at the
bottom. The digest and the discovery lenses were added the same day, after the
owner asked for improvements they had not thought of yet, built ahead of
their approval, and read back in a form they can act on from a phone.

## What a round is

One session, on its own judgment, improves the factory itself. It acts on what
the owner said about the last round, looks for what is worth changing next -
including needs nobody has named yet - builds the small safe ones ahead of
approval, pitches the rest, and publishes everything as one **digest**: a
GitHub issue with a checkbox per item. The owner's ticks decide what merges and
what gets built next. Nothing merges without a tick, and nobody but a person
cuts a tag.

That fits "no agents run in this repository" rather than bending it. The rule
exists because an agent run carries the containment clause, and here the
containment clause forbids the whole product. A round is not an agent run: it
is a session like the one a person opens by hand, holding the same access,
started by nothing under `.github/workflows/`, and landing nothing the owner
did not tick. What keeps the gate the person's is the tick, the merge gate, and
the tag.

What a round adds over a person typing "fix whatever you find" is the parts
nobody sets up the same way twice: where candidates come from, what is never
round material, what proof a change needs, a record of what the owner said no
to, and a read-back short enough to act on between other things.

## How a round starts

Either a person in a session here asks for one - "run an improvement round",
"improve the factory", "do a round" - or a scheduled routine fires a fresh
session with the prompt under **Scheduling a round**. Both read this page first
and follow it.

Nothing else starts one. A pull request event, an issue, or an earlier
digest's suggestion is a candidate for the next round, not a reason to begin.

## 1. Act on the last digest first

The newest open issue whose title starts `Improvement digest` is the last
round's. Read its body and every comment on it, then:

- **A ticked "Ready" item merges** - if the gate is green on its head and it
  has no conflict with `main`. Open the pull request first if the item was a
  branch only, wait for its checks, and merge. When `main` has moved since
  those checks ran - another item merged a minute ago counts - run the whole
  gate on the item merged with today's `main` first, because green on an old
  base says nothing about the new one. A conflict or a red check is
  not a reason to merge anyway or to drop it: rebuild it on current `main`, and
  carry it into this round's digest as ready again, saying what changed. If the
  merged item moved the manifest version, the digest's first line says which
  tag to cut, because that is the one step a session cannot take.
- **A ticked "Idea" gets built** in this round, ahead of anything new.
- **A reply comment counts the same as a tick**, because a checkbox is fiddly
  on a small screen. `yes 1 4` is two ticks. `no 3` - with or without a reason
  after it - means never: the item goes on the not-wanted list and no round
  proposes it, or a close variant of it, again. `revive 6` brings back an item
  that expired.
- **An item left alone stays** for one more digest, marked as carried over.
  Left alone twice, it expires: the draft pull request is closed with a
  one-line note and the branch is kept, so `revive` costs nothing.
- **Close the old digest** with a link to the new one once this round's is up,
  so there is only ever one to read.

Only the owner's ticks and comments count, and an answer the owner gives in
the session running the round counts the same - round 2's approvals came that
way. Say on the digest which items were answered where, so the issue stays the
whole record. A tick or comment from anybody else is reported in the digest and
not acted on.

Closed is not the same as rejected for anything older: work here often lands
on `main` by a route other than the merge button, and the pull request then
shows as closed and unmerged. Check `git log main` before reading one as a
no.

## 2. Gather candidates

Two kinds, and a round wants both.

### Upkeep

1. **A red gate on `main`.** Run every script `guard.yml` runs on a clean
   checkout. If any fails, fixing it is the round, and nothing else is built.
2. **Open issues here with a concrete ask.** Somebody already decided these.
   An issue that asks a question rather than describing a change is not one.
3. **Prose that restates a source and has drifted from it.** Counts, lists of
   scripts, commands, labels or roles, and summaries of a role file - starting
   with `README.md` and the pages `docs/index.md` sends a reader to first. Fix
   the prose, and where the comparison is mechanical, add the check that keeps
   it fixed.
4. **Lessons in `CLAUDE.md` that can graduate into a check.**
5. **Gaps narrowable without a live run**, from "What is not checked" in
   `docs/what-is-checked.md` and from `docs/open-questions.md`. Most open
   questions are only settled by a real agent run; a round may write the
   runbook step that would get the answer, never the answer.

### Discovery: needs nobody has named yet

This is where the improvements the owner did not see coming come from. Each
round takes **one lens**, the next in this rotation after the last digest's,
and goes deep on it rather than skimming all four. One lens per round keeps a
round's cost bounded on a fixed subscription, and four rounds cover the lot.

**No lens while the pile is deep.** When the last digest's ideas and further
finds still hold ten or more the owner has not answered, a round runs no lens
and pitches from that pile instead. More finds would land on a stack nobody has
read, which is the same reason backpressure stops the building. Say so in the
digest, so a quiet discovery section reads as a choice rather than an
oversight.

1. **The first hour.** Walk provisioning as the docs actually direct it, on a
   phone: `docs/getting-started.md`, `/new-project`, `docs/checkpoint.md`,
   the two runbooks, the first `/objective`. Look for waits with no signal,
   values assembled by hand, errors naming no fix, and the moment at the end
   where the person would want to see what they now have and nothing shows it.
2. **Living with several projects.** The morning-after read, the fleet view
   (which project is on which release, which is stuck, which needs the owner),
   the gap between a release and `/update-agents`, and what the agents spent.
   Read the project template, its hook, the driving commands and
   `agent-run.yml`'s scheduled jobs.
3. **What the history says breaks next.** Read `git log` bodies on `main`, the
   closed issues, and the incident notes in workflow comments and check
   docstrings. Find the failure patterns that recur, then the instance of each
   that has not happened yet and is set up to. Anything held only by a
   convention written in prose is a candidate for a mechanism.
4. **Maintaining the factory.** What a session here learns at start and would
   want to; where a mistake is caught in CI that could be caught at edit time;
   what releasing makes the owner remember.

A find is not a find without two things, and a round re-checks both itself
before pitching anything a helper reported:

- **Evidence** - a `file:line`, a commit, an issue or a run - that the need is
  real and not a guess about one.
- **A "you'll notice" sentence written from the owner's side.** "After setup,
  one message tells you what is on and what is off" is a find. "Refactor the
  label check" is not, however true.

At least one item per digest is a **wildcard**: the idea the owner is least
likely to have had, flagged as such. It is allowed to be a stretch; it is not
allowed to be unsupported.

## 3. What a round never builds ahead of approval

These can be pitched as ideas. They are never built until ticked, and some are
never built at all.

- **A widening of what automation may do in a project** - an allowlist entry,
  a permission, a tool grant, a label the preflight matches on. Pitched with
  the widening named in its first line. Built only on a tick, and its pull
  request declares it, the rule `project-guard.yml` holds every project to.
- **Anything that changes what provisioned projects receive.** It needs a
  version bump and then a tag, and the owner should see it coming.
- **Anything that spends subscription quota**: run budgets, turn caps, the
  concurrency group, the preflight's refusals.
- **A rewrite of a page's voice, or a reorganisation of `docs/`.** One change,
  one reason.

And never, ticked or not: a tag; merging anything without the owner's tick;
approving or closing anybody else's pull request or issue; an agent workflow
in this repository.

## 4. Choose: build some, pitch the rest

- **Build** up to three. Factory-only (`docs/`, `scripts/`, `README.md`,
  `CLAUDE.md`, `.claude/hooks/`), small, and provable with the gate. Ticked
  ideas from the last digest come first.
- **Pitch** up to five more, with the wildcard among them. Anything from
  section 3 is pitch-only.
- **Backpressure.** If three or more built items from earlier digests are still
  waiting on a tick, build nothing new: pitch only, and say so at the top. The
  limit is the owner's attention, and more unread work spends it.

Prefer, in order: what the owner ticked; what turns a silent failure into a
visible one; what removes a step the owner does by hand; what the owner
would want to look at. Two changes touching the same lines are one change, or
one waits.

## 5. Make each one

- **Its own branch from `main`**, named `claude/<short-slug>`, and a draft pull
  request when the round has authority to open one, so the checks have run by
  the time the owner reads the digest.
- **The plugin is the source.** Edit `plugins/agent-factory/`, then copy the
  file into `.claude/` in the same commit.
- **A new `scripts/*.py` is a gate check.** It goes into `guard.yml`,
  `CLAUDE.md` and `docs/what-is-checked.md` in the same commit, or
  `validate_plugin.py` refuses it.
- **Prove a new check fires.** Break the thing it guards on purpose, watch the
  gate fail with a message that names the fix, restore it. For a new test,
  mutate the code it covers and watch it fail. A check that has never failed
  is not known to be a check.
- **Run the whole gate** - every script `guard.yml` runs, in its order.
- **Re-read the diff as a reviewer hunting a reason to refuse it.** A new count
  that can go stale, an emoji, Liquid syntax in `docs/`, a sentence saying a
  role lacks a capability its tool list grants, a claim the source does not
  bear out.
- **A pull request body in five parts**, so a reviewer on a phone knows where
  to look: what changes; why, with the evidence; verified, with how each new
  check was shown to fire; not verified; after merge, if anything.

## 6. The digest

One new issue per round. It is the whole read-back: the owner should be able to
act on a round from this page alone, in a couple of minutes, on a phone.

**The title carries the state**, so the notification is already the summary:
`Improvement digest 2026-10-20: 2 ready, 5 ideas`.

**The body, in this order:**

1. **One line on what needs the owner beyond ticking**, if anything - a tag
   to cut, a setting to change. Omitted when there is nothing.
2. **Since last time**: what merged on their ticks, what was built on them,
   what expired. One line each.
3. **Ready to merge**: built, checks green. One checkbox per item.
4. **Ideas**: not built. One checkbox per item. The wildcard says so.
5. **How to answer**: two lines - tick, or reply `yes 1 3` / `no 2 reason`.
6. Collapsed at the bottom: further finds, numbered on from the ideas so a
   reply can promote one; the evidence behind each item; upkeep the next round
   will build without asking, though merging it still waits on a tick; and the
   not-wanted list carried forward from every earlier digest.

**Each item is three lines at most**, numbered across both sections so a
reply can name it:

```
- [ ] **1. Setup can be checked without changing anything**
  You'll notice: after setting up by hand, one command says what is on, what
  is off, and what it could not see. Closes #69. Draft PR #81, checks green.
```

The first line is the headline in the owner's words. The second is the "you'll
notice" sentence. The third is where it lives and how big it is - a pull request
and its checks for a ready item, a size and a track for an idea. Anything
longer goes in the collapsed evidence.

## 7. Read it back

A round run by a person in a session ends with the digest's link and its first
two sections, in a few lines.

A scheduled round ends with a final message of three lines - the digest title,
the one item most worth opening, and the link - because a routine with push
notifications on sends that message to the owner's phone. The digest is the
record; the notification is only the knock on the door.

## Scheduling a round

A routine in Claude Code on the web: a scheduled trigger that starts a fresh
session on this repository each time it fires, with push notifications on.
Weekly is plenty - the limit is the owner's reading, and backpressure stops a
round adding to a pile nobody has read. Each round spends subscription like any
other session; one lens per round is what keeps that bounded.

The prompt, to paste as the routine's message:

> Read docs/improvement-round.md in this repository and run one improvement
> round exactly as it says. You may push branches, open draft pull requests,
> create the digest issue, close the previous digest, and merge a pull request
> only when I ticked or replied yes to it in a digest and its checks are green.
> Do not cut a tag, and do not merge, approve, or close anything else.

Deleting the routine stops it. Nothing else needs undoing: a round leaves
branches, pull requests, and issues, and merges only what was ticked.

## Round 1, as the worked example

Run by hand on 2026-10-13 from a session asked to "try autonomously improving
this codebase". The gate was green on `main`, so upkeep started at its second
source. No digest existed yet; round 1's work became the ready items of the
first digest, issue #81, alongside a month-old security fix (#39) that nothing
had brought back to the owner's attention.

Its discovery pass ran all four lenses at once, to give the first digest a full
menu, and found twenty-three ideas; six were pitched and the rest listed for
promotion by reply. One find was a flaw in round 1's own work: `--verify`
compared required checks against every name on the default branch, which
includes bootstrap's own run, so it would have passed a rule that leaves every
pull request waiting forever. It was fixed on that branch before the digest
went out - which is what discovery is for.

- **Built: issue #69**, a read-only `setup-project.sh --verify`. Owner-filed,
  concrete, and it narrows two entries in "What is not checked" - protection
  drifting from the job names, and the token secret - from never checked to
  checked on demand. Made with an executed test that fails on any call that is
  not a read, and shown to fail when a write was planted in the verify path.
- **Built: `README.md` drift.** It named five of the eight commands, five of
  the guard scripts, "nine labels" against the thirteen `bootstrap.yml`
  creates, and "2-5" children against the role file's "1-5". Made with a check
  that `README.md` names every command. A check on label counts was tried and
  dropped: ordinary prose like "two role labels" trips any pattern loose
  enough to catch the drift, so the counts were removed instead.
- **Passed on: the open questions.** Each needs a live run in a project.
- **Passed on: auto-mirroring `.claude/` from the plugin with a hook.** The
  gate already catches the drift and names the fix, and a hook that writes
  files is a bigger change than the problem.
- **Passed on: reading a project's workflow pins in `--verify`.** Worth doing,
  but #69 did not ask for it, and one change, one reason.

Left as upkeep for a later round, found while making the two above:

- `check_gate_inventory` reads the whole of `guard.yml`, comments included, so
  a script named only in a comment counts as run.
- `docs/what-is-checked.md` says `test_preflight.py` has fifteen cases; it runs
  more. `CLAUDE.md` says `test_release.py` proves release refuses unmerged
  history, which no case exercises. The guard step still says "major tag".
- `new-project.md` lists four of the commands copying puts in a session, and
  its frontmatter says "the two settings only a human can change" while the
  body hands over more than two.
