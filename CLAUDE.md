# Project context

## What this is

The factory. It ships the agent roles, house rules, and provisioning commands
that every other repository takes a copy of. Nothing here is a product feature;
everything here is how work is supposed to move somewhere else.

No agents run in this repository, and none should be bootstrapped into it. The
containment rules a project receives protect `.github/workflows/`,
`.claude/agents/`, `.claude/skills/`, `.claude/commands/` and the plugin
directory - which here is the entire product, so an agent working in this
repository would be forbidden from everything worth changing. Sessions here are
human or interactive, and that is the design rather than a gap in it.

## Layout, and the one thing sessions get backwards

`plugins/agent-factory/` is the source. `.claude/` is a byte-identical copy of
its `agents/`, `commands/`, and `skills/` directories, carried here because a
session loads those out of the clone and installs no plugin.

So the rule is the opposite of the one in a provisioned repository. There, the
plugin directory is untouchable and `.claude/` is what an agent reads. Here, the
plugin directory is what you edit, and `.claude/` is a mirror you never hand
edit - change the plugin, then copy the file across. `scripts/validate_plugin.py`
fails the build if the two disagree by a byte, and it names which side is the
source in the error.

The same check refuses a file in `.claude/agents|commands|skills` that has no
counterpart in the plugin. This repository therefore cannot have private
tooling in those three directories: anything added there ships to every project
provisioned afterwards. Factory-only tooling goes in `scripts/`, `docs/`, this
file, or `.claude/hooks/`.

## Commands

There is no package manager here and no build. The gate is five Python scripts,
run in this order by `.github/workflows/guard.yml`:

- `python scripts/validate_plugin.py` - manifests, roles, skills, portability,
  and the mirror
- `python scripts/validate_workflows.py` - the workflows parse and stay inside
  their limits (needs `pyyaml`)
- `python scripts/test_ci.py` - the gate still fails what it should fail
- `python scripts/test_preflight.py` - agent-run still refuses what it should refuse
- `python scripts/test_release.py` - release still refuses to tag unmerged history

`python -m pip install --quiet pyyaml` is the only dependency. The SessionStart
hook installs it and runs the first script, so a session that opened cleanly has
already been told whether the mirror is in sync.

## Standing rules

Templates pin the factory through `__FACTORY_VERSION__`, never a literal ref.
Provisioning substitutes it. A hardcoded ref ships to every repository
provisioned afterwards, and a moving one puts them all back on a live pointer.

The plugin describes how we work, not what any one project contains. No
framework, vendor, or product nouns in anything under `plugins/` - the
portability check holds a list and fails on a word boundary match.

A change projects must pick up needs a manifest version bump in the same pull
request. The tag name is read from `plugins/agent-factory/.claude-plugin/plugin.json`,
so a change with no bump behind it can never be released, and a bump with no tag
behind it provisions repositories whose every check fails as an invalid
workflow reference.

Cutting the tag is a human step, run from the Actions tab after the merge. No
workflow here grants `actions: write`, and a session that says it moved a tag
did not. Releasing changes nothing in any existing project: they pick a release
up when someone runs `/update-agents` there and merges what it opens.

No emoji anywhere in `.md`, `.json`, `.yml`, or `.py`. The check walks the whole
repository, not just the plugin.

## Where to read next

Do not read all of `docs/`. Read the one that matches what you are doing:

- `docs/what-is-checked.md` - the full check inventory and the four layers, before
  touching anything in `scripts/`
- `docs/versioning.md` - the pin and release model, before touching a template
  or the manifest
- `docs/checkpoint.md` - the steps only a human with account access can do
- `docs/open-questions.md` - what is still undecided, and where an answer has
  to land before an entry may be deleted
- `docs/proving-the-gate.md` and `docs/smoke-test.md` - the two runbooks
- `README.md` - the tour, if none of the above is the thing

The workflows under `.github/workflows/` carry their reasoning in comments, at
length and on purpose. A session about to change one reads that file first; it
is where the last person's mistake is written down.

## Lessons

Repository-specific lessons live here rather than in `.claude/memory/<role>.md`,
because no role runs in this repository and the memory protocol already sends a
lesson every role needs to `CLAUDE.md`. Same rules as a memory file: one line,
stated as a rule with the reason attached, proposed in a pull request, and this
section caps at 40 lines. Past the cap, rewrite rather than append.

A lesson that can be turned into a check in `scripts/` gets the check and loses
the line - the sentence is dead weight once something enforces it, and it
competes for attention with the lessons nothing enforces yet. Graduating a
lesson is the goal, and in this repository most lessons can graduate, because
the product is text files with structural rules.

<!-- Add lessons below this line, newest last. -->
