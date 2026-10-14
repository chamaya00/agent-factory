# Checkpoint: the things only you can do

Everything in phases 1 to 5 is built and merged. These steps need a human with
account access. Step 0 comes before provisioning any repository, nothing
agent-side works until steps 1 and 2 are done, and step 3 is the fiddly one.

All of it is doable from an iPhone. The note about the private key in step 3 is
the part that catches people out.

Most of it is once, not once per repository. With step 7 set up, provisioning a
project is: create it, run `/new-project`, approve one deployment. The steps
below that repeat per repository say so, and say what replaces them.

---

## Which path you are on, before anything below

This page describes the handoffs one repository at a time, which is the only
option on a personal account. On an organization, most of them have an
org-level default that applies to every repository provisioned afterwards, with
no per-repository step at all.

Read whichever of the next two sections is yours and skip the other. Somebody on
a personal account who reads the organization table will go looking for settings
that are not there.

### On a personal account

Steps 0 to 5 below are the list, and steps 2 and 5 repeat for every project
repository you provision. There is no account-level version of them, and that is
a property of personal accounts rather than something missing here.

What there is instead is step 7: a workflow on this repository that does the
per-repository part for you, after you approve it. Set it up once and step 2,
the per-repository half of step 3, and step 6 stop being yours - the run sets
them and reads each one back. Step 5 is outside it; publishing is not part of
what a new repository needs. ADR 0003 has the reasoning and what it costs.

### In an organization

Four of the five handoffs become one-time org settings:

| Handoff | Org-level mechanism |
|---|---|
| The Actions permission (step 1 of `/new-project`) | org Settings, Actions, Workflow permissions - applies as the default for repositories in the org |
| `CLAUDE_CODE_OAUTH_TOKEN`, `AGENT_APP_ID`, `AGENT_APP_PRIVATE_KEY` (steps 2 and 3) | org secrets, shared with all repositories |
| Installing the agent identity App (step 3) | installed on the org with "All repositories" |
| Branch protection (step 5 of `/new-project`) | an org ruleset targeting the repository set |

Labels are the partial one, and it is worth stating precisely rather than
rounding up. Org default labels apply **at repository creation**, so they cover
a fresh repository and not a label a later factory release adds. `bootstrap`
stays the mechanism for those, which is what the session-start hook is already
checking for.

You still generate the token once (step 1) and create the App once (step 3).
What an organization removes is repeating their *installation* per repository,
not their creation.

**What it costs, which is not nothing:**

- An org secret shared with all repositories is readable by every workflow in
  every repository in that org, including ones with nothing to do with this
  system. Scoping the secret to selected repositories is the narrower option and
  gives back a small per-repository step.
- Existing repositories have to be transferred. A transfer carries issue and
  pull request history with it, but URLs change and any local remotes need
  updating.
- Transferring **the factory itself** interacts with the factory's own declared
  repository. `plugins/agent-factory/.claude-plugin/plugin.json` names it, every
  caller a project receives is written from that name, and
  `docs/decisions/0001-factory-repo-is-declared-in-the-manifest.md` has the
  reasoning. Move the repository and that field needs the same change in a pull
  request; the guard fails until it does, which is the intended signal rather
  than a problem. Every repository already provisioned keeps calling the old
  location until `/update-agents` moves its pins - which is the pinning working
  as designed, not a migration failure.

---

## 0. Cut a release tag

This is not a deploy. Nothing here reaches a project on its own, and no
existing repository changes when you do it. What it is, since the callers
started pinning, is a prerequisite: `/new-project` writes `v` plus the version
in `plugins/agent-factory/.claude-plugin/plugin.json` into four workflow files,
so a manifest version with no tag behind it produces a repository whose every
check fails as an invalid workflow reference - an error raised in the project,
naming a ref in this repository, describing neither. Cut the tag before
provisioning anything.

Check first, it is two taps: `github.com/chamaya00/agent-factory/tags` should
list a tag matching the manifest version. If it does, this step is done and
stays done until the next version bump.

The tag name comes from that manifest, so a release starts with a merged pull
request bumping the version. Once that is on `main`:

1. Open `github.com/chamaya00/agent-factory/actions/workflows/release.yml`.
2. Tap **Run workflow**, leave the input empty, then **Run workflow** again.
3. Read the run summary. It lists the workflows callable at the tag - four
   names, `bootstrap.yml` among them - and says explicitly that no project
   picked anything up.

A project takes the release when you run `/update-agents` there and merge what
it opens. Until then it keeps running the release it was pinned to.

One piece of history worth clearing while you are on that page: `v1`, from
before the pins, still exists and points at a commit older than the vendored
roles. Nothing should resolve it, and anything that still does is wrong in a
way that reads as working. Delete it.

`docs/versioning.md` has the full model if you want the reasoning.

## 1. Generate the subscription token

This is what makes runs bill against Pro instead of API credits. One time only.

The token comes from `claude setup-token`, which needs a terminal. A Codespace
is a terminal in mobile Safari, and it is free for this.

1. In Safari, open `github.com/chamaya00/agent-factory`.
2. Tap the green **Code** button.
3. Tap the **Codespaces** tab, then **Create codespace on main**. Wait for the
   editor to load - about a minute the first time.
4. Tap the hamburger menu, top left, then **Terminal**, then **New Terminal**.
   The keyboard is cramped. Turn the phone landscape.
5. In the terminal:

   ```
   npm install -g @anthropic-ai/claude-code
   claude setup-token
   ```

6. It prints a URL. Long-press it, open in a new tab, sign in with the Pro
   account, approve, and copy the code it gives you.
7. Paste the code back into the terminal and press return.
8. It prints a token starting `sk-ant-oat01-`. Select the whole thing and copy.
   Select carefully - a truncated token fails with an auth error that looks
   exactly like a wrong token.
9. **Do not close the Codespace yet.** Finish step 2 first, in another tab, so
   you do not have to redo this if the paste goes wrong.
10. Once step 2 is confirmed, go to `github.com/codespaces` and delete the
    Codespace. It is a terminal with your token in its scrollback.

## 2. Store the token as a repository secret

The name has to be exactly `CLAUDE_CODE_OAUTH_TOKEN`. The workflow reads that
string; anything else silently produces an unauthenticated run.

1. Open the repository the agents will work in. **Not this one** - this repo
   holds the workflows, but agents run inside project repos. Every project repo
   needs its own copy of this secret.
2. **Settings** tab. On a phone it is behind the `...` at the right of the tab
   strip.
3. Left sidebar: **Secrets and variables**, then **Actions**.
4. **New repository secret**.
5. Name: `CLAUDE_CODE_OAUTH_TOKEN`. Secret: paste the token. **Add secret**.

You will repeat steps 1 to 5 of this section for each new project repo, but you
only ever generate the token once - reuse the same value.

**With step 7 set up, skip this section entirely.** The token goes into the
`provision` environment once, and every provisioning run copies it into the
project.

## 3. Create the GitHub App for the agent identity

Why bother, and this is no longer optional. Two reasons, and the second one
arrived with v1.12.0:

Pull requests opened with the default Actions token land in an
approval-required state, so you would have to tap "Approve workflows to run" on
every single one, from your phone, forever. An App token skips that entirely.

More importantly, an orchestrator that queues its own children cannot work
without it. Events raised by `GITHUB_TOKEN` do not start workflow runs, so with
no App the label the orchestrator puts on a child raises nothing and the child
never runs - and neither does the wake when a child lands. You get the
decomposition and then silence. `docs/open-questions.md` entry 7 has the
detail.

1. `github.com/settings/apps` then **New GitHub App**.
2. Name: something unique, for example `chamaya00-agent-factory`. GitHub App
   names are globally unique, so expect to add a suffix.
3. Homepage URL: the factory repo URL. Anything valid works.
4. Uncheck **Active** under Webhook. There is no webhook here.
5. Repository permissions - set exactly these and nothing more:
   - Contents: **Read and write**
   - Issues: **Read and write**
   - Pull requests: **Read and write**
   - Metadata: **Read-only** (it selects itself)
   - Workflows: **No access**. This is deliberate. An identity that can rewrite
     workflows can rewrite its own gates.
6. Under "Where can this GitHub App be installed", choose **Only on this
   account**.
7. **Create GitHub App**.
8. On the App's page, note the **App ID** at the top. Copy it.
9. Scroll to **Private keys**, tap **Generate a private key**. Safari downloads
   a `.pem` file.

   **The iPhone part.** The `.pem` lands in Files, under Downloads. Tapping it
   does not open it. To read it: open the **Files** app, long-press the file,
   **Quick Look**, and the contents show as text you can select and copy. If
   Quick Look refuses, rename the file to end in `.txt` first and it will open.
   Copy everything including the `-----BEGIN` and `-----END` lines.

10. Still on the App's page, left sidebar: **Install App**, install it on your
    account, and choose **Only select repositories** - the project repositories,
    or with step 7 set up, any one of them. Not **All repositories**: the
    private key sits in every project's secrets, so "all" would let a key
    leaked from any one project reach every repository you own, this one
    included.
11. Back in each project repo, add two more secrets the same way as step 2:
    - `AGENT_APP_ID` - the App ID from step 8
    - `AGENT_APP_PRIVATE_KEY` - the full contents of the `.pem`

    With step 7 set up, put these two in the `provision` environment instead,
    once. Every provisioning run copies them into the project and adds the
    project to the App's installation, so neither 10 nor 11 repeats.
12. Delete the `.pem` from Files.

Skipping this section used to cost only the approval tap on every pull request.
Since v1.12.0 it costs the orchestration: the caller still passes empty App
secrets and still falls back to the default token, so a single run started by a
human label works exactly as before, but nothing that agent labels afterwards
starts anything. An objective decomposes and stops. Roles queued by hand, one at
a time, still work - that is the pre-v1.12.0 flow, and it is what a project
without this section is left with.

## 4. The commands: nothing to do, and why

This step has said two wrong things already, so here is what is actually true.

It first said to run `/plugin marketplace add` and `/plugin install`. That does
not work: `/plugin` is a command of the terminal and desktop apps, and a web
session answers it with "isn't available in this environment" - which is the
only device you have.

It then said the repository declares the marketplace in `.claude/settings.json`
and a session installs the plugin at startup. That is also wrong, and it is the
worse of the two because it looks like it works. Claude Code drops a marketplace
declared in a repository's settings unless the folder has been trusted for
project plugins. Trust is a prompt, a web session has nobody to answer it, and
so the flag is never set: the marketplace is never registered, the
`enabledPlugins` entry beside it is an orphan, and nothing installs. No tag and
no branch changes that.

What a cloud session does load is `.claude/commands/`, `.claude/agents/`, and
`.claude/skills/` from the repository it cloned. Those are ordinary files in the
clone, not a third-party source being fetched, so they are not behind the trust
gate. This repository now carries its own copy of all three, checked against
`plugins/agent-factory/` by `scripts/validate_plugin.py` so the two cannot
drift. `/new-project` copies the same files into every project repository, which
is how `/retro`, `/decompose`, and `/update-agents` turn up there.

So the check is to look, not to install:

- Type `/new` in a session on this repository. `/new-project` should be
  offered. If it is, this step is done.
- Ask for the `engineer` agent by name. It should be found.

If the commands are missing, the cause is that `.claude/commands/` is not on the
branch the session cloned - check that first, then start a fresh session.
Commands are read once at startup, so a session that started before the files
landed will not pick them up no matter what you type in it.

## 5. Turn on publishing for the project repo

Something has to render an agent's work as a page you can look at, or reviewing
from a phone means reading diffs on a 6-inch screen. The cheapest version of
that needs no third-party account and no deploy step: serve the project repo's
default branch straight from GitHub.

On the project repo, not this one - there is nothing to publish here:

> 1. Open `github.com/<owner>/<repo>/settings/pages`
> 2. Source: **Deploy from a branch**
> 3. Branch: the default branch, folder: **/ (root)**
> 4. **Save**

Root rather than `/docs`, because provisioning already put `decisions/`,
`design/`, and `research/` in `docs/` and none of those are the website.

Two things this does not give you, worth knowing before you rely on it. The URL
404s until something lands at the root of the default branch, which is correct
and not a broken setup. And publishing from a branch covers merged work only -
there is no per-pull-request preview, so a pull request is reviewed against its
acceptance criteria and its test names, and the page is looked at after the
merge. Connecting a preview provider on top of this is a later decision, not a
prerequisite.

---

## 6. Start the `bootstrap` run for each new project

Confirmed as yours rather than the session's, which this page and
`/new-project` both used to get wrong.

`/new-project` step 4 dispatches `bootstrap.yml` to create the labels and
report the check names branch protection needs. That dispatch comes back
`403 Resource not accessible by integration` - on a public repository, freshly
provisioned, with all four callers already on the default branch, so none of
the usual explanations apply. The cause is that the App the session runs as has
no `actions: write`.

The distinction that matters, because it sends people to the wrong settings
page: the **Workflow permissions** setting in step 1 of `/new-project` governs
what `GITHUB_TOKEN` may do *inside* a run. It has no bearing on what an
external App may do *to* the repository. Setting it to "Read and write" does
not make the dispatch work, and there is no repository setting that does - the
permission belongs to the App, not to you.

So this is four taps, per project, after step 3 lands on the default branch:

> 1. Open `github.com/<owner>/<repo>/actions/workflows/bootstrap.yml`
> 2. Tap **Run workflow**, then **Run workflow** again to confirm

Then tell the session it has finished. **Do not read the summary back to it.**
Starting a run and reading one are different permissions and only the first is
refused, so the session reads the run itself and takes the check names off it.
Transcribing them off a phone is how a typo gets into a branch protection rule,
and a required check name that never reports blocks every merge including the
one that would fix it.

The fast-path script avoids this entirely: `scripts/setup-project.sh` runs `gh`
as you, so `gh workflow run bootstrap.yml` works there, along with the labels
and branch protection. If you are at a terminal, that is the shorter road.

If you did this page by hand rather than through provisioning (step 7),
`bash scripts/setup-project.sh --verify <owner/repo>` in the same Codespace
reads every one of these settings back and changes nothing. A session cannot
read the Actions permission or branch protection, so without the provisioning
run's report this is how they get confirmed rather than taken on your word. It
is worth re-running later on either path: settings drift, and nothing else
reads them again.

Step 7 avoids it with no terminal: the provisioning run starts `bootstrap`,
waits for it, samples the labels, and sets branch protection from the check
names the two gates actually reported.

## 7. Set up provisioning, once

This is what turns every per-repository step above into one approval. It is a
workflow on this repository, `.github/workflows/provision.yml`, holding a token
that can administer your repositories, and it only ever gets that token after
you approve the run that asked for it. Four parts, about ten minutes, all from
the phone.

Read ADR 0003 first if you want the costs before the steps. The short version:
this repository then holds a token with admin over every repository you own,
and the approval is what bounds it.

**The token.**

> 1. Open `github.com/settings/personal-access-tokens/new`
> 2. Token name: `agent-factory provisioning`. Expiration: the longest it
>    offers, and put the date somewhere you will see it.
> 3. Resource owner: your account
> 4. Repository access: **All repositories**. A token on selected repositories
>    cannot reach one created after it, which is every repository it will ever
>    provision.
> 5. Repository permissions - set exactly these and leave the rest at
>    **No access**:
>    - Actions: **Read and write** - starts `bootstrap` and re-runs a gate
>    - Administration: **Read and write** - the Actions setting and branch
>      protection
>    - Contents: **Read-only** - checks the files have landed
>    - Issues: **Read-only** - reads the labels back
>    - Secrets: **Read and write**
>    - GitHub App installation repository access: **Read and write** - adds
>      each project to the agent App. If your form does not list it, skip it;
>      the run says so on that one line and links the page that does it by
>      hand.
>    - Metadata: **Read-only** (it selects itself)
> 6. **Generate token** and copy it

Contents stays read-only and Workflows stays at no access on purpose: this
token sets up a repository, and never writes code or workflow files into one.
Administration is wider than the two settings it is here for - GitHub files
renaming and deleting a repository under it too - and there is no narrower
grant that covers them.

**The environment.** On this repository, not a project:

> 1. Open `github.com/chamaya00/agent-factory/settings/environments`
> 2. **New environment**, name it exactly `provision`, **Configure environment**
> 3. Tick **Required reviewers** and add yourself. Leave **Prevent self-review**
>    unticked: you are the one asking and the one approving.
> 4. Deployment branches and tags: **Selected branches and tags**, then **Add
>    deployment branch or tag rule**, and enter `main`
> 5. **Save protection rules**
> 6. Under **Environment secrets**, **Add environment secret** four times:
>    - `PROVISION_TOKEN` - the token above
>    - `CLAUDE_CODE_OAUTH_TOKEN` - from step 1
>    - `AGENT_APP_ID` - from step 3, item 8
>    - `AGENT_APP_PRIVATE_KEY` - the full `.pem` from step 3, item 9

They have to be **environment** secrets, not repository secrets. A repository
secret is handed to every workflow run here with nobody approving anything,
which is the one thing this whole arrangement exists to prevent.

The run checks parts 3 and 4 before it asks you to approve anything, and refuses
in a comment if either is missing. It cannot check that the secrets are
environment secrets rather than repository ones. That one is yours.

**The label.**

> 1. Open `github.com/chamaya00/agent-factory/labels`
> 2. **New label**, name it exactly `provision`, **Create label**

**Then, per repository, from now on:**

1. Create it at `github.com/new` - public, with a README - as in `/new-project`
   step 2.
2. Run `/new-project <owner/repo>` in a session on this repository. It files an
   issue here titled `provision <owner/repo>`, labelled `provision`, and goes
   on writing the files.
3. GitHub notifies you that a deployment is waiting for your review. Open it -
   or the run, from the issue or the Actions tab - tap **Review deployments**,
   tick `provision`, **Approve and deploy**.

The run sets the Actions permission, the three secrets and the App installation
straight away, waits for the files `/new-project` is pushing, starts
`bootstrap`, waits for the two gates to report on that push, and sets branch
protection from the names they reported. Then it comments on the issue: one
ticked line per thing it confirmed by reading it back, and an unticked line,
with the page that fixes it, for anything it could not. The session reads that
comment for its own report. When every line is ticked it closes the issue.

Re-running is safe: re-apply the label, or **Run workflow** on
`github.com/chamaya00/agent-factory/actions/workflows/provision.yml` with the
repository typed in. Every step re-sets or skips what is already done.

**When something expires.** The token: generate a new one the same way and
update `PROVISION_TOKEN` in the environment. Nothing else changes. The
subscription token from step 1: update `CLAUDE_CODE_OAUTH_TOKEN` in the
environment, then re-run provisioning once per existing project - every run
re-sets the secrets from the environment, which is how a renewed value reaches
a repository that already has the old one.

## When you are done

Reply with which of these are done. Then phase 7 proves the gate before any
agent is pointed at it - that ordering matters, and the reason is in
`docs/proving-the-gate.md`.
