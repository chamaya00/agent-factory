---
description: Bring this repository's copy of the shared roles, skills, and workflow pins up to a factory release, as one reviewable pull request.
argument-hint: "[version]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__github__get_file_contents, mcp__github__create_branch, mcp__github__push_files, mcp__github__create_pull_request, mcp__github__list_branches
---

Update this repository to a factory release. Nothing here happens on a
schedule and nothing happens to any other repository: this command proposes a
diff in one repository, and a human merges it or does not.

`$1` is the release to move to, for example `v1.2.0`. If it is empty, read the
latest release tag of `chamaya00/agent-factory` and use that.

Everything you copy comes out of the factory repository at that tag, read with
`mcp__github__get_file_contents` against `chamaya00/agent-factory` with `ref`
set to the tag. Do not read it from an installed plugin: a cloud session has
none, and the whole point of naming a tag is that the answer does not depend on
what happens to be on the machine you are running on.

## 1. Work out where this repository is

Read `.claude/agent-factory.json`.

**It is missing.** This repository was provisioned before the roles were
vendored, or was never provisioned at all. Check whether
`.github/workflows/ci.yml` calls the factory. If it does, this is the older
arrangement: continue, and say in the pull request body that it moves the
repository onto vendored roles for the first time. If it does not, this is not
a factory repository - stop and say so rather than turning it into one, which
is what `/new-project` is for.

**It is there and its version already equals the target.** Say so and stop. Do
not open an empty pull request.

**It is behind.** Continue, and remember both versions for the body.

If the tag does not exist in the factory, say so and stop rather than falling
back to a branch. A release is a commit somebody reviewed; the default branch
is whatever landed last.

## 2. Collect what changes

Read these out of the factory at `$1`:

- `agents/*.md` - every role
- `skills/*/SKILL.md` - every skill
- `commands/retro.md`, `decompose.md`, `update-agents.md` - the commands a
  project gets. Not `new-project.md`, which stays in the factory.

Compare each against the copy in `.claude/agents/`, `.claude/skills/`, and
`.claude/commands/`. Note which are new, which changed, and which exist here
but no longer exist in the factory. A role that was removed upstream gets
deleted here too, and gets its own line in the body, because a stale role that
nothing maintains is worse than no role.

Then read `.github/workflows/*.yml` and find every line matching
`uses: chamaya00/agent-factory/...@`. Those are the workflow pins. Collect the
ones not already at the target version.

The pins are the four workflow callers and nothing else. There is no
marketplace `ref` to move: this repository loads its commands and roles from
its own `.claude/` directory, so the copies you are writing in this same commit
are the only thing that decides which release it runs. That includes this
command - after this merges, `/update-agents` here is the copy from `$1`.

If nothing at all differs, say so and stop.

## 3. Propose it

One branch, one commit, one pull request:

- `mcp__github__create_branch` from the default branch
- `mcp__github__push_files` with every changed file in a single commit
- `mcp__github__create_pull_request`

What goes in the commit:

- The changed role, skill, and command files, verbatim from the factory. Do not
  edit them on the way through. A local edit makes this repository quietly
  disagree with every other one, and the next run of this command overwrites it
  anyway.
- All four workflow callers moved to the target version together. The roles,
  the workflows around them, and the commands that maintain them are one
  release; taking half of it is how they drift apart.
- `.claude/agent-factory.json` with the new version, and the role, skill, and
  command lists refreshed to what was actually written.

Leave alone, always:

- Everything under `.claude/memory/`. Those are this repository's lessons, and
  they are the reason the roles are copied in rather than shared live. Nothing
  in an update reads them, writes them, or carries them anywhere.
- `CLAUDE.md`. It describes this product, not the process.

## 4. Say what it does in the body

The point of the pull request is that somebody reads it before it runs, so
write the body for that reader:

- The two versions, from and to.
- Which roles, skills, and commands changed, one line each, saying what
  actually changed in behaviour rather than that the file changed.
- Which pins moved.
- Anything removed upstream, called out separately.

Then note that the checks on this pull request run at the *old* pin, because a
caller change only takes effect once merged. So a green pull request here
proves the diff is well-formed, not that the new release passes on this
repository. The first run at the new pin is the next pull request after this
one merges - worth watching.

If the person who has to merge this is also the person who owns the factory,
say plainly which changes came from a factory release they cut and which are
local drift being reverted. Those are different things and they read the same
in a diff.
