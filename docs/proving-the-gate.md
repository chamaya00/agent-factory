# Phase 7: prove the gate before wiring agents

## Why this ordering

An agent pointed at a gate you do not trust produces work you have to read line
by line, which is the whole thing you were trying to avoid. Until a red check
reliably blocks a merge, every agent pull request is a manual review. Once it
does, most of them are a glance at a preview URL.

So the gate gets proven by hand, on a repo you can throw away, before
`agent-run.yml` is enabled anywhere.

Do not skip to phase 8 because phase 7 is boring. Boring is the result you are
looking for.

## 1. Create the throwaway repo

```
/new-project chamaya00/gate-test-public
```

The command does not run start to finish on its own, by design: a cloud session
holds an installation token on repositories that already exist, so it can
neither create one nor change a setting on one. Four of its steps are handed to
you. Expect to be asked for these, in this order:

1. **Create the repository yourself**, at `github.com/new`. Name it
   `gate-test-public`, make it **public**, and tick **Add a README file**.
   Public because a private repository cannot call the factory's reusable
   workflows; the README because a repository with no commits has no default
   branch to branch from. Then tell the session it exists.
2. **Tick the two Actions settings** at
   `github.com/chamaya00/gate-test-public/settings/actions` - "Read and write
   permissions" and "Allow GitHub Actions to create and approve pull requests".
   This is the one that fails silently: with it off, every later step appears
   to work and no pull request ever appears.
3. **Merge the pull request** the command opens with the caller workflows and
   project files. `workflow_dispatch` only sees workflows already on the
   default branch, so nothing in step 4 is possible before this merges.
4. **Run the `bootstrap` workflow** from the Actions tab. It creates the nine
   labels and prints the check names you need for branch protection.
5. **Set branch protection** using the names from that run summary.

Before any of it, confirm `v1` points at the tip of the factory's `main`. The
callers this command writes all resolve `@v1`, and the tag falls behind on
every merge there - `docs/checkpoint.md` step 0 is the three taps that move it.
A stale tag surfaces here as an invalid workflow reference naming nothing about
a tag in another repository.

Then confirm by hand:

- The Actions settings above are actually ticked. Look, do not remember.
- The repo has all nine labels.

Branch protection stays a human step on purpose, here and forever: setting it
needs an administration token, and an identity that can set a gate can remove
one.

## 2. Add one component and one test

Deliberately trivial. This is a test of the gate, not of the code.

Something that renders a string, and a test asserting it renders that string.
Whatever the stack's default scaffold gives you is fine, as long as
`npm run typecheck`, `lint`, `test`, and `build` all exist and pass locally.

Commit straight to `main` this once, before protection is on, so `main` starts
green. A branch protection rule added while `main` is red blocks the pull
request that would fix it.

## 3. Open a pull request by hand

Change the string. Update the test to match. Open the pull request from the
GitHub web UI - it can edit a file and open a pull request in one flow, which is
the whole loop from a phone.

Confirm four things, in this order:

1. **Checks run.** `ci / typecheck, lint, test, build` and `guard / memory cap
   and protected paths` both appear on the pull request and both go green.
2. **A preview URL appears.** As a comment or a check. Open it. It should show
   the changed string.
3. **The check names match branch protection.** Repo Settings, Branches, the
   `main` rule: the required checks listed there are exactly the names from
   step 1. They follow the job names, so a renamed job silently stops being
   required - which reads as green when it is really absent.
4. **Merge is blocked.** Merge it and confirm it merges cleanly.

## 4. Prove red blocks merge

This is the step people skip, and it is the only one that actually proves
anything. A gate that has never refused anything is not known to be a gate.

Open a second pull request that breaks the test on purpose - assert the string
is something it is not.

Confirm:

- `ci` goes red.
- The merge button is disabled, with "Required statuses must pass".
- You cannot merge it from the mobile web UI either. Check this specifically:
  the mobile layout puts the merge button somewhere different and it is worth
  seeing the block with your own eyes on the device you will actually use.

Then close that pull request without merging.

## 5. Prove the containment guard

One more, because this rule is the one an agent is most likely to trip.

Open a pull request that adds a line to `.github/workflows/ci.yml`. Since you
are the repository owner, `project-guard` will pass it - that is correct
behaviour, and it is why the check reads the pull request author.

To see it fail you need an author who is not a maintainer, which in practice
means an agent pull request. So do not force this one now: note it, and confirm
it in phase 8, when the engineer opens its first pull request. If an agent ever
does touch a workflow file, this check is what catches it.

## 6. Only now enable agent-run

When steps 1 to 4 are boring and repeatable, add `CLAUDE_CODE_OAUTH_TOKEN` to
`gate-test-public` and let `agent-run.yml` stay as it is - it is already in
the repo from `/new-project`, and it does nothing until an issue carries the
right labels.

Then go to phase 8.

## What to report back

For each of steps 1 to 5: worked, or needed hand-holding and what exactly. The
"needed hand-holding" list is the real backlog, and it is worth more than a
clean report.
