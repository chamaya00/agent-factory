---
description: Keep work moving while no session is open - set up, change, or stop the scheduled session that runs /check-in on this repository every few hours, in a repository whose runner is session.
argument-hint: "[every <N> hours | stop]"
---

Set the clock that opens a session on this repository when nobody else has.

In a repository whose `.claude/agent-factory.json` says `"runner": "session"`,
nothing starts a run but a session. That is the whole of the trade: no stored
subscription token and no workflow spending it, in exchange for nothing moving
while no session is open. A child that finished overnight, a pull request
merged from a phone, an objective filed and walked away from - each waits for
the next session someone happens to open. Pull request subscriptions carry an
open session a long way, but they wake only a session that exists, and they
never see an issue label.

This is the session that exists anyway. It is a scheduled routine that starts a
fresh session on this repository every few hours and runs `/check-in`, which
dispatches whatever is queued. It replaces two things the agent-run workflow
did on its own: starting a run when a label appeared, and the twelve-hourly
tick that said out loud when something queued was not moving.

Read `.claude/agent-factory.json` first. If `runner` is not `session`, say so
and stop: there the workflow starts runs, and a second clock dispatching the
same issues double-spends them.

## 1. Find the one that exists

List the routines this account has (`list_triggers`, where there is one) and
look for one named `heartbeat: <owner/repo>`. There must be at most one per
repository - two heartbeats are two sessions racing for the same queued issue,
and the `agent:running` label is the only lock between them.

- `$ARGUMENTS` is `stop`: delete it, say so, and stop. If there is none, say
  that instead.
- One exists: change its schedule to what was asked rather than creating a
  second. With nothing asked, say what it is set to, when it next fires, and
  stop.
- None exists: make it, below.

## 2. Make it

- **Name:** `heartbeat: <owner/repo>`.
- **Schedule:** every four hours unless `every <N> hours` says otherwise, and
  never more often than hourly. Each firing is a session spending the
  subscription even when it finds nothing to do, and the work it catches has
  been waiting hours already; a tighter clock buys least exactly when it fires
  most. Use minute `0` for an every-N-hours schedule.
- **Each firing starts a fresh session on this repository,** not a wake of this
  one. This session will be gone long before the routine is; a firing must not
  depend on what this conversation remembered.
- **Push notifications on,** so a firing that found something waiting on the
  person reaches their phone.
- **The message,** verbatim:

> Run /check-in in this repository, exactly as .claude/commands/check-in.md
> says, including dispatching what is queued one run at a time with /dispatch.
> Merge only where an objective carries a `Merge policy: green` line a person
> wrote, and only what passes the gate. Do not start a self-driving stretch,
> write a merge policy, close an objective, or remove a label a person set.
> End with at most three lines: what moved, what is waiting on me, and the link
> to look at first. If nothing changed and nothing is waiting on me, say so in
> one line.

## 3. Say what you made

When it first fires, how often after that, what each firing does, and how to
stop it: `/heartbeat stop` in any session on this repository, or deleting the
routine. Say too what it does not do: it does not answer a question a role
raised, merge anything without a policy line, or start a stretch that hands
over the person's calls - `/self-driving` is that, and only the person starts
one.

If the environment has no way to schedule a session, say so plainly and stop.
Work in this repository then moves only while a session is open, and the
person should hear that from you now rather than discover it from a quiet
week.
