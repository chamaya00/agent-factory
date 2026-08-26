# Checkpoint: the things only you can do

Everything in phases 1 to 5 is built and merged. These steps need a human with
account access. Step 0 is thirty seconds and everything downstream depends on
it; nothing agent-side works until steps 1 and 2 are done either.

All of it is doable from an iPhone. Step 3 is the fiddly one, and the note about
the private key is the part that catches people out.

---

## 0. Tag `main` as `v1`

Every caller workflow in every project resolves
`chamaya00/agent-factory/.github/workflows/ci.yml@v1`. Until that reference
exists, a project's checks fail before they start, with an error about an
invalid workflow reference rather than anything to do with the code.

From the web, on the phone:

1. Open `github.com/chamaya00/agent-factory/releases/new`.
2. Tap **Choose a tag**, type `v1`, then **Create new tag: v1 on publish**.
3. Target: `main`.
4. Title `v1`. Leave the body empty or paste the first paragraph of the README.
5. **Publish release**. That creates the tag.

The tag is load-bearing and it is mutable: moving it changes what every project
runs, immediately, with no pull request anywhere. When the factory changes in a
way projects should not pick up automatically, cut `v2` and let each project
move its callers when it is ready.

To move it deliberately later, delete the `v1` release and republish it against
the newer commit.


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

## 4. Enable the plugin on your Claude account

In any Claude Code session:

```
/plugin marketplace add chamaya00/agent-factory
/plugin install agent-factory@agent-factory
```

Then confirm it loaded, in a cloud session rather than locally, since cloud
sessions are where you will actually use it:

- `/plugin` should list `agent-factory` as enabled.
- Typing `/new-project` should offer the command.
- Asking for the `engineer` agent by name should find it.

If the commands do not appear, the usual cause is the marketplace being added
but the plugin not installed. Both lines are needed.

## 5. Connect the preview deploy provider

Sign in to the provider with GitHub, import the project repo, and let it open
its own pull request for the config. Confirm that a pull request gets a preview
URL comment. That URL is what makes reviewing an agent's work from a phone
possible at all - without it you are reading diffs on a 6-inch screen.

Do not give the provider access to the factory repo. There is nothing to deploy
here.

---

## When you are done

Reply with which of these are done. Then phase 7 proves the gate before any
agent is pointed at it - that ordering matters, and the reason is in
`docs/proving-the-gate.md`.
