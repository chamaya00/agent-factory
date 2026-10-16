# ADR 0005: sessions are the only runner, and setup needs no credentials

Date: 2026-10-16
Status: accepted. Supersedes the `runner` setting in ADR 0004, and narrows ADR
0003.

## Context

ADR 0004 let a repository run its agents from Claude Code sessions instead of
from the `agent-run` workflow, and kept the workflow as a second runner chosen
by a `runner` field. The reason for keeping it was that the subscription token
it needed might be fixed by regenerating it.

The owner has since moved everything to sessions and decided the token is not
coming back. With no token the workflow runner cannot run anything at all, and
keeping it cost far more than a field: 1,500 lines of workflow, two test
suites, a run-time allowlist that two validators cross-checked against every
role, an agent identity App whose private key had to be created and pasted from
a phone, and a getting-started path whose longest steps were all about those
credentials. Every one of those was paid for again by each new person who read
the setup docs.

A second thing surfaced while removing it. The project's `guard` and
`bootstrap` callers declared no permissions, and a new repository's default
token is read-only, so the reusable workflows - which ask for
`pull-requests: read` and `issues: write` - failed at startup with no log. That
is why setup used to include changing the repository's Actions permission, and
why `/new-project` carried a paragraph about an unexplained `startup_failure`.

## Decision

- **Sessions are the only runner.** `agent-run.yml`, its caller, its tests, and
  the run-time allowlist checks are deleted. `/dispatch` is how every run
  starts. The `runner` field is dropped; `/update-agents` removes it and
  deletes the old caller from a project.
- **No credential is part of setup.** No subscription token, no agent App, no
  repository secret. A session works as the person who opened it.
- **Callers declare their own permissions,** exactly what their reusable
  workflow asks for, so the gates start on a repository with GitHub's default
  settings. The Actions-permission step is gone from setup.
- **Provisioning stays, optional and smaller.** `provision.yml` now does only
  what a session cannot and the person would otherwise do by hand: start
  `bootstrap` and set branch protection from the reported check names. Its
  secrets, App, and Actions-permission steps are removed, along with
  `scripts/setup-project.sh`, the terminal path to the same steps.
- **A person who has not forked the factory can set up a repository** from a
  session on that repository: it clones the factory at its newest release and
  follows `/new-project` from the clone. Projects set up that way call the
  upstream factory's workflows and take its releases through `/update-agents`.

## What setup is now

Per repository, the person does at most three things: create it (public, with
a README) if it does not exist, tap Run workflow on `bootstrap`, and set branch
protection from two check names the session reads back for them. Everything
else is file work the session does.

## Consequences

- A project on a release before this one keeps its `agent-run` caller, and that
  caller keeps firing on queue labels and failing on the missing token, spending
  an attempt each time, until `/update-agents` deletes it. That pull request is
  the migration, and nothing else is.
- The protections the workflow enforced in code - turn caps, a timeout, a
  concurrency group, a preflight the agent could not argue with - are now steps
  `/dispatch` follows. The budgets are still counted from marker comments, so
  they hold across sessions, but nothing executes them. `project-guard` is the
  one containment check left that no session can talk its way past, which is why
  ADR 0004's branch rule matters as much as it does.
- The bot-author path in `project-guard` - an agent App's pull request, cleared
  by a maintainer's push - no longer has anything to serve. It is left in place
  because it is harmless, tested, and is what an organization that reintroduces
  a separate agent identity would want.

## Alternatives

**Keep the workflow runner as an option.** That was ADR 0004, and it is the
right call while the credential might return. Without it the option is a
second runner nobody can use, documented at length in exactly the pages a new
person reads first.

**Retire provisioning too.** Its remaining value is one approval instead of one
tap and one settings page per repository, for an owner who sets up many. That
is worth keeping as long as it costs a new person nothing, and moved out of the
main path it does not.
