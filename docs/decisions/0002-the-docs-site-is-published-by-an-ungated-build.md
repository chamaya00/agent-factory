# ADR 0002: the docs site is published by a build the gate does not run

Date: 2026-09-20
Status: accepted

## Context

`docs/` is a GitHub Pages site as well as a folder. The source is a repository
setting - deploy from a branch, `main`, `/docs` - so every push to the default
branch triggers a Jekyll build, and there is no deploy workflow on purpose:
building from a branch needs nothing added to `.github/workflows/`, and a
system whose agents must never touch those files should not grow one it does
not need.

The gate here is the Python scripts in `scripts/`. None of them builds the
site. So this repository publishes through a program its gate does not run,
which is precisely the gap the header comment in the project template's
`ci.yml` now asks every project about. The factory had it too, and nobody had
looked.

It was not hypothetical. `what-is-checked.md` described the test scripts as
substituting the workflow expressions the runner would, and wrote that
expression out literally. Jekyll runs Liquid over a page before Markdown, so
backticks and fenced blocks protect nothing: the doubled braces were read as an
output tag, and the published page said something different from the file, for
as long as that sentence existed. Every check was green throughout, and all 45
Pages builds have succeeded, because nothing in this repository has ever read
the built site.

Two failure modes, both measured against Liquid 5.14 rather than assumed. A
workflow expression collapses to a bare dollar sign - silent, green, wrong. An
unclosed Liquid tag raises a syntax error and fails the build outright.

The bound a project has does not exist here. The scheduled sweep in
`agent-run.yml` reads the runs on the default branch tip, names any that failed,
and comments on the open objective - which is what makes an ungated deploy a
time-bounded risk rather than an unbounded one. `agent-run.yml` runs in
projects. No agents run in this repository and none should be, so nothing here
would report a failed Pages build. The Actions tab is the whole of the
notification.

## Decision

Accept the gap, and close the part of it that is cheap.

`validate_plugin.py` now refuses Liquid syntax anywhere under `docs/`, with a
raw tag as the escape hatch for the rare page that has to show the syntax. The
gate still does not build the site; it checks the one property of the source
that decides whether the build produces what the file says.

No Jekyll in the gate, and no deploy workflow.

## Consequences

Covered from now on: both measured failure modes, at authoring time, in the
pull request rather than after the merge that publishes it.

Not covered, and worth being plain about it. The gate does not build the site,
so theme resolution, the three Pages plugins the config depends on, and the
link rewriting between `.md` files are all still unverified by anything except
a person opening the page. A Pages build that fails for any reason other than
Liquid remains unreported here - a human notices, or nobody does.

One consequence is visible in the shape of this document. The literal syntax
this ADR is about cannot be written in this ADR, because the check would refuse
it and the site would mangle it; the examples live in the check's own docstring
in `validate_plugin.py`, which is Python and therefore never published. That is
the constraint working rather than a wart.

Revisit this if the site grows past plain Markdown. The moment it has layouts,
includes, or anything whose correctness is not readable in the source, the
argument for building it in the gate stops being weaker than the cost.

## Alternatives rejected

**Build the site in `guard.yml`.** The honest version, and it prices itself out.
It means a Ruby toolchain and a gem lockfile in a repository whose only
dependency is `pyyaml` and whose stated design is that there is no build. What
it buys over the check above is the residue listed under Consequences, on a site
that is 11 files of plain Markdown.

**Switch Pages to a deploy workflow.** `actions/deploy-pages` makes the build a
first-class check that branch protection could require, which is genuinely
better. It also adds a file to `.github/workflows/`, and the reasoning already
written into `docs/_config.yml` and the README holds: building from a branch
needs nothing there. Reconsider alongside the previous option, not before it.

**Set Liquid's error mode to strict.** Turns the silent corruption into a failed
build, which sounds like an improvement until you notice that a failed build
here is unreported. It converts an invisible failure into a different invisible
failure, and takes the site down to do it.

**Turn Pages off.** The site is the operating documentation, linked from the
README and written for someone reading on a phone. The gap is worth the site.
