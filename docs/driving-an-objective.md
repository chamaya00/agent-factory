# Driving an objective

**Status: proposal.** Nothing here is built. One decision is already made (the
merge policy, below); the rest is written to be argued with and amended before
any of it ships. Delete this banner when the last piece lands.

## The problem

The system describes how work moves between agents. It says nothing about the
session sitting in front of a person.

Read `templates/project/CLAUDE.md`: "How work moves" covers objectives, labels,
the orchestrator, and which role does what. There is no section about the
interactive session, because the session was never given a role. So the person
types one out, every time, in some variation of:

> I want this and that. File an objective and kick off the orchestrator run.
> Watch it and merge anything that looks good.

Three separate things are being hand-specified there, and all three are
artifacts this repository should own rather than leave to prose:

1. **Filing an objective** is a command that does not exist. `/decompose` runs
   the orchestrator against an issue that is already filed; nothing writes one.
2. **Kicking off the run** is applying `agent:queued`, which the person has to
   know about.
3. **Watching and merging** is a posture, held only in the context of the
   session that was told it, and lost the moment that session ends.

The third is the expensive one, and it fails in a way that looks like nothing
happening.

## The split this design turns on

"Watch the run and merge for me" reads like one job. It is two, and a session is
good at exactly one of them.

**Deciding** - does this pull request pass the gate, is this child blocked, what
does the person actually need to be told? This needs judgment against the house
rules. A session is the right place for it and there is no substitute.

**Persisting** - staying available across the hours between a run finishing and
a person looking. A session is the wrong place for this, and the evidence is
direct: during `new-project-agents-v3#66` a session was asked to watch the run,
scheduled itself a check-in, and went silent for four hours. The in-session
scheduler it used was session-scoped and was discarded; the durable one was
withdrawn from that session mid-run. Neither failure was visible from inside.

In the same four hours the orchestrator woke four times, read the state
correctly each time, and posted an accurate status - on GitHub's
infrastructure, with no session alive anywhere.

**So the durable half already works.** What keeps getting lost is the deciding
half, because the only place it has ever lived is the context of one session.
Every piece below follows from that: move the posture into the repository where
a cold session picks it up for free, and stop asking a session to be a cron.

## Decided: the merge policy is recorded on the objective

The house rules already allow a session to merge for someone:

> A person who says "merge when green" has decided, in advance, that green is
> the standard they want applied to this work. That decision holds while the
> session that received it is working.

The clause doing the damage is "while the session that received it is working".
Session ends, authority ends, and the next session has to be told again - which
is the boilerplate this document exists to remove.

The decision is durable; only its storage was ephemeral. So store it durably:

```
Merge policy: green
```

One line in the objective issue's body. Rules:

- **Absent means ask.** No line, no authority. It fails closed, so an objective
  filed by hand behaves exactly as today.
- **`green`** means a session may merge that objective's children once each
  passes the full gate in the house rules' "Who merges" - not merely once CI
  is green. The `/ship` review is unchanged; what changes is that a session no
  longer needs a person present to act on it.
- **`ask`** is the explicit form of the default.
- **It is scoped to one objective.** It authorises merging that objective's
  children and nothing else. There is deliberately no repository-wide setting:
  the point is a person deciding about a piece of work, not once about all
  work forever.
- **Revoking it is editing the issue.** No command, no state anywhere else.
- **The six items in "What a revert does not undo" still stop and ask**,
  whatever the line says. A credential, a widened permission, a new outbound
  destination, a deletion, a first-of-its-kind dependency, or a change the
  pull request does not mention: the policy was about green, and those are not
  that. This is not a caveat, it is the boundary of the whole mechanism.

### Who may write the line

This is where the mechanism could quietly become the thing the house rules
exist to prevent. If the orchestrator could write `Merge policy: green` on the
objective it is working, the factory would be authorising its own merges, and
"the loop closing on itself" would be back with a written record that looks
like consent.

So: **the line is only honoured when a person put it there.** An objective's
body is attributable - GitHub records who authored and who last edited it. A
session writes the line only as the direct result of a person answering the
question, and never on its own initiative.

Whether that is enforced or merely stated is the main open question below.

## The four pieces

### 1. `/objective <rough idea>` - a command that does not exist yet

Collapses the opening prompt to one line. What it does, in order:

1. **Refines the idea with the person first.** This is the part that should
   stay interactive - the difference between a good objective and a bad one is
   mostly made here, before anything is filed. Read the repository, ask what is
   genuinely ambiguous, propose the scope back in a sentence.
2. **Drafts the objective** in the shape the orchestrator reads well: the
   problem stated as what a person sees, what already exists, what done looks
   like, and a "for the orchestrator" section naming the traps.
3. **Asks the merge policy question, once**, and writes the answer into the
   body as the line above.
4. **Files it, labels it `objective` and `agent:queued`.**
5. **Then drives it**, per the driver section below.

The refinement step is why this is a command and not a workflow. Everything
after step 1 is mechanical; step 1 is the whole value.

### 2. A `## Driving an objective` section in the project template

The fix for "my sessions are not tuned to be this system's driver". It belongs
in `templates/project/CLAUDE.md` rather than in a hook or a setting, for one
reason that decides it: **CLAUDE.md is read by every session in the
repository, including a cold one opened tomorrow that knows nothing about
today.** That is precisely the "I check back later" case, and no amount of
session-side machinery covers it.

It should say, in substance:

- A session pointed at an objective is that objective's driver and the person's
  window into it. Nobody else is going to look.
- **Read the merge policy on the objective and adopt it.** Where it says
  `green`, merging children that pass the gate is the job, not a favour to ask
  permission for.
- **Report in prose.** The orchestrator already maintains the status table on
  the parent issue; repeating it in the terminal is not a report. Say what
  changed, what it means, and what is next.
- **A blocker is a question, asked so it can be answered.** Enough context to
  answer without opening four issues, in the person's language rather than the
  diff's.
- **On catching up**, lead with where the objectives stand, not with a summary
  of the last session.
- **End every turn saying what happens next and what needs a person.**

### 3. A `needs-human` label

Today "waiting on you" is prose inside a status comment on the parent issue.
You have to open the issue to find out, which means you have to already suspect
it.

As a label it is visible in the issue list, filterable, and answerable in one
query by a session catching up. The orchestrator applies it when an objective
is genuinely waiting on a person - a decision only they can make, a child at
`needs-decomposition`, a second block after a corrective pass - and clears it
when the objective is moving again.

Note what this does *not* include once `Merge policy: green` is recorded: a
pull request waiting to be merged is no longer waiting on a person. That is the
point of the policy line, and `needs-human` should not be applied for it.

### 4. The orchestrator's done-report names what to look at

Its report currently ends at which children merged and whether the default
branch is green. Both are facts about the repository, and neither answers the
question a person actually has, which is what is different now.

When an objective is met, the report should also name **what a person can now
open, and what changed from a user's point of view** - the URL, the page, the
command. The smoke test already takes this position for the system as a whole
("judged by opening a URL rather than by reading a diff"); this applies the
same standard to every objective.

## What this deliberately does not do

**No workflow that merges without a session.** It was considered and rejected.
It would deliver the autonomy asked for, and it would remove the last human
decision from the chain - the exact failure the house rules name. The policy
line gets most of the way there while keeping a person deciding, per objective,
in a place that is attributable and revocable.

**No repository-wide merge setting.** Same reason. A per-objective decision is
a person choosing about a piece of work they understand; a global one is a
person choosing once, about work that does not exist yet.

**No session-side scheduler as load-bearing infrastructure.** A session may
poll while a person is present and it is useful when it works. It must never be
the thing a report depends on, because when it fails it fails silently, and the
observed cost of that is four hours of apparent nothing.

## Open questions

Each needs an answer before the piece it belongs to ships. An entry is deleted
when it is answered, not annotated.

1. **Is "only a person may write the merge policy line" enforced, or only
   stated?** Stated is one sentence and trusts the roles. Enforced means
   something reads the issue's edit history and refuses to honour a line last
   touched by the agent identity - real protection against the one failure that
   matters here, at the cost of a check that has to know which account is the
   bot. Recommendation: enforce it. This is the hinge the whole mechanism turns
   on, and it is the kind of rule that is obeyed right up until the run that
   does not.

2. **Does `/objective` file the issue, or file it and queue it?** Filing and
   queueing in one step is what the person asked for. It also means a
   mis-scoped objective starts burning runs before anyone has re-read it.
   Possible answer: queue immediately by default, show the drafted body first
   and let them say no.

3. **Where does the merge policy line live in the body - anywhere, or a fixed
   position?** Anywhere is friendlier to a human editing it later. A fixed
   position is greppable and unambiguous. If question 1 is answered
   "enforced", this probably has to be fixed-position.

4. **Should `needs-human` carry the reason?** One label is simple.
   `needs-human:decision` versus `needs-human:decomposition` is filterable but
   multiplies the label set, and the provisioning step that creates labels is
   already one of the four things a person has to do by hand.

5. **What happens to an objective whose policy is `green` when a child blocks
   twice?** The policy authorises merging, not deciding what to do about
   failure. Presumably it still stops and asks - but that should be written
   down rather than inferred.
