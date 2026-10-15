# ADR 0004: agent runs can happen in sessions, and the runner is a setting

Date: 2026-10-15
Status: accepted

## Context

Every agent run in every project has been one job in `agent-run.yml`, which
wraps an action that authenticates with `CLAUDE_CODE_OAUTH_TOKEN` - a token
from `claude setup-token`, generated once in a Codespace and pasted into every
repository as a secret. That token is the one credential in the system that
expires or can be revoked, and when it stops working every run in every
project fails at once. They fail as blocked issues that have spent an attempt,
not as a message saying the credential has gone.

The person this system serves drives it from cloud sessions on a phone. Those
sessions already authenticate as that person, already reach the repository
through a GitHub connection, and can already run the role definitions: a
session loads `.claude/agents/` as subagents with the tool lists the roles
declare, and can start further sessions of its own. Everything a run needs
except a trigger was already there.

What the workflow provides that a session does not has to be named, because
that is what this decision gives up or replaces:

1. **A trigger.** A label starts a run, a merge wakes the parent, and a
   twelve-hourly tick reports what is stuck. A session hears nothing about
   issue labels; it hears pull request activity only for pull requests it has
   subscribed to.
2. **Limits the agent cannot argue with.** A turn cap, a timeout, three
   attempts, two revision rounds, twenty supervision runs - all enforced before
   or around the agent rather than by it.
3. **An identity of its own.** The agent App opens the pull requests, so "the
   author is a maintainer" means a person wrote it. `project-guard` rests on
   that.
4. **A hand-back that runs even when the agent dies.**

## Decision

`.claude/agent-factory.json` gains a `runner` field, `actions` or `session`.
It is the project's setting, not the release's, and `/update-agents` keeps
whatever it says. A manifest without it predates it and means `actions`.

Under `session`:

- **`agent-run.yml` stands down.** Its preflight reads the field from the
  default branch and skips before anything writes. The caller stays in the
  project, so switching back is one line, and the merge job still labels the
  parent `agent:queued` - which is now a request a session acts on rather than
  an event a workflow does.
- **`/dispatch` is the run.** It carries the workflow's checks, budgets,
  marker comments, labels, brief, and hand-back into the driving session, so
  the orchestrator and a person reading the issue cannot tell which runner did
  the work. The orchestrator always runs in the session as a subagent; other
  roles run as subagents or, with `--child`, in a child session the person can
  open.
- **`/check-in` dispatches what is queued,** one run at a time, and
  `/heartbeat` creates a scheduled routine that opens a fresh session every
  few hours to run it. Together they replace the label trigger and the tick.
- **`project-guard` reads the branch as well as the author.** A
  maintainer-authored pull request from a branch matching `agent-branches`
  (`claude/*` by default) is checked as the automation's, and neither the
  author nor the sender exemption applies.
- **The OAuth token is optional** in `agent-run.yml` and in provisioning, and
  the template ships `runner: session`, so a new repository needs no token at
  all.

## What was given up, and what replaces it

**The trigger** becomes a session. Nothing starts a run while no session is
open, except the heartbeat, which runs on the order of hours rather than
seconds. That is accepted: the work this catches has usually been waiting
for a person anyway, and a tighter clock spends the subscription fastest exactly
when nothing is happening.

**The hard limits** become partly convention. Attempts, revisions and
supervisions are still counted from the same marker comments and refused at the
same numbers, but by `/dispatch` rather than by a preflight the agent cannot
reach, and there is no turn cap or timeout on a session. The subscription's own
rate limit is the real ceiling, and one run at a time is a rule in the command,
not a concurrency group.

**The identity** goes entirely. Checked rather than assumed, on 2026-10-15:
pull requests opened from sessions on this repository are authored by the
owner's own login, and a session's push is the owner's too. So no check that
reads who opened or pushed something can tell the person from the automation.
The branch is what is left, and the guard now reads it. That is a tripwire, not
a wall: the same check showed a session can push to a branch of any name. It
stops a role editing a gate because the work seemed to need it, which is the
drift it was always for. It does not stop an agent set on getting round it, and
with one identity for the person and the automation nothing in this repository
can.

**The always-run hand-back** becomes the dispatching session's step 4, plus the
two-hour rule: an issue left at `agent:running` with no live run behind it is
handed back by the next `/dispatch` or `/check-in` that finds it. A session that
dies mid-run therefore leaves the issue looking busy until then, where a dead
workflow job handed it back at once.

## Alternatives

**Keep Actions and replace the credential.** An API key bills per token rather
than against the subscription, which the workflow refuses on purpose; a cloud
provider's model endpoint bills the same way and adds an account to keep.
Regenerating the OAuth token is the right fix when it has merely expired, and
`runner: actions` stays fully supported for that case. It does not remove the
single credential whose failure stops every project, which is the problem this
decision is about.

**Sessions only, deleting the workflow runner.** Simpler, but it would make
every existing project's next `/update-agents` a migration whether its owner
wanted one or not, and it would leave no way back if sessions turn out to be
the worse runner for some repository. A setting costs one field and one
preflight check.

**Child sessions for every role.** Each run gets its own container and its own
context, and the person can open it. But a session that finishes cleanly does
not report back unless told to, and the orchestrator's output is the very brief
the driving session reads next, so running it elsewhere only adds a round trip.
Subagents are the default; a child session is one flag away when isolation or
visibility is worth the extra moving part.

**A webhook from GitHub into a session.** Would restore the event trigger. No
such bridge exists for issue events: the only GitHub activity a session receives
is on pull requests it subscribed to.

## Consequences

- A repository switches by changing one line in a reviewed pull request,
  usually through `/update-agents`. Its existing labels, budgets, marker
  comments, briefs, memory files, and roles carry over untouched.
- `/update-agents` and `/new-project` open their pull requests from
  `update-agents/<version>` and `provision/<version>`, not `claude/...`, so the
  guard does not refuse the person's own gate changes.
- Under `session`, the agent App is no longer what opens pull requests. It is
  still used by the workflow's merge and stuck-work jobs where a project keeps
  the caller, and provisioning still installs it.
- Dispatching spends the subscription from inside the conversation. Every run
  is a marker comment on the issue, and `/check-in` says how many it started.
