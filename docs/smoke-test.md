# Phase 8: smoke test the full loop

Run this on the throwaway repo from phase 7, only after that gate is boring.

## What comes out of it

A working website, published at the project's Pages URL, that the agent team
built from one sentence of objective.

That is the whole design of this phase. Earlier drafts had the smoke test
produce a headless package and judged it by reading the diff and the issue
bodies, which put the one thing this system exists to avoid - reading an
agent's output line by line - at the centre of the test that decides whether
the system works. A site you can open on a phone is either right or wrong in
three seconds, and everything underneath it is provable by `npm test` and the
gate.

So the split of labour is fixed, and worth holding to:

- **`npm test` and CI verify everything mechanical.** Content parses, pages
  generate, links resolve, the committed output matches a fresh build, the
  empty case renders. If a fact about the site can be checked, it is checked
  there, not by you.
- **You verify the two things a check cannot.** Whether the site is any good to
  look at, and whether what got built is what you asked for.

If you find yourself checking anything else by hand, that is a missing test,
and it is worth more than the smoke test result.

## Before you start

Everything in `docs/what-is-checked.md`, layer 4, plus one setting specific to
this phase: **Pages has to be on.** Settings, Pages, "Deploy from a branch",
`main`, `/docs`. It is a repository setting, like branch protection and for the
same reason - an identity that can publish a site can publish anything.

Turn it on before the first agent run and confirm the placeholder page loads.
That way a blank site later means the agents did not finish, rather than that
Pages was never switched on. Those are different problems and they look
identical if you skip this.

## The objective

File this as an issue, titled "Portfolio site", and label it `objective`:

> I want a personal portfolio site published at this repository's Pages URL,
> with a projects section and a posts section. Adding or editing a project or a
> post should be a matter of writing one plain text file in the repository and
> running one command - no CMS, no accounts, no database - so a coding agent
> connected to this repository can do it in a single change. The site has to
> work with JavaScript disabled.

Every clause in that is load-bearing, which is what makes it a good test of the
orchestrator rather than of your patience:

- **projects and posts** are two sections, which is the natural seam for
  splitting the work.
- **one file and one command** is the requirement that decides the
  architecture, and it is checkable by a test rather than by opinion.
- **works with JavaScript disabled** rules out rendering in the browser, which
  is what forces the generated-and-committed HTML that lets CI prove the exact
  bytes Pages will serve.

Nothing runs yet. `objective` alone does not start anything: the run label
does, and only a human applies it.

## The six steps, and what to watch for

**1. The orchestrator comments with a plan and creates its child issues.**

Label the objective `agent:queued`. The orchestrator should comment its plan
first, then create the children.

The count is not a pass condition. `orchestrator.md` allows between two and
five, and both earlier runs sat at the ends of that range with a stated reason.
Judge the split by reading the criteria, not by counting the issues.

Watch for: a split along the seams the objective actually has - the content
pipeline, then the two sections, then how it looks. A split that gives one
child "the whole site" and another "tests" has not understood the objective.

Watch for: criteria that name a check. "The posts index lists newest first,
proved by a test over a fixture directory" is a criterion. "Posts look good" is
an aspiration, and it is a failure of this step even though an issue got
created.

Watch for: grandchildren. There should be none. Anything needing a further
split should be labelled `needs-decomposition` and left alone.

**2. You label one child `agent:queued`.**

Pick the one with no dependencies - the content model and the generator, most
likely. The plan comment should say which those are.

Watch for: an ADR landing with it. The content schema is a schema, and how
Markdown becomes HTML is either a dependency or hand-rolled code; the standing
rules require an ADR in the same diff either way. `docs/decisions/0003` in the
project deliberately leaves both open so that this run has to make them.

**3. The engineer opens a pull request and the checks pass.**

There is no preview URL, and there is deliberately no attempt to build one.
Pages publishes from `main`, so the live site updates at step 5, and before
then the gate is what you have. That is the trade for having no deploy workflow
and no third-party preview account, and it is the right way round: the checks
are what should be trusted, not a screenshot.

Watch for: the generated site in the diff. It should be there, and you should
not read it. `docs/` is derived, and the regeneration test is what makes it
safe to skip - if that test is missing, the whole arrangement is unsound and
this is the moment to catch it.

Watch for: whether the tests map onto the acceptance criteria one to one. This
is still the failure mode that looks identical to success on the checks tab.

Watch for: the issue moving through `agent:running` to `agent:review` on its
own. If the labels do not move, the App token or the labels are wrong, not the
agent.

**4. You comment a revision, it pushes a fix.**

Comment on the pull request starting with `@claude`, asking for one specific
change. The empty state is the one worth asking for: a portfolio with no posts
yet should say so rather than render an empty page.

Watch for: a new commit on the same branch, not a new pull request. And watch
the attempt counter - this is attempt 2 of 3 on that issue.

**5. You merge, then you open the site.**

This is the step the whole phase is for. Merge, wait for the Pages deployment,
and open the URL on a phone.

Look at it the way a stranger would. Does it read as a portfolio? Do the two
sections work? Does a post open? Turn JavaScript off and load it again - it
should not change at all.

Then add a post yourself: write one Markdown file, run `npm run build`, commit.
If that takes more than one file and one command, the central requirement was
not met, whatever the tests say. That is the one criterion worth checking by
hand, because it is the one the whole objective was about.

**6. `/retro` proposes a one-line memory entry as a pull request.**

Run `/retro` from a Claude session against the repo. It should open a pull
request touching only `.claude/memory/`, with a line naming something specific
that happened during steps 1 to 5.

Watch for: a lesson with no incident behind it. "Write clear tests" is a
preference, not a lesson, and it should not survive. Watch for the file staying
inside 40 lines - `project-guard` fails the pull request if not.

## Reporting back

For each of the six: worked, or needed hand-holding and what exactly.

Then, separately, three things that are worth more than the pass or fail:

- **How many attempts did each issue take.** Anything hitting 3 means the
  orchestrator scoped it wrong, and the fix belongs in the orchestrator's role
  definition or in that repo's memory, not in trying again.
- **What you checked by hand that a test should have checked.** Every one of
  those is a missing test, and this is the only time you will notice it.
- **What you found yourself typing more than once.** That is the next command.

## The likely failure modes

Ranked by how often they bite, so you can recognise them rather than debug
them:

1. `CLAUDE_CODE_OAUTH_TOKEN` missing from this repo. Every run fails
   immediately at auth. Secrets are per repo.
2. "Allow Actions to create and approve pull requests" off. The run succeeds
   and no pull request appears.
3. Pages not switched on, or pointed at the wrong branch or folder. The checks
   are green and the URL 404s. Confirming the placeholder page before step 1 is
   what separates this from "the agents built nothing".
4. Generated output committed stale, because the agent edited `content/` and
   did not rebuild. This should be a red check. If it merged green, the
   regeneration test is missing or is asserting against itself, and that is a
   worse finding than the stale page.
5. Acceptance criteria too vague, so the engineer builds the wrong thing and it
   passes its own tests. Fix the orchestrator's output, not the engineer.
6. The run label applied to the parent objective again after the split, which
   re-runs the orchestrator and produces duplicate children.
7. Required check names in branch protection drifting from the job names, so
   nothing is actually required any more.
