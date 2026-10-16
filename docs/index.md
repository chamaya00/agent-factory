# agent-factory

A reusable toolbox that turns high-level objectives into working code across
projects. Agent roles and process travel in a plugin, automation travels as
reusable workflows each project calls in one line, and everything a project
learns stays in that project.

The repository is at
[github.com/chamaya00/agent-factory](https://github.com/chamaya00/agent-factory);
its README covers the layout and the design decisions. These pages are the
operating documentation.

## Start here

**[Getting started](getting-started.md)** - what you need (a Claude plan with
Claude Code, and GitHub connected - no tokens, secrets, or Apps), setting a
repository up from a session on it, and using it day to day. The whole of it,
for anybody, readable on a phone.

## Running the factory

1. **[The checkpoint](checkpoint.md)** - what only the factory's owner does:
   cutting a release after a version bump, cleaning up what older releases
   needed, and two optional conveniences.
2. **[Proving the gate](proving-the-gate.md)** - confirm by hand that a red
   check blocks a merge and that the containment guard refuses an agent branch,
   on a throwaway repository, before any objective is filed.
3. **[The smoke test](smoke-test.md)** - two objectives through the whole loop,
   building a site the repository publishes, so the result is judged by opening
   a URL rather than by reading a diff.

## Reference

- **[Improvement rounds](improvement-round.md)** - how a session improves
  the factory on its own judgment: finds needs nobody has named yet, builds the
  small safe ones ahead of approval, and reads it all back as one digest issue
  the owner answers with ticks. Also how to run one weekly.
- **[What is checked](what-is-checked.md)** - which parts of the system are
  verified automatically, which are verified by hand, and which are not
  verified at all. Start here if you are asking whether any of this works.
- **[Open questions](open-questions.md)** - the assumptions this system runs
  on that nothing has tested yet, each with how to settle it and what changes
  once you do. An entry gets deleted when it is answered, not annotated.
- **[How a change reaches a project](versioning.md)** - what a release tag
  is, why the callers pin one, and why cutting a tag changes nothing on its
  own.
- **[Driving an objective](driving-an-objective.md)** - the design record for
  the interactive session's role: what it owns, and how a person's "merge when
  green" survives the end of the session they said it in.
- **[Implementation plan](implementation-plan.md)** - the document this was
  built from, phase by phase. Historical: its Actions runner, subscription
  token, and agent App were retired by ADR 0005.
