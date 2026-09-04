---
name: acceptance-criteria
description: The format for writing acceptance criteria that are observable and checkable, used when creating child issues, judging whether an issue is ready to start, or deciding whether a pull request actually satisfies its issue.
---

# Acceptance criteria

A criterion is a statement that a test can prove false. If nobody can say precisely what would make it fail, it is an aspiration, and aspirations cannot gate a merge.

## The format

Each criterion is one line, in the form:

`Given <starting state>, when <action>, then <observable result>.`

Attach to each criterion the check that proves it: a test name or a command. If the criterion is something a user can see, attach both - the check, and where a human looks to confirm it with their own eyes.

Both, rather than either, because each one alone fails in its own direction. A check nobody can see passing sends the reviewer back to reading the diff, which is the thing checks exist to replace. A screen nobody tested regresses quietly, with nothing going red.

## The test

Read the criterion and ask: could two reasonable people disagree about whether it is met? If yes, rewrite it.

Good: "Favorites persist across a tab switch, verified by a test that reloads the page and asserts the list length."

Bad: "Favorites work well."

Good: "An empty favorites list shows the empty state, not a spinner, verified by a component test."

Bad: "Handle the empty case gracefully."

Good: "Given three entries in the content directory, when the page is built, then all three are listed in date order - covered by `lists entries newest first`, and visible as three rows on the entries page."

Bad: "The entries page looks right." Nothing here says what a reviewer would be looking at, so two people can disagree about whether it passed.

## Coverage

Criteria cover the states, not just the happy path. For anything a user touches, that means at least: the normal case, the empty case, and the failure case. An issue whose criteria only describe success is an issue that will ship a broken error path.

Criteria describe behaviour, not implementation. "Uses a reducer" is not a criterion; it is a decision, and it belongs in an ADR.

## How many

Between two and six per issue. One criterion means the issue is a task and probably belongs inside another issue. More than six means it is two issues wearing a coat.

## Readiness

An issue is ready to start when every criterion is observable, checkable, and covered by a named check. An issue that fails that test does not get worked on - it gets sent back with the specific criterion that needs rewriting quoted in the comment.
