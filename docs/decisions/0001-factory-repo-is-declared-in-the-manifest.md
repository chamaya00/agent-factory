# ADR 0001: the factory's own repository is declared, not inferred

Date: 2026-09-20
Status: accepted

## Context

The four caller workflows a project receives address the factory by a literal
owner:

```
uses: chamaya00/agent-factory/.github/workflows/ci.yml@__FACTORY_VERSION__
```

The version is a placeholder and the owner was not. So anyone who forked this
repository and ran `/new-project` provisioned repositories that called
*upstream's* reusable workflows. Their own factory edits never reached their own
projects, and upstream's releases reached them whether or not they wanted them.
Nothing reported it: every check green, every workflow resolving, every run
succeeding - just not running the code the person thought they were running.

The same literal sat inside the check that was supposed to police these lines.
`check_template_pins()` matched `uses: chamaya00/agent-factory/...@(\S+)` and
refused any ref that was not the placeholder. In a fork with the owner changed,
that pattern matched nothing, so the check did not fail - it went quiet. A fork
could hardcode `@v1.2.0` in all four callers and the gate stayed green. A check
that stops matching is worse than one that fails, because the build stays green
while the protection is gone.

Replacing the literal with `__FACTORY_REPO__` is the easy half. The decision is
where the substituted value comes from, and it is a category change in how a
provisioned repository resolves its workflows, so the house rules want it
recorded rather than settled inside a pull request.

## Decision

The factory declares its own `owner/repo` in the plugin manifest, and
provisioning substitutes that declaration.

The field already exists. `plugins/agent-factory/.claude-plugin/plugin.json`
carries `"repository": "https://github.com/chamaya00/agent-factory"`, so a fork
edits one line it already had reason to edit, and no new concept is introduced.
It is also the file the release tag is read from, which keeps *which factory*
and *which release* in one place rather than two.

The checkout's `origin` remote is not the source. It is a witness.
`check_factory_repo_is_declared()` compares the two whenever a remote is
readable, and fails when they disagree.

## Consequences

A fork now gets projects that call the fork. Editing one manifest line is the
whole of the migration, and the placeholder cannot be forgotten silently
because the string is still sitting in the file to be found - the same
reasoning already applied to `__FACTORY_VERSION__` and `__PROJECT_OWNER__`.

`check_template_pins()` is anchored on the shape of a reusable workflow
reference - `<something>/.github/workflows/<file>@<ref>` - rather than on
anybody's account. It now fails on a hardcoded owner, a hardcoded ref, and a
reference carrying no ref at all, in a fork exactly as here. The quiet mode is
gone: there is no owner a template can name that this check does not read.

The cost is the cross-check's blast radius. A fork that has not yet edited the
manifest has a red build from its first run, which is the intended signal but
is still a red build on a clone somebody has not touched yet. The message names
the file, the field and the fix in one line, which is the most that can be done
about it. A pull request from a fork *to this repository* is unaffected, because
the checkout for that run is this repository and `origin` agrees with the
manifest.

What this rules out later: inferring the factory from anything ambient - an
environment variable, the session's working directory, the marketplace entry a
plugin was installed from. Those were never candidates, but the reason is worth
writing down, which is that none of them is reviewable in a diff.

Transferring this repository to an organization now changes a declared value in
a pull request rather than a literal in four templates. Repositories already
provisioned keep calling the old location until `/update-agents` moves their
pins, which is the pinning working as designed rather than a migration failure.

## Alternatives rejected

**Infer it from `git config --get remote.origin.url` at provision time.**
Correct by construction for the ordinary fork, and it needs no migration step
at all - which is a real advantage this loses. It lost because the value is
then invisible: nothing in a diff says which factory a project will be
provisioned against, and a session run from a detached, mirrored, or
remote-less checkout substitutes something unhelpful with nothing to review it
against. The manifest keeps the answer in a file somebody can read. The
remote's one genuine advantage - that a fork cannot forget - is recovered by
using it as the cross-check instead of the source, which is where it ended up.

**A new dedicated field, separate from `repository`.** One more thing for a
fork to remember, and forgetting it reproduces exactly the bug being fixed.
`repository` already has to be right, so reusing it means a fork that keeps its
manifest honest gets this for free.
