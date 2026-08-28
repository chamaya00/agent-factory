---
name: house-rules
description: The non-negotiable process rules for any repo built by the factory - acceptance criteria before work, tests before merge, an ADR for schema and dependency changes, and the three-strike rule. Use at the start of any agent run and whenever deciding whether a piece of work is ready to start or ready to merge.
---

# House rules

These apply to every repository this system touches. They are process, not preference. If a rule and a project convention disagree, the project convention wins on style and these rules win on process.

## Before work starts

Every child issue has acceptance criteria before anyone opens an editor. No criteria means the work is not ready, and starting anyway produces a diff nobody can judge. Ask for criteria instead of inferring them.

Every issue names one role. Work that needs two roles is two issues.

## Before merge

Tests before merge. Every acceptance criterion has a test that would fail if the criterion were violated. A criterion covered only by a manual check is not covered.

The checks are the gate, and the gate is deterministic. Never skip, disable, or quarantine a test to get to green, and never widen a pull request to get around a failing check.

A pull request changes one issue's worth of code. Things noticed along the way become issues, not commits.

## Decisions

Any change to a schema, a data shape, or a dependency gets an ADR in `docs/decisions/`, in the same diff that makes the change. Four sections: context, decision, consequences, alternatives rejected. A dependency added without an ADR is a dependency nobody can remove later, because nobody knows why it is there.

## The three-strike rule

Three failed attempts on one issue means the issue was scoped wrong. It does not mean try harder. Stop, comment what was tried and how each attempt failed, label the issue `needs-decomposition`, and wait for a human.

The same applies to a check that fails three times for three different reasons: the problem is the scope, not the fix.

## What agents never touch

Workflow files, CODEOWNERS, and branch protection are outside every agent's reach. A system that can rewrite its own gates has no gates. An agent that believes a workflow needs to change says so in a comment and stops.
