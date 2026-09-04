# Checkpoint: the things only you can do

Everything in phases 1 to 5 is built and merged. These steps need a human with
account access. Step 0 comes before provisioning any repository, nothing
agent-side works until steps 1 and 2 are done, and step 3 is the fiddly one.

All of it is doable from an iPhone. The note about the private key in step 3 is
the part that catches people out.

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

## 3. Create the GitHub App for the agent identity

Why bother: pull requests opened with the default Actions token land in an
approval-required state, so you would have to tap "Approve workflows to run" on
every single one, from your phone, forever. An App token skips that entirely.

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
    account, and choose the project repositories.
11. Back in each project repo, add two more secrets the same way as step 2:
    - `AGENT_APP_ID` - the App ID from step 8
    - `AGENT_APP_PRIVATE_KEY` - the full contents of the `.pem`
12. Delete the `.pem` from Files.

If you skip this section entirely the system still works: the caller workflow
passes empty App secrets and falls back to the default token. You just get the
approval tap on every pull request.

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

## 5. Switch on Pages for the project repo

`/new-project` hands this over as its own step, with the taps, so there is
nothing to do here ahead of time. It is on this list so that it is not a
surprise later:

Publishing is a repository setting - Settings, Pages, deploy from a branch, the
default branch, `/docs` - and it stays a human step for the same reason branch
protection does. An identity that can publish a site can publish anything.

What a fresh repository publishes on day one is its own decisions and research,
rendered, plus a placeholder page. Confirm that page loads when you set it.
That confirmation is the whole value of the placeholder: without it, a blank
site later could equally mean the agents built nothing or that Pages was never
switched on.

No third-party preview provider, and no deploy workflow. A preview account
would put the deployment behind a vendor, and a deploy workflow would put it
somewhere the agents may never touch, which is the wrong place for the thing
they are building. The trade is that there is no per-pull-request preview URL:
the checks are what you trust before a merge, and the site is what you look at
after one.

---

## When you are done

Reply with which of these are done. Then phase 7 proves the gate before any
agent is pointed at it - that ordering matters, and the reason is in
`docs/proving-the-gate.md`.
