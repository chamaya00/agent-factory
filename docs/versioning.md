# How a change here reaches a project

The thing to know first: it does not, on its own. Nothing you do in this
repository changes what any project runs. A project moves when somebody opens a
pull request there and merges it.

That is the whole design, and everything below is the mechanics of it.

## Four things travel, separately

| What | Lives in a project as | Moves when |
|---|---|---|
| Role, skill, and command definitions | copies under `.claude/agents/`, `.claude/skills/`, and `.claude/commands/` | `/update-agents` opens a pull request there and it merges |
| Workflows (the gates) | four thin callers pinned to a release tag | the same pull request bumps the pins |
| Shared process prose | the managed block in `CLAUDE.md`, between the `agent-factory:begin` and `agent-factory:end` markers | the same pull request replaces the block |
| Repo-specific lessons | `.claude/memory/<role>.md` | never - these are written in that repository and stay there |

The second-to-last row is the newest and was missing for a long time, which
cost something worth writing down. `CLAUDE.md` was skipped by `/update-agents`
entirely, on the stated grounds that it describes the product rather than the
process. Measured against a real project that was true of about half the file:
its stack and its commands are the repository's own, and its account of how work
moves, what drives an objective, the standing rules and the labels came from
here.

With two ownerships interleaved in one file and no boundary between them,
skipping all of it was the only safe thing the command could do - so every
release that changed process desynchronised every project's description of
itself, silently, and the drift stayed invisible until somebody read a sentence
that contradicted the roles they were watching run. That is how a project came
to be running roles that open their own pull requests while its `CLAUDE.md`
still told the reader those roles could not.

The markers are the boundary that makes the file updatable without overwriting
what belongs to the repository. Inside them is ours and gets replaced wholesale;
outside them is the project's and is never touched. A repository that predates
the markers keeps working - the guard passes a file that has none - and gets
them on its next update, which is the one step in that command that shows a
person what it is about to replace before it does it.

The last row never leaves a repository, and the first row is the reason it
does not have to. The roles are copied in rather than fetched at run time, so a
project's agents behave the way they behaved the day it was provisioned, and
its lessons stay next to the roles that learned them.

The commands are copied for a second reason as well: a session only loads
commands that are in the repository it cloned. A marketplace named in
`.claude/settings.json` is ignored until the folder is trusted for project
plugins, and a cloud session has nobody to answer that prompt, so a project
that relied on one would open with no `/retro`, `/decompose`, or
`/update-agents` at all.

## Cutting a release

1. Open a pull request here that bumps `version` in
   `plugins/agent-factory/.claude-plugin/plugin.json`.
2. Merge it.
3. Actions tab, `release.yml`, **Run workflow**, leave the input empty.

The tag name comes from that manifest, not from the input. This is not
ceremony: `/update-agents` compares the tag it is moving to against the version
recorded in `.claude/agent-factory.json`, so a tag whose name got ahead of the
manifest would ship new files under a version that claims to already be there.
Tying the two together makes that unrepresentable rather than documented.

Release tags never move. `release.yml` refuses a tag that already exists, and
there is no force path. If a release was wrong, the fix is the next release -
projects pinned to the bad one stay on it until somebody moves them, which is
the correct behaviour, not a problem to route around.

## Taking a release into a project

In that repository:

```
/update-agents v1.3.0
```

It reads the factory at that tag, compares it against what that repository has,
and opens one pull request: changed roles, skills, and commands, the four
workflow pins moved together, and `.claude/agent-factory.json` recording the
new version. Omit the version and it uses the latest release.

There is nothing to update locally first. The command reads the factory
repository at the tag you name rather than an installed copy, so what it
proposes depends on the tag and not on the container it happened to run in.

Read the diff, merge it or do not. Repositories you do not run this in stay
exactly where they are, indefinitely. That is allowed and it is not drift -
a repository that is finished does not need the newest roles.

One thing about that pull request is worth knowing: its own checks run at the
*old* pin, because a caller change only takes effect once it is on the default
branch. So green there means the diff is well-formed, not that the new release
passes on that repository. The first real run at the new pin is the next pull
request after it merges.

## Why not a moving `v1`

It was one before. A caller holding `@v1` resolves it fresh on every run, so
moving the tag changed what every project executed, immediately, with no pull
request in any of them - including projects whose author had not touched them
in months and had no idea anything had changed. That is a deploy to everything
at once, triggered by a merge here, reviewed nowhere.

It also failed in the boring direction. The tag fell behind on every merge, and
a project provisioned against a stale tag addressed a workflow that was not in
that tree - which surfaced as an invalid workflow reference, in the project
repo, naming nothing about a tag in a different repository.

Pins cost one pull request per project per update. They buy the property that
nothing changes under anyone, and that every change arrives as a diff somebody
read.
