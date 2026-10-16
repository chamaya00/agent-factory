# Phase 7: prove the gate before wiring agents

## Why this ordering

An agent pointed at a gate you do not trust produces work you have to read line
by line, which is the whole thing you were trying to avoid. Until a red check
reliably blocks a merge, every agent pull request is a manual review. Once it
does, most of them are a glance at the checks and then at the published page.

So the gate gets proven by hand, on a repo you can throw away, before any
objective is filed anywhere.

Do not skip to phase 8 because phase 7 is boring. Boring is the result you are
looking for.

## 1. Create the throwaway repo

```
/new-project chamaya00/gate-test-public
```

The command does not run start to finish on its own, by design: a cloud session
holds an installation token on repositories that already exist, so it can
neither create one nor change a setting on one. A few of its steps are handed
to you. Expect to be asked for these, in this order:

1. **Create the repository yourself**, at `github.com/new`. Name it
   `gate-test-public`, make it **public**, and tick **Add a README file**.
   Public because a private repository cannot call the factory's reusable
   workflows; the README because a repository with no commits has no default
   branch to branch from. Then tell the session it exists.
2. **Merge the pull request**, if the command opened one rather than pushing
   to the default branch - it pushes directly to a repository with nothing but
   a README in it. `workflow_dispatch` only sees workflows already on the
   default branch, so step 3 waits on this.
3. **Run the `bootstrap` workflow** from the Actions tab. It creates the nine
   labels and prints the check names you need for branch protection.
4. **Set branch protection** using the names from that run summary.

Before any of it, confirm a release tag exists for the version in the
factory's `plugins/agent-factory/.claude-plugin/plugin.json`. `/new-project`
pins the callers to that version, and a pin with no tag behind it surfaces here
as an invalid workflow reference naming nothing about a tag in another
repository. `docs/checkpoint.md` step 1 cuts one.

Then confirm by hand:

- The repo has every label listed under `labels` in its
  `.claude/agent-factory.json`, which is the set `bootstrap` creates.
- No file under `.github/workflows/` still contains `__FACTORY_VERSION__` or
  `__FACTORY_REPO__`. Both are substituted at provision time; a surviving one
  means the callers address a ref or a repository that does not exist.
- The owner in each `uses:` line is the factory you provisioned from. It is
  written from that factory's declared `repository`, so this only ever differs
  in a fork whose manifest still names upstream - in which case the project is
  running upstream's workflows rather than the ones you can edit.
- `.claude/agents/` has a file for every role. The agent job refuses to start
  without them, which is the correct behaviour and a confusing first failure
  if you were not expecting it.

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
2. **Publishing is on and its URL resolves.** Set from `docs/checkpoint.md`
   step 5, serving the default branch from its root. Until something lands at
   that root the URL 404s, which is the expected answer here and not a broken
   setup - what you are confirming is that the setting is saved and the address
   exists. There is no per-pull-request preview on this arrangement, so a pull
   request is judged on its checks and its acceptance criteria and the page is
   looked at after the merge.
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

One more, because this rule is the one an agent is most likely to trip, and it
can now be seen failing by hand.

Agents push to branches named `claude/...`, and the guard checks those whoever
opened the pull request - because a role run from a session opens its pull
request as you. So, on `gate-test-public`:

1. From the GitHub web editor, edit `.github/workflows/ci.yml` - add a comment
   line - and choose **Create a new branch**, named `claude/gate-test`.
2. Open the pull request.
3. `guard` goes red, naming the file and calling `claude/gate-test` an agent
   branch.

Then do the same edit on a branch named `gate-test-mine`. `guard` passes:
you are a maintainer, and a branch outside the agent pattern is how your own
deliberate gate change gets through. Close both without merging.

## 6. Only now point agents at it

When steps 1 to 4 are boring and repeatable, go to phase 8. There is nothing to
enable: agents run from a session on the repository, and nothing runs until an
objective is filed there.

## What to report back

For each of steps 1 to 4: worked, or needed hand-holding and what exactly. The
"needed hand-holding" list is the real backlog, and it is worth more than a
clean report.
