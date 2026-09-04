# Project context

<!-- Replace the bracketed lines. Everything else is the standing arrangement. -->

## What this is

[One sentence: what this product does and for whom.]

## Stack

[Language, framework, data store, hosting. Name the versions that matter.]

## Publishing

This repository publishes a site from `docs/` on the default branch, through
GitHub Pages. Deploy from a branch, no deploy workflow: agents here may never
touch `.github/workflows/`, so hosting that needs a workflow would put the
deployment permanently out of their reach.

Out of the box that site is the project's own records - `docs/decisions/`,
`docs/research/`, `docs/design/` - rendered as pages, plus a placeholder at the
root. Nothing is built to make that work.

If this project publishes something of its own from `docs/`, say so here, and
say which parts of `docs/` are generated. A generated site should delete
`docs/_config.yml` and add `docs/.nojekyll`, so Pages serves the committed
bytes rather than running Jekyll over them, and the generator must leave the
three record directories alone.

**Anything generated into `docs/` is generated, never hand-edited, and a test
proves the committed copy matches a fresh build.** Without that test, a stale
page is invisible; with it, a stale page is a red check.

## Commands

- Install: [command]
- Dev: [command]
- Typecheck / lint / test / build: `npm run typecheck`, `npm run lint`, `npm run test`, `npm run build`

The four scripts above are what CI runs. If one is renamed here, rename it in
`.github/workflows/ci.yml` in the same commit, or the gate silently stops
checking that thing.

## How work moves

Objectives become issues labelled `objective`. The orchestrator splits one into
2-5 child issues, each with acceptance criteria and one role label. A human
labels a child `agent:queued` when it is ready to run. Nothing runs itself.

Labels: `objective`, `agent:queued`, `agent:running`, `agent:review`,
`agent:blocked`, `needs-decomposition`, `role:researcher`, `role:designer`,
`role:engineer`.

## Standing rules

Acceptance criteria before work starts. Tests before merge. An ADR in
`docs/decisions/` for any schema or dependency change, in the same diff.

Everything worth verifying is verified by the test suite or the CI gate. A
criterion that can only be checked by a person looking at the result is a
criterion that will pass by accident one day. What is left for human eyes is
whether the thing is any good, which is a different question and not one a
check was ever going to answer.

Three failed attempts on one issue means the issue was scoped wrong. Stop and
ask for decomposition rather than trying a fourth time.

Never edit `.github/workflows/`, `CODEOWNERS`, or anything under a plugin
directory. If the work seems to need it, say so in a comment and stop.

## Memory

Lessons specific to this repository live in `.claude/memory/<role>.md`, one file
per role, 40 lines each. They are proposed in a pull request, never written
silently. A lesson that has graduated into a test, a lint rule, or a type gets
deleted - the check enforces it now, and the sentence is competing for attention
with the lessons nothing enforces yet.
