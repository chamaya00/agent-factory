# Phase 8: smoke test the full loop

Run this on the throwaway repo from phase 7, only after that gate is boring.

## What this test is for, and what changed

The old version of this phase filed a "favorites list" objective and judged the
result by reading the child issues, the diff, and the tests. That put the one
thing the system exists to avoid - reading an agent's output line by line - at
the centre of the test that decides whether the system works. A pass meant "a
human read it all carefully and was satisfied", which is not a pass, it is the
absence of the thing being tested.

So the objective is now something you look at. Two objectives build a personal
portfolio site, published from the repository itself, and the pass condition is
that you open the URL on a phone and see the thing described. The diff stops
being the evidence.

That only works if the criteria are written so a rendered page can settle them,
which is why `acceptance-criteria` asks for both a check and a place to look
whenever a criterion is something a user can see. Watch for that specifically in
step 2: a criterion with a test and no visible consequence sends you straight
back to reading diffs, and it will look like a perfectly good criterion.

## Before you start

Everything phase 7 asked for, still: the provisioned repository, the OAuth
secret, both Actions settings, the nine labels, branch protection on the check
names that actually reported, and a release tag matching the plugin manifest.

Then one more, and it is new. Publishing has to be set up before an objective is
filed, because an agent cannot do it:

> 1. Open `github.com/<owner>/<repo>/settings/pages`
> 2. Source: **Deploy from a branch**
> 3. Branch: the default branch, folder: **/ (root)**
> 4. **Save**

Root rather than `/docs`, because `docs/` already holds `decisions/`, `design/`,
and `research/` from provisioning, and those are not the website.

Three things follow from that choice, and each one is a cycle if it surprises
you later:

- **What is committed is what is live.** There is no deploy step and no build
  server. Whatever HTML sits at the root of the default branch is the site, so
  the build output is committed rather than ignored.
- **The site is served from a subpath**, `<owner>.github.io/<repo>/`, not from
  the domain root. Links written as `/assets/site.css` resolve to the wrong
  place and 404. This is the single most likely way objective 1 spends an
  attempt, which is why the objective names it.
- **There is no per-pull-request preview.** Deploying from a branch publishes
  merged work only. You review the pull request against its criteria and its
  test names, merge, then look at the site. Anything wrong on the page goes back
  round as a new issue, which is the loop working rather than a wasted merge.

Set publishing up now rather than after the first pull request. The URL will
404 until something lands at the root, and a 404 you were expecting is
information; the same 404 discovered in step 6 reads as a broken run.

## The two objectives

Two, run back to back, rather than one large one. Each splits comfortably inside
the orchestrator's 2-to-5 range, and running the loop twice is closer to how the
thing gets used than running it once - the second decomposition reads a memory
file with something in it, which the first one cannot.

File the first as an issue titled "Portfolio site: shell and about", labelled
`objective`:

> I want a personal portfolio site published from this repository at its GitHub
> Pages URL. A home page and an about section, with navigation between them,
> readable on a phone. Pages serves this repository's default branch from the
> root, so whatever is committed there is what is live - there is no deploy step
> and no build server. The site is served from a subpath, not the domain root,
> so every link has to work from there. No accounts, no backend, no analytics.

The second waits until the first is merged and visible. Title it "Portfolio
site: projects and posts", label it `objective`:

> The site needs a projects section and a posts section. Each project and each
> post is a content file in the repository: adding one file and nothing else
> should make it appear in its section, and on the home page as a recent entry.
> Every section needs an empty state for when there is no content yet.

Neither objective names a framework, a generator, or a file format. Those are
decisions, they belong to the roles, and watching them get made and recorded is
a large part of what this test is for. If you specify them here, you have tested
your own typing.

Nothing runs yet. `objective` alone does not start anything: the run label does,
and only a human applies it.

## The run, step by step

Steps 1 to 7 describe objective 1. Objective 2 repeats them, and the notes at
the end say where it differs.

**1. You label the objective `agent:queued`.**

**2. The orchestrator comments a plan, then creates its children.**

The count is not a pass condition. `orchestrator.md` allows between two and
five, and previous real runs sat at both ends of that range with a stated
reason. Judge the split by reading the criteria, not by counting the issues.

Expect something close to three or four here: one `role:researcher` child for
how a site gets published from the root with no deploy step and what generates
the HTML, one `role:designer` child for navigation and states, and one or two
`role:engineer` children to build it.

Watch for: criteria that a rendered page can settle. Each one that a user can
see should name both the check and where you would look. "The about page renders
the bio" is a criterion. "The about page is well structured" is not, and it will
cost you a cycle to discover that after the fact rather than now.

Watch for: the plan comment ending with how you will see the result. The
orchestrator is asked to name that whenever accepting an objective means looking
at something, so its absence here is a finding about the role, not about the
project.

Watch for: grandchildren. There should be none. Anything needing a further
split should be labelled `needs-decomposition` and left alone.

**3. You queue the research child.**

Pick the one with no dependencies. The plan comment should say which those are.

Watch for: an ADR in `docs/decisions/` landing with the research, since choosing
how the site is generated is a dependency decision and the house rules require
one in the same diff. Research that recommends a dependency without an ADR is
the failure to catch here.

**4. You queue the design child.**

Watch for: a document in `docs/design/` that enumerates the states, not just the
happy path - what the home page looks like with no content in it, what
navigation does on a narrow screen. The empty state is the one that gets skipped
and the one objective 2 will need.

**5. You queue the engineer child. It opens a pull request and the checks pass.**

Queue the smallest engineer child first, whatever the plan says the order is,
and read `num_turns` in the run's result block before queueing a larger one.
This is the first engineer run the system has had, and the turn cap has never
been tested against a role that builds, runs tests, and reacts to a red check.
If it lands near the cap, raise it in the template before objective 2 rather
than after.

Watch for: whether the tests map onto the acceptance criteria one to one. Tests
that pass without testing the criteria is the failure mode here, and it looks
identical to success on the checks tab. Read the test names against the criteria
list - that is a minute, and it is not the same as reading the diff.

Watch for: a test that regenerates the site and compares it against the
committed HTML. Without one, content and markup drift apart silently and the
published site goes stale while every check stays green. If the engineer does
not write it, that is the most valuable thing you will learn in this phase.

Watch for: the issue moving through `agent:running` to `agent:review` on its
own. If the labels do not move, the App token or the labels are wrong, not the
agent.

**6. You comment a revision, it pushes a fix.**

Before merging, comment on the pull request starting with `@claude`, asking for
one specific change. Without the trigger phrase nothing happens, by design.

The page is not visible yet, so the basis for the revision is the criteria list
against the test names, or the design document against what the pull request
says it built. That is a fair test of the review surface this arrangement
actually gives you: if you cannot find anything to ask for without opening the
diff, say so in the report, because that is a finding about the criteria.

Watch for: a new commit on the same branch, not a new pull request. And watch
the attempt counter - this is attempt 2 of 3 on that issue.

**7. You merge, then open the site.**

Give it a minute; publishing from a branch is not instant. Then open
`<owner>.github.io/<repo>/` on the device you would actually use.

This is the step the whole redesign exists for. Go down the acceptance criteria
with the page in front of you. Do not open the diff.

Something being wrong on the page is not a failed run. With no per-pull-request
preview this is the first time anyone could have seen it, so file what you saw
as a new issue, let it go round again, and count the round trip in the report.
A loop that fixes a visible problem in one pass is the result you want; needing
three is the finding.

**8. `/retro` proposes a one-line memory entry as a pull request.**

Run `/retro` from a Claude session against the repo. It should open a pull
request touching only `.claude/memory/`, with a line naming something specific
that happened during steps 1 to 7.

Watch for: a lesson with no incident behind it. "Write clear tests" is a
preference, not a lesson, and it should not survive. Watch for the file staying
inside 40 lines - `project-guard` fails the pull request if not.

### Where objective 2 differs

Run it after objective 1 is merged and visible, not in parallel.

The acceptance test writes itself here, and it is the sharpest one in the whole
phase: once the projects and posts work has merged, add one content file by
hand, through the web UI, and confirm it appears on the site. Nothing else
changes, and no agent runs. If making an entry appear needs a code change as
well, the content-file criterion was not met, whatever its tests said and
however green the checks were.

Step 2 is worth watching more closely the second time. The orchestrator now has
a memory file with lessons in it and a repository with a shape. A decomposition
that ignores both - proposing a structure the site does not have - says the
memory protocol is not doing anything, which is a finding worth more than the
objective itself.

## Reporting back

For each of the eight steps: worked, or needed hand-holding and what exactly.

Then, separately, four things that are worth more than the pass or fail:

- **How much of the diff you had to read.** This is now the headline number, not
  a footnote. Nothing, and the design works. All of it, and either the criteria
  were not visible enough or the gate is not trusted yet, and the report should
  say which.
- **`num_turns` for each engineer run.** `docs/open-questions.md` has an open
  entry on whether the cap is enough, and there has never been data behind it.
  This phase is where that entry gets answered or deleted.
- **How many attempts each issue took.** Anything hitting 3 means the
  orchestrator scoped it wrong, and the fix belongs in the orchestrator's role
  definition or in that repo's memory, not in trying again.
- **What you found yourself typing more than once.** That is the next command.

## The likely failure modes

Ranked by how often they bite, so you can recognise them rather than debug them:

1. `CLAUDE_CODE_OAUTH_TOKEN` missing from this repo. Every run fails
   immediately at auth. Secrets are per repo.
2. "Allow Actions to create and approve pull requests" off. The run succeeds and
   no pull request appears.
3. **Links written from the domain root.** The site lives at a subpath, so
   `/assets/site.css` and `/about/` resolve above the site and 404. The page
   loads unstyled, or navigation goes nowhere, and every check stayed green
   because nothing tested the published URL.
4. **Jekyll processing the site.** Publishing from a branch runs the files
   through Jekyll unless a `.nojekyll` file sits at the root. Anything under a
   path starting with an underscore is dropped, and the symptom is a 404 on a
   file that is plainly there in the repository.
5. **The site went stale rather than wrong.** Content changed, the HTML was not
   regenerated, every check passed. This is what the regeneration test in step 5
   is for, and its absence is invisible until the day it matters.
6. Acceptance criteria too vague, so the engineer builds the wrong thing and it
   passes its own tests. Fix the orchestrator's output, not the engineer.
7. The run label applied to the parent objective again after the split, which
   re-runs the orchestrator and produces duplicate children.
8. Required check names in branch protection drifting from the job names, so
   nothing is actually required any more.
