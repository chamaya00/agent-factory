# How a change here reaches a project

The thing to know first: it does not, on its own. Nothing you do in this
repository changes what any project runs. A project moves when somebody opens a
pull request there and merges it.

That is the whole design, and everything below is the mechanics of it.

## Three things travel, separately

| What | Lives in a project as | Moves when |
|---|---|---|
| Role, skill, and command definitions | copies under `.claude/agents/`, `.claude/skills/`, and `.claude/commands/` | `/update-agents` opens a pull request there and it merges |
| Workflows (the gates) | four thin callers pinned to a release tag | the same pull request bumps the pins |
| Repo-specific lessons | `.claude/memory/<role>.md` | never - these are written in that repository and stay there |

The third row never leaves a repository, and the first row is the reason it
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
