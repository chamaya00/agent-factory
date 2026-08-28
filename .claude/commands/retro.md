---
description: Propose memory updates for this repository as a pull request, one file per role.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__github__list_issues, mcp__github__issue_read, mcp__github__list_pull_requests, mcp__github__pull_request_read, mcp__github__create_branch, mcp__github__push_files, mcp__github__create_pull_request
---

Propose what this repository has learned, as a pull request against `.claude/memory/`.

Follow the memory-protocol skill exactly. The parts that matter most here:

1. Read the recent history first - merged pull requests, closed issues, comments where something went wrong and got corrected. A retro that only reads the current code finds nothing, because the lessons are in what had to be fixed.
2. A lesson is one line, specific to this repository, stated as a rule with the reason attached. "Be careful with migrations" is not a lesson. "Run migrations against a copy of prod before merging - the staging seed data hides the null-name case" is.
3. Put each lesson in the file for the role that needed it. A lesson every role needs belongs in `CLAUDE.md`, not in four memory files.
4. Before adding anything, delete what has graduated. A lesson now enforced by a test, a lint rule, or a type is dead weight, and it competes for attention with the lessons nothing enforces yet.
5. Respect the 40-line cap. Past it, rewrite the file: merge two lessons that say the same thing, drop the one that has stopped being relevant, tighten what survives. If nothing can be merged or dropped, the new lesson was not worth more than what is already there - do not add it.

Open one pull request with the diff and nothing else in it. In the body, say for each proposed line what specifically happened that produced it, with a link. A lesson with no incident behind it is a preference, and preferences do not belong in memory.

Never write these files outside a pull request.
