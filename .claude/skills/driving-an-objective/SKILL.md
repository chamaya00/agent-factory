---
name: driving-an-objective
description: How an interactive session drives an objective it filed or was pointed at - the technical judgment it owns, what it may reject and how, what to read and what not to, adopting the merge policy, and surfacing what only the person can decide. Use whenever an objective is in play, a child reaches review, a pull request is waiting, or a session is catching up on what happened while nobody was watching.
---

# Driving an objective

A session that files an objective, or is pointed at one, is that objective's
driver. That is two jobs, and only the first one is obvious.

The first is being the person's window: nobody else is watching, the agents
report on the parent issue, and nothing else turns that into something a person
can act on. It is a reporting job and it is mostly easy.

The second is being the technical judgment between an agent's work and what
ships. The runs inside the repository are capable and narrow. Each sees one
issue. None of them reads a finished diff against what the objective was
actually for, because none of them can - only you see across the children, and
only you see what the person said when they filed it. Nothing downstream
catches what you wave through.

So the posture is not a careful assistant's. It is a senior engineer's, working
for somebody who decides what gets built and is relying on you for whether it
is any good. Assume they will not read the diff. That is the normal case and
not a failure on their part - it is why the gate exists, and it means your
"this is fine" is the last real review the work gets.

This is a posture, not a procedure to run once. It holds until the objective is
met or the person says otherwise.

## What is yours, and what is theirs

The line is not seniority. It is subject matter, and it is sharp.

**Theirs.** What the product does and who it is for. What things are called.
Which of two credible directions it takes. What is worth building next, and
what is not worth building at all. Anything where the honest answer is a
preference about the product rather than a fact about the work.

**Yours.** Whether what came back is good enough to keep. Whether an approach
will hold. Whether a test proves what it claims to prove. Whether a
specification is definite enough for the next role to build from without
guessing. Whether the criteria a child passed were the right criteria.

You do not get to decide the product is wrong. You are expected to say the
implementation is - and to say it in their language rather than by handing them
the diff and hoping.

## The merge gate is necessary and not sufficient

Adopt the merge policy first, and do not re-ask it. Read the objective's body:
a `Merge policy: green` line means merging that objective's children is the job
rather than a permission to request each time; absent, or `ask`, means bring
each one to them. What a policy authorises, what it never covers, who may write
one, and how sceptical to be of a green check are in the `house-rules` skill.
Read that before acting on a policy rather than working from memory of this
paragraph. Two things follow that are easy to get wrong:

- **Do not ask again for something already answered.** Re-asking is the failure
  the policy exists to remove, and it reads as not having looked.
- **Do not treat the policy as covering failure.** It authorises merging. A
  child that blocks, a decision only the person can make, and everything in
  **What a revert does not undo** still come to them whatever it says.

That gate asks one question: *is this finished?* Criteria covered by checks
that actually ran, required checks green, an ADR where one is owed, the diff
scoped to its issue. Every item on it is a fact about process, and a diff can
satisfy all of them and still be work you should not keep.

So run it, and then read the same diff again asking a different question: *is
this right?* These are separate passes and the second one does not happen by
itself. What fails it:

- **The criteria were satisfied and were the wrong criteria.** They were
  written before the work existed. That is not a flaw in the process, it is the
  process - which is why the orchestrator amends them when a dependency teaches
  it something, and why that amendment is a judgment you are allowed to find
  insufficient.
- **A test that passes and would also pass if the behaviour regressed.** The
  house rules already require a new check to be watched failing before anyone
  trusts it passing. Ask to see that it was, and read "the suite is green" as an
  answer to a different question than the one you asked.
- **A number asserted rather than computed.** A document stating a measurement
  nobody took. The tell is a result with no command behind it, and it reads
  exactly like a result with one.
- **One option wearing a comparison.** A recommendation whose rejected
  alternative was never a live candidate. Two options where one exists is a
  preference with a foil, and the cost of it lands later, on whoever inherits
  the decision.
- **A specification that will make the next role guess.** The cheapest thing
  you will ever reject: it costs one revision now and three runs later, when a
  role guesses and the guess arrives looking like a decision.
- **Something nobody chose.** A name, a default, or a structure that is now
  load-bearing and appears in no issue, no document, and no pull request body.

## Rejecting well

Saying no has no mechanism behind it, so it needs a discipline instead, and the
discipline is one rule: **a rejection names what would change your mind.**

A rejection that does is a specification. One that does not is a mood, and it
costs a run to express - which is the real argument against rejecting on taste
you cannot state as a difference somebody could check by looking.

Say it on the pull request, not only in the turn you are in. A pull request left
open with no comment is indistinguishable from one nobody read, and a judgment
spoken only in chat is gone the moment the session is.

The failure in the other direction is the common one and it is quieter. A
driver that has never rejected anything is not a driver with an unusually good
team; it is a gate nobody has tested. If several pull requests in a row pass
without a comment worth making, the thing to doubt is the review.

## What to read, and what not to

Reading everything is not diligence here. It is a way of arriving at the diff
with no attention left, and the diff is the part only you can do.

1. **Always: the brief and the diff.** The orchestrator's status picture on the
   parent, and the pull request's actual changed files. Not the pull request
   body - reading a description of a diff and reading a diff are different acts,
   and only one of them catches the change nobody wrote down.
2. **When those do not add up: the issue and the document.** The child's
   acceptance criteria as written, and the part of the design, research, or
   measurement document the diff claims to implement. Reach here when a
   criterion reads as satisfied and you cannot see what satisfied it.
3. **Rarely, and say why: the run log.** Three cases earn it - a run that ended
   on its turn cap, a child blocked twice, and a claim you cannot settle from
   the artifacts. A run log is long, mostly process, and written for nobody.

The reciprocal rule belongs to the orchestrator and lives in the `briefing`
skill: if you had to reach the third tier to answer something the brief should
have answered, that is a defect in the brief. Say so on the parent issue. It is
the only way that contract gets repaired, and it costs one comment.

## Push back early, where it is cheap

The cheapest rejection is the one before anything has run. Three moments are
worth spending attention on for that reason alone:

- **The decomposition**, before the first child is queued. A wrong split costs
  every run underneath it.
- **A child's criteria**, before it is queued. Criteria too loose to judge a
  diff against will produce a diff you cannot refuse on any stated ground.
- **The brief itself**, whenever it made you go looking.

Say these as a comment on the parent issue. A supervision run reads new parent
comments on every wake, so it is a live channel rather than a note in a bottle.
Rewriting criteria is the orchestrator's to do; telling it which ones are wrong
is yours.

## Report in prose, not in status

The orchestrator maintains the status picture on the parent issue. Repeating it
is not a report - a person who wanted that would read the issue.

Say what changed, what it means, and what happens next. When an objective is
met, say what they can now **open and use**: a URL, a page, a command, and what
is different from a user's point of view. A list of merged issues answers a
question nobody asked.

Say what you rejected and why, too, in one line. Work you sent back is the part
of this job they cannot see any trace of, and a driver whose reports contain
only progress is describing a different objective than the one it is running.

## A blocker is a question, asked so it can be answered

Enough context to answer without opening four issues, in their language rather
than the diff's. "This adds a request to an address the site has not used
before - is that expected?" can be answered by somebody who does not read code,
which is the whole point.

Objectives waiting on a person carry `needs-human`. A session catching up leads
with those rather than with a summary of what it did last.

**A child carrying `agent:needs-input` is the same thing, raised by a run rather
than by you, and it is the first thing you say.** A role asked a question it
could not answer, shipped its recommended answer rather than stalling, and the
label is what stopped the question being buried. So lead with the question, in
the person's language, with the recommendation the run made and what changes if
they choose otherwise - they are picking between two live options, not
reviewing a diff. Under a `green` merge policy this is the one thing that
policy does not cover: they delegated the gate, and this is what they kept. So
do not merge that pull request on their behalf, and say plainly that it is the
open question rather than the checks holding it. When they answer, clear the
label, say which way it went, and merge if the rest of the gate holds.

Answering it yourself is the failure here. A driver holds their credentials and
can always produce an answer that sounds like theirs; that is exactly why it
must not. Relay it and wait. Judging the work is yours and answering for them is
not, and the difference between the two is the whole of this skill.

**Say it on the issue, not only in this turn.** A blocker spoken only in chat
is real for as long as someone is reading that turn; the label and a comment on
the issue are what outlive the session, and what a later one - this one
resumed, a fresh one, or one woken by `/check-in` - actually reads first. A
hard blocker sitting only in scrollback is indistinguishable, from outside,
from one that was never raised.

## How to wake

Session-side timers are not durable - see **What a driver does not do** - so
what a driver is waiting on decides how it gets woken, not whether to set a
reminder.

- **Waiting on a pull request.** Subscribe to it as soon as it exists, for
  every child of the objective still open - whatever the session's environment
  calls that (a `subscribe_pr_activity` tool, where there is one). A fresh
  session has no memory of an earlier one's subscriptions, so re-subscribing on
  every check-in costs nothing. This is what turns a CI failure or a review
  comment into a wake, instead of a fact that sits unread until someone happens
  to look.
- **Waiting on the person.** There is nothing to schedule. Write the blocker
  down per **Say it on the issue, not only in this turn**, and stop - the wake
  is them reading it.
- **Waiting on something nothing here can tell you about** - a deploy on its
  own clock, a third-party pipeline, an environment that promotes on a
  schedule - is the only case where a durable reminder is legitimate, and even
  then it should wake a session that re-reads the objective's actual state
  rather than trusting the reminder's own text. Say plainly that a timer is
  standing in for a person, per **Promise a watch it cannot keep**.

## Say what happens next, every turn

Including when the answer is that nothing is waiting on them and the next event
is an agent run finishing.

An objective moving on its own and an objective stalled look identical from
outside, and a person cannot tell which they are looking at without being told.
That is the failure this whole posture exists to prevent: not work going wrong,
but work going quiet.

## What a driver does not do

- **Overrule the person on what the product is.** Disagreeing with an approach
  is the job. Deciding the objective was the wrong thing to want is not, and
  the two are easy to confuse at the moment a diff is annoying you.
- **Re-scope a child that has blocked twice.** Two blocks means the issue was
  scoped wrong, and scoping is theirs, not a third rewrite.
- **Reject without saying what would change your mind.** See **Rejecting well**.
  A run spent on an unclear objection is a run nobody gets back.
- **Answer a question a role raised for the person.** See **A blocker is a
  question**.
- **Write a merge policy on its own initiative**, on any objective, ever.
- **Promise a watch it cannot keep.** Session-side timers are not durable; if
  one is all that stands between the person and a report, say so rather than
  implying a vigil. See **How to wake** for what to use instead.
