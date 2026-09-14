# Getting started

**Status: built.**

## Why this exists

Someone attaches a clone of this repository to a session - their own, or
someone else's - and the first thing they type is "hi", "help", "new",
"start", or "getting started". `/new-project` is the answer to that message,
but nobody who has not read the README knows to type the command, let alone
that it asks for an `owner/repo` and hands several steps back to a human
partway through. Left alone, a session answers a greeting with a menu of
everything in `plugins/agent-factory/`, and the person is no closer to a
provisioned repository than before they opened the session.

This document is the walkthrough `CLAUDE.md` points a session to. Follow it in
place of asking "what would you like to do?" when the opening message is
onboarding-shaped rather than task-shaped.

## When this fires

The opening message in the session is a greeting or a vague request to begin,
not a stated task. Treat any of these, and close variants, as
onboarding-shaped:

- `hi`, `hello`, `hey`
- `help`, `getting started`
- `new`, `start`, `new project`

**Not onboarding-shaped:** a message that already names a repository, a bug,
a file, or an objective. "Fix the mirror check" or "provision
`acme/widgets`" is a task - do the task, and do not interrupt it with the
walkthrough on the theory that the person must be new. Onboarding is for the
message that gives you nothing to act on yet.

Fire this once. If the person has already been through the walkthrough this
session - `/new-project` has run, or they have said what they actually want -
a later "hi" is small talk, not a re-trigger.

## The walkthrough

1. **Say what this is, in two sentences.** This repository provisions other
   repositories with the four agent roles, the reusable workflow callers, and
   the house rules that let an orchestrator run there safely. It does that
   through `/new-project <owner/repo>`, which the walkthrough is about to run.

2. **Ask for the target**: which `owner/repo` is being provisioned. If they do
   not have one yet, tell them the two things `/new-project` needs before it
   can start - the repository has to exist and it must be public - and point
   at step 2 of the command for the one-tap way to create it, rather than
   repeating those instructions here.

3. **Name the shape of the work before running it**, so nothing that happens
   next is a surprise: most of provisioning is file work the session does
   itself, but several things in `/new-project` are handed to a human -
   allowing Actions to approve pull requests, creating the repository if it
   does not exist, running `bootstrap`, adding the secrets, and branch
   protection. Say plainly, in one line, that these come back as a checklist
   at the end rather than as blockers now.

4. **Run `/new-project <owner/repo>`** once they confirm the target, and let
   the command's own steps narrate themselves - it already says which path it
   is on (`gh` present or not) and hands each manual step back in place. Do
   not re-explain what the command is about to say.

5. **Close on the report `/new-project` produces.** Its final step is already
   the deliverable: what was created, and the ordered list of what is still
   waiting on the person. Nothing here duplicates it - point at it rather than
   summarizing it a second way.

## What this deliberately does not do

**No new command.** The walkthrough is a way of opening the existing
`/new-project`, not a second path through provisioning - a `getting-started`
command that reimplemented step ordering would be a second copy of
`new-project.md` to keep in sync, which is the failure the mirror check
exists to catch in the other direction.

**No state.** The trigger is the shape of one message, decided fresh each
time a session opens here. There is nothing to persist, revoke, or get out of
sync, because there is nothing durable to a greeting.
