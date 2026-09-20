# Driving an objective

**Status: built, in 1.21.0.** All four pieces and the merge policy shipped; the
open questions that opened this document were answered in review and folded into
the sections below. What remains open is the last section, and it is the one
thing the design knowingly does not solve. This document is now the reasoning
behind what exists rather than a proposal.

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

## Addendum: how a driver actually wakes (1.26.0)

The line above said what not to do. It did not say what to do instead, and the
gap kept getting refilled with exactly the forbidden thing - a driver setting
itself a reminder because nothing else was named.

`driving-an-objective`'s "How to wake" section names the substitute: what a
driver is waiting on decides the mechanism, not a habit of scheduling
something. A pull request gets a subscription, so its own activity - a CI
failure, a review comment - wakes the next check instead of a session polling
for it. A wait on the person is not scheduled at all; the blocker goes on the
issue, per the skill's "Say it on the issue, not only in this turn", and the
wake is the person reading it. Only a wait with no signal available anywhere -
something outside the pull request's own activity - falls back to a durable
reminder, and even that wakes a session that re-reads the objective's actual
state rather than trusting what the reminder says.

`/check-in` is the fixed shape catch-up takes, whatever woke it: what is
waiting on the person first, then the state of every child, then act under the
policy. It exists as a command rather than three lines retyped from memory for
the same reason `/objective` does - so the same procedure runs regardless of
who or what invoked it.

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

## Addendum: a question is a third terminal state (1.28.0)

The label set above had two terminal states for a child and both are verdicts on
the run: `agent:review` says it went fine, `agent:blocked` says it did not.
Neither says "it went fine and somebody has to decide something before this
merges", and that turned out to be a common and expensive case.

A role that hit one had three options and all were bad. Block itself, and spend
one of the issue's three attempts on a run that had actually succeeded. Write
the question in a comment, where the orchestrator's next status rewrite buries
it - the parent picture is *replaced* on every wake by design, so anything held
only in its prose has a lifetime of one child finishing. Or pick silently. Over
an entire design objective across two repositories, every role picked silently,
every time, and nobody found out until the work was merged.

So `agent:needs-input`, and the thing to understand about it is where the
question actually lives:

- **The comment holds the question.** It stays where it was asked, beside the
  work it is about, which is also where a driver reading pull requests will
  meet it.
- **The label holds the fact.** A label survives every comment rewrite and can
  be queried, which prose cannot.
- **The parent issue holds neither - it renders them.** The orchestrator rebuilds
  its "waiting on you" section every wake by reading the children's labels. That
  is what makes "replace, do not append" safe: the orchestrator displays
  questions and never stores them, so a wake that forgets to re-read shows
  nothing rather than losing something.

A role raises one by writing `<!-- agent-factory:needs-input -->` into its issue
comment. The run's handback greps for it and applies the label. No role gained a
label grant for this: the marker is a string any role could already write, and
the handback step already held the token and already edited labels. It is
compared against a timestamp taken just before the agent starts, so a question
answered on attempt one is not re-raised by attempt two.

It rides *alongside* `agent:review` rather than replacing it, costs no attempt,
and stops nothing except the merge. The role is told to ask the question and
then finish the work anyway under its own recommendation - a question with a
delivered recommendation attached is a far better question than the same words
with nothing to look at.

And it is the one thing `Merge policy: green` does not cover. The person
delegated the gate; this is what they kept. A driver relays it and waits, and
must not answer it on their behalf - a driver holding someone's credentials can
always produce an answer that sounds like theirs, which is exactly why it may
not.

## Addendum: the driver is a role, and the brief is a contract (1.30.0)

Everything above designs the driver as a *window*. Re-read the verbs in the
original skill and they are all transmission: report, surface, relay it and
wait. The only judgment the driver exercised was the merge gate in
`house-rules`, and every item on that gate is a fact about process - criteria
covered by a check that ran, required checks green, an ADR where one is owed,
the diff scoped to its issue. There was nowhere in the system to say *this
passes the gate and I am still not taking it*.

That was fine while the driver and the roles were the same kind of reader. It
stopped being fine once the driver became the most capable reader in the loop
and the only one that sees across children. A window does not need judgment.
A person relying on one session for whether the work is any good does.

So two changes, and they are the two ends of one channel.

**The driver owns technical judgment.** The skill now draws the line by
subject matter rather than seniority: what the product does, who it is for and
what it is called are the person's; whether what came back will hold is the
driver's. It runs the merge gate and then reads the same diff a second time
asking a different question, because a diff can satisfy every process fact and
still be work nobody should keep - criteria that were satisfied and were the
wrong criteria, a test that would also pass if the behaviour regressed, a
number asserted rather than computed, a specification the next role will have
to guess at. The discipline that keeps this from becoming churn is one rule: a
rejection names what would change your mind. The failure in the other
direction is the quiet one - a driver that has never rejected anything is not
a driver with a good team, it is a gate nobody has tested.

It also gets a reading budget, because reading everything is how a driver
arrives at the diff with no attention left. Brief and diff always; issue and
document when those do not add up; the run log rarely, in three named cases,
and say why.

**The orchestrator owes a brief, not a status.** A supervision run on an
objective in a downstream repository produced three comments, opened with a
checklist of the skills it had read, and put the single most important
sentence it had - that a designer had hand-computed some contrast ratios and
flagged them as unverified - in the fourth clause of the third paragraph of
the second comment, below a note about a refused command. Nothing was lost.
It was de-ranked into invisibility, which from the driver's side is the same
thing.

The fix is not "be concise", because a brief fails in two ways that look like
opposites - a finding does not survive it, or nobody finishes reading it - and
treating those as a length dial is what produces a report that is both long
and missing things. They happen to different material, so the rule is:

> **Compress the state. Quote the caveats.**

State is which child is doing what. It is repetitive and compresses
losslessly. A caveat is a sentence where somebody qualified their own work,
and the hedge is the entire content, so summarising one deletes exactly the
part worth having - "the designer hand-computed these and flagged it" becomes
"contrast verified" in a single well-meaning pass, and nothing in that chain
is false. The new `briefing` skill carries that rule, a six-class ranking with
a role's caveat about its own deliverable at the top, a fixed `### For the
driver` section, and a do-not-report list whose first entry is process
narration.

**And the channel runs both ways.** The orchestrator's supervision section
read the children's labels and nothing else, so a driver's correction written
on the parent issue was never read - the one reader allowed to correct a split
had no way to. It now reads new parent comments on every wake, and the driver
is told the three moments worth spending pushback on: the decomposition before
the first child is queued, a child's criteria before it is queued, and a brief
that sent it looking. All three are cheaper than the diff they prevent.

What this does **not** add is a way to send a rejected diff back for revision.
That arrived in 1.31.0, below.


## Addendum: work that comes back (1.31.0)

1.30.0 gave the driver the authority to refuse a diff and left it with nowhere
to put the refusal. A child at `agent:review` whose pull request was rejected
had two exits and both were wrong:

- **`agent:queued`** spends one of three attempts and starts a run holding
  nothing but the issue it already satisfied once. The review - the one
  artifact that says exactly what to change - is not in the issue, and nothing
  tells the run to go and read it.
- **`agent:blocked`** sends the orchestrator to do a corrective pass, which
  rewrites the *issue*. The issue was not the problem. The diff was.

The cost landed on the budget, and that is what made it decisive rather than
merely awkward. Rejecting a diff cost exactly what failing to write one costs,
so a driver that sent work back twice left a nearly-right issue at
`needs-decomposition` with nothing left to spend. The rational move was to
merge something mediocre, which is the opposite of what 1.30.0 was for. An
authority with a punitive mechanism under it is not an authority.

So `agent:revise`, and the shape of it follows the two budgets that already
existed. The preflight has always counted runs by marker comment, against
`max-attempts` for a child and `max-supervisions` for an objective, because
those two measure different things. A revision round measures a third thing -
work that was delivered, read, and sent back with a review attached - so it
gets a third marker and a third budget, and neither of the other two spends it.

**Two rounds, not three**, and the asymmetry with the three-strike rule is
deliberate. Three attempts means the issue was scoped wrong. A run that cannot
satisfy a *written review* after two goes is not short of ideas: either the
review asks for something the issue does not cover, or it is not specific
enough to act on. Both of those are the reviewer's to fix, so the third round
goes to a person rather than to the role - and the refusal says so in those
terms, rather than reciting a three-strike rule that never applied.

**It is a second way into a run, not a new kind of run.** The revise label
starts a run through the same preflight as the run label, with the same gating,
the same concurrency, and the same hand-back. What differs is the budget it
spends and what the prompt tells the run it is doing: read the review on your
own open pull request first, work the branch that exists, address what was
asked and nothing else, reply saying what you changed and what you did not.
Disagreement is allowed and does not stop the work - say so on the pull
request, then do it their way, unless it would break a house rule, and then
name the rule and stop.

Two consequences worth stating, because they are the ones that will bite:

- **The review is now the run's entire brief**, which makes its quality
  load-bearing in a way a comment on a pull request never was. A review naming
  the file and what about it is a specification. One naming an impression is a
  revision round spent on nothing, and the budget it spends is the reviewer's
  doing rather than the role's.
- **A label the preflight matches on and the repository does not have is a
  mechanism that fails silently.** The same trap `agent:needs-input` hit one
  release earlier: a repository provisioned before the label existed drops the
  work on the floor. `bootstrap` is idempotent, and re-running it from the
  Actions tab after `/update-agents` is the whole fix.

The watchdog covers both labels now, for the reason it exists at all: every
fault this system has had presented as a correctly labelled issue with no run
behind it, and a second way in that nothing watched would have reintroduced
that on the new label while the old one stayed covered.

What is still not built is any way for the orchestrator to send work back. That
is deliberate rather than pending. `agent:revise` carries a person's reader's
judgment about a diff, and the orchestrator does not read diffs - it reads
labels, criteria, and what a child reported about itself. Giving it the label
would close the loop the house rules keep open on purpose: the factory
splitting an objective, building it, judging it, and re-running itself with no
decision from a person anywhere in the chain.
