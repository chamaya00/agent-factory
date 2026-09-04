# agent-factory

A reusable toolbox that turns high-level objectives into working code across
projects. Agent roles and process travel in a plugin, automation travels as
reusable workflows each project calls in one line, and everything a project
learns stays in that project.

The repository is at
[github.com/chamaya00/agent-factory](https://github.com/chamaya00/agent-factory);
its README covers the layout and the design decisions. These pages are the
operating documentation.

## Standing a project up

In order, and the order is the point.

1. **[The checkpoint](checkpoint.md)** - the steps only a human can do: the
   subscription token, the repository secrets, the agent identity App, the
   release tag. Written for an iPhone, since that is the only device involved.
2. **[Proving the gate](proving-the-gate.md)** - confirm by hand that a red
   check blocks a merge, on a throwaway repository, before any agent is
   pointed at it. An agent aimed at a gate you do not trust produces work you
   have to read line by line, which is the thing this system exists to avoid.
3. **[The smoke test](smoke-test.md)** - one objective through the whole loop,
   ending in a working website you can open on a phone. What to watch for at
   each of the six steps, and the failure modes worth recognising on sight.

## Reference

- **[What is checked](what-is-checked.md)** - which parts of the system are
  verified automatically, which are verified by hand, and which are not
  verified at all. Start here if you are asking whether any of this works.
- **[Open questions](open-questions.md)** - the assumptions this system runs
  on that nothing has tested yet, each with how to settle it and what changes
  once you do. An entry gets deleted when it is answered, not annotated.
- **[How a change reaches a project](versioning.md)** - what a release tag
  is, why the callers pin one, and why cutting a tag changes nothing on its
  own.
- **[Implementation plan](implementation-plan.md)** - the document this was
  built from, phase by phase. Kept for the reasoning behind each phase.
