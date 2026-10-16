# Getting started

The factory sets a GitHub repository up so a team of AI agents can work in it:
an orchestrator that splits an objective into issues, and a researcher,
analyst, designer, and engineer that each take one. They work as pull requests
against checks that stop anything red from merging. You describe what you want
in a Claude Code session; the session runs the agents, reviews what they
deliver, and merges what passes - or brings it to you.

Everything happens in Claude Code sessions, from a phone if you like. There is
nothing to install.

## What you need

- **A Claude plan with Claude Code** - on the web, the desktop app, or the
  mobile app.
- **GitHub connected to Claude**, with access to the repositories you want the
  agents to work in. Claude asks for this the first time you start a session on
  a repository; if a repository is missing from the list later, add it under
  `github.com/settings/installations`, Claude, Repository access.

That is all. No API key, no tokens, no secrets, and no GitHub App of your own:
a session works as you.

## Set up a repository

The repository has to be **public** - it calls this factory's shared
workflows, which a private repository cannot - and it needs at least one commit.
For a new one, create it at `github.com/new` with **Add a README file** ticked.

Then pick whichever of these fits.

**From a session on your own repository - works for anyone.** Start a Claude
Code session on the repository you want set up and send:

> Set this repository up with the agent factory: clone
> https://github.com/chamaya00/agent-factory at its latest release and follow
> plugins/agent-factory/commands/new-project.md from that clone, for this
> repository.

**From a session on the factory - if you own it or have forked it.** Start a
session on the factory and send `new project <owner/repo>`.

Either way the session writes every file itself, then hands back at most two
things, with links:

1. **Run `bootstrap` once.** One tap: Actions tab, `bootstrap`, Run workflow.
   It creates the labels the agents use. The session reads the result itself.
2. **Turn on branch protection.** One settings page, recommended: it is what
   makes "merge when green" mean something. The session tells you the exact
   check names to require.

Your repository then calls the factory's workflows pinned to a release. It
moves to a newer release only when you ask: `/update-agents` in a session on
it opens one pull request with everything that changed.

## Use it

In a Claude Code session on your repository:

- **`obj <what you want>`** (or `/objective`) starts a piece of work. The
  session asks a question or two, writes the objective up as an issue, asks
  whether it may merge work that passes the checks or should bring each piece
  to you, and then drives it: the orchestrator splits it, each role runs in
  turn, and you hear about anything that needs you.
- **`/check-in`** catches you up after time away and starts anything queued.
- **"Keep this going overnight"** - or for the weekend, or until it is done -
  starts a self-driving stretch. The session asks everything it will need up
  front, then keeps working on a schedule while you are away, writing every
  decision it makes for you on one issue you can read afterwards.

Agents run only while a session on the repository is open, unless a
self-driving stretch is keeping one going.

## Coming from an older release

A repository set up before 1.43.0 ran its agents in GitHub Actions with a
`CLAUDE_CODE_OAUTH_TOKEN` secret, and may still have an `agent-run` workflow
that fails on every queued issue. In a session on it, run `/update-agents` and
merge the pull request it opens: that deletes the old workflow and moves
everything to sessions. Then delete the `CLAUDE_CODE_OAUTH_TOKEN`,
`AGENT_APP_ID`, and `AGENT_APP_PRIVATE_KEY` secrets from the repository's
settings - nothing reads them any more.

## Owning the factory

If the factory is yours, `checkpoint.md` has the few things only you can do:
cutting a release, and two optional conveniences.

---

## For a session: the walkthrough

`CLAUDE.md` sends a session here when it is opened on the factory with a
greeting instead of a task - "hi", "help", "start", "new", "getting started",
or close variants. A message that already names a repository, a bug, a file, or
an objective is a task: do the task, and do not interrupt it with this. Fire it
once; after the person has said what they want, a later "hi" is small talk.

1. **Say what this is, in two sentences** - the first paragraph of this page,
   shortened.
2. **Ask which repository** to set up, as `owner/repo`. If they do not have
   one yet, the two things it needs are above: public, and a first commit.
3. **Say what will come back to them** before running anything, in one line:
   creating the repository if it does not exist, one tap to run `bootstrap`,
   and branch protection - as a short list at the end, not as blockers now.
4. **Run `/new-project <owner/repo>`** once they confirm, and let its steps
   narrate themselves.
5. **Close on its report**, which is already the deliverable. Point at it
   rather than summarising it a second way.

No new command and no state: this is a way of opening `/new-project`, decided
fresh from the shape of one message, with nothing to keep in sync.
