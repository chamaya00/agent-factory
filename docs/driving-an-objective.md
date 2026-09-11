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

Start from what is actually true, rather than from what would be convenient:
**a driver holding a person's credentials is indistinguishable from that
person.** A driver session files issues as the account it authenticates as, and
in the setup this was designed against that is the owner's own account, not a
bot. So no check can separate "the person told the driver to write this" from
"the driver decided to write it" - not by author, not by edit history, and not
by any token a different harness could present instead. Any design that claims
otherwise is describing a check it does not have.

That is not the failure worth preventing, though, and the one that is happens
to be cleanly separable. The dangerous case is an **unattended** run - the
orchestrator waking on a label event with no person in the conversation at all -
granting itself authority to merge. Runs like that authenticate as the agent
identity App, and drivers do not. So the boundary is drawn there, and it is
drawn in terms of identities rather than of any particular harness:

**Enforced.** A `Merge policy` line is honoured only when the objective's body
was last edited by an account that is not the agent identity App. A driver
authenticating as the person passes whatever tool it is built from; anything
running as the App is refused. The orchestrator and every other role are
additionally told never to write the line, and to ignore one that is present,
because it is not addressed to them - a rule that can graduate into a preflight
check rather than staying prose.

**Stated, and unenforceable by construction.** A driver writes the line only as
the direct result of a person answering the question, never on its own
initiative. There is no mechanism behind this and there should not be a pretence
of one. What makes it a different risk from the unattended case is structural
rather than cryptographic: a driver is, by definition, mid-conversation with a
person, and an unattended run is not.

**Recorded, for legibility rather than security.** The line carries who set it
and when - `Merge policy: green (set by @owner, 2026-09-11)` - so the provenance
is readable at a glance. This is self-reported and forgeable by the same account
that writes the line. It is worth having because it makes a surprising policy
easy to notice and question, and it is worth not overselling.

The line may appear anywhere in the objective's body, matched line-anchored;
`/objective` writes it in a consistent place near the top so it is visible
without scrolling.

### What the policy does not authorise: failure

A `green` policy authorises merging. It says nothing about what to do when work
fails, and the two must not be conflated - the person decided that green is a
standard they trust, not that the driver should decide on their behalf what a
second block means.

So when a child blocks a second time, after the orchestrator's one corrective
pass, **that child stops and comes to the person** with what was tried and how
each attempt failed. No third rewrite, no fourth attempt in a different coat:
the three-strike rule already says that three attempts means the issue was
scoped wrong, and scoping is not a driver's call.

**Its siblings keep moving.** Children that are ready and passing still merge
under the policy, because one badly scoped child is not evidence about the
others and freezing the whole objective turns a local problem into a global
stall. The objective gets `needs-human` for the blocked child while the rest of
it continues.

The exception worth naming: if a second block suggests the *objective* was
scoped wrong rather than the child - the same finding surfacing from more than
one child, or a dependency nobody spotted at decomposition - then merging
siblings is premature and the driver says so instead of continuing. That is a
judgment call, which is exactly why it comes to a person.

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
4. **Shows the drafted body and waits for a yes before filing.** One
   keystroke, and it is the last beat of the refinement conversation rather
   than a separate approval step. It buys the thing that is expensive to fix
   later: a mis-scoped objective that is already queued has started spending
   runs, and children that arrive at a person with a third of their attempt
   budget gone is a failure this system has already had.
5. **Files it, labels it `objective` and `agent:queued`.**
6. **Then drives it**, per the driver section below.

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

One flat label, not a suffixed family. The label answers "does anything need
me?" from the issue list; the orchestrator's status comment answers "what?" in
prose, which it already does well, and duplicating that into the label set buys
filtering at the cost of three labels to provision and a suffix the orchestrator
can pick wrongly. Creating labels is still one of the handful of steps a person
does by hand, and that argues for the small set.

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

Four of the five questions this document opened with have been answered, and
the answers are folded into the sections above rather than recorded here - an
entry is deleted when it is answered, not annotated. What remains is the one
thing the design knowingly does not solve.

1. **Should the driver have its own identity, separate from the person's?**
   Everything above accepts that a driver authenticating as the owner is
   indistinguishable from the owner, and draws its enforceable boundary around
   the agent identity App instead. That boundary is real and it stops the
   failure that matters, but it leaves a gap: nothing can tell a policy line the
   person dictated from one a driver wrote unprompted, because both arrive from
   the same account.

   Giving the driver its own identity - a second App, or a token that is not the
   owner's - would close it. Then "the owner edited this" and "a driver edited
   this" are separable facts, the enforced rule can require the former, and the
   behavioural rule stops being load-bearing.

   The cost is a new identity to create, store, and rotate, on a system whose
   setup already has several steps only a person can do, and it buys protection
   against a driver that has gone wrong while holding credentials the person
   handed it deliberately. That is a real risk but not obviously this system's
   biggest one, which is why this is a question rather than a decision. It
   should be settled before the policy mechanism is relied on anywhere the
   consequences of a wrong merge are worse than they are today.
