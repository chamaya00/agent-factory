---
description: Bring this repository's copy of the shared roles, skills, and workflow pins up to a factory release, as one reviewable pull request.
argument-hint: "[version]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__github__get_file_contents, mcp__github__create_branch, mcp__github__push_files, mcp__github__create_pull_request, mcp__github__list_branches
---

Update this repository to a factory release. Nothing here happens on a
schedule and nothing happens to any other repository: this command proposes a
diff in one repository, and a human merges it or does not.

`$1` is the release to move to, for example `v1.2.0`. If it is empty, use the
version in `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` - that is the
factory you have installed locally, and it is the normal case.

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

If your local plugin is older than `$1`, say so and stop: you cannot copy
files you do not have. The fix is `/plugin update agent-factory@agent-factory`
first, then run this again.

## 2. Collect what changes

Read from `${CLAUDE_PLUGIN_ROOT}`, which is the installed factory:

- `agents/*.md` - every role
- `skills/*/SKILL.md` - every skill

Compare each against the copy in `.claude/agents/` and `.claude/skills/`. Note
which are new, which changed, and which exist here but no longer exist in the
factory. A role that was removed upstream gets deleted here too, and gets its
own line in the body, because a stale role that nothing maintains is worse
than no role.

Then read `.github/workflows/*.yml` and find every line matching
`uses: chamaya00/agent-factory/...@`. Those are the pins. Collect the ones not
already at the target version.

If nothing at all differs, say so and stop.

## 3. Propose it

One branch, one commit, one pull request:

- `mcp__github__create_branch` from the default branch
- `mcp__github__push_files` with every changed file in a single commit
- `mcp__github__create_pull_request`

What goes in the commit:

- The changed role and skill files, verbatim from the plugin. Do not edit them
  on the way through. A local edit makes this repository quietly disagree with
  every other one, and the next run of this command overwrites it anyway.
- Every workflow pin moved to the target version, the four callers together.
  The roles and the workflows around them are one release; taking half of it
  is how the two drift apart.
- `.claude/agent-factory.json` with the new version, and the role and skill
  lists refreshed to what was actually written.

Leave alone, always:

- Everything under `.claude/memory/`. Those are this repository's lessons, and
  they are the reason the roles are copied in rather than shared live. Nothing
  in an update reads them, writes them, or carries them anywhere.
- `CLAUDE.md`. It describes this product, not the process.

## 4. Say what it does in the body

The point of the pull request is that somebody reads it before it runs, so
write the body for that reader:

- The two versions, from and to.
- Which roles and skills changed, one line each, saying what actually changed
  in behaviour rather than that the file changed.
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
