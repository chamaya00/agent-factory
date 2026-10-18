# ADR 0006: a workflow changes only through `/gate`, on the person's yes in session

Date: 2026-10-18
Status: accepted. Narrows the containment rule in the `house-rules` skill;
leaves ADR 0004's branch tripwire as it is.

## Context

No role may edit `.github/workflows/`, and `project-guard` refuses a change
there from an agent branch. That rule is the reason the gates mean anything,
and nothing here relaxes it.

But a project's gate has to change at least once. It is provisioned as a
placeholder whose tripwire fails the first engineer pull request on purpose,
and the real one has to land on that pull request's branch, because on the Node
path the default branch has no lockfile yet. So the swap was handed to the
person as a manual step: open GitHub's web editor on the branch, paste a YAML
block out of the pull request body, commit. In a project it blocked an
objective for about a day. Nobody was confused about what to do; the step
simply waited for a person to be at a browser with the right page open.

Meanwhile the session driving the objective could have done it in a minute.
Since ADR 0005 every session works as the person, and the guard only refuses a
workflow change on an agent branch, so a session pushing the file on any other
branch passes. The blocker was the rule and the missing procedure, not access.

## Decision

- **Roles still never write a workflow.** A role whose work needs one changed
  commits the whole file as it should read at `.github/proposed/<same
  filename>` on its own branch, and says in its pull request in plain words
  what the change does. No block for a person to paste.
- **The driving session applies it with `/gate <pr>`, and only on the person's
  explicit yes, in the conversation, to the diff it showed them.** The command
  reads the proposed files, shows the change against the default branch's
  current workflow in the person's language - what the check will run instead,
  and whether anything in **What a revert does not undo** is touched - and asks
  once. On a yes it builds `gate/issue-<n>` from the pull request's head, moves
  each file into `.github/workflows/`, commits saying whose yes and when, and
  opens a replacement pull request carrying `Closes #<n>`, `Replaces #<old>`,
  and a `Privilege change:` line that records the approval. The old pull
  request is closed with a link.
- **Nothing standing covers that yes.** Not a merge policy, a self-driving
  stretch's delegation, an orchestrator's brief, or a role's request. A no, or
  no answer, leaves the pull request waiting with `needs-human` on it.
- **Three changes are refused rather than applied:** a renamed check name,
  which stops the required check reporting and blocks every merge; a proposal
  written against an older version of its target, which would undo whatever
  landed since; and a moved factory pin, which belongs to `/update-agents`.
- **`project-guard` fails a pull request into the default branch that would
  leave a file under `.github/proposed/`.** Merged as it stands, a proposal
  changes nothing while reading as done. The privilege step stops reading those
  files, since nothing runs them there, and reads them in full in the
  replacement, where they become executable.

## Consequences

- The first real gate lands in the session, at the moment the person is
  already there reviewing the work, rather than waiting on a separate trip to a
  browser.
- The person's yes is the only thing between a proposal and a running
  workflow. The session holds their credentials and could push the file
  without asking; what stops it is the same thing that stops a driver writing
  its own merge policy - every place that describes the step forbids it, and a
  driver honours only what it can account for. That is a rule, not a wall,
  exactly as ADR 0004 says of the branch check.
- An engineer pull request carrying a proposal is red on the guard until
  `/gate` replaces it. That is the hand-off working, and the skill and
  `/check-in` say so, so a driver does not send it back as a failure.
- A replacement that needs more work does not go to a role on the `gate/`
  branch, which the guard does not watch. The replacement is closed, the
  original reopened and sent back, and `/gate` runs again on what returns.
- Self-driving stretches stop at a gate change. The yes cannot be given ahead,
  because the diff does not exist yet, so a stretch names the child that will
  propose one as a stopping point when it starts.

## Alternatives

**Keep the manual step.** It is safe and it costs a day each time, at the one
point in a project's life when the person is most likely to want things moving.

**Let the engineer edit the workflow on its own branch.** That is a role
rewriting its own gate, which is the thing the containment rule exists to stop.
A guard exemption for the gate file would be one nobody could tell apart from
drift.

**Let a merge policy or a self-driving delegation cover it.** Both are standing
instructions about green. A gate change decides what green means, so it is not
something a person can have agreed to before seeing it.
