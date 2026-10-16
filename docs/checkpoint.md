# Checkpoint: what only the factory's owner can do

Setting up a project needs nothing from this page - `getting-started.md` is the
whole of that, and it involves no token, App, or secret. This page is for
whoever owns the factory repository: one step that is required whenever the
version changes, and two that are optional.

All of it works from a phone.

---

## 1. Cut a release after a version bump

Projects call this factory's workflows pinned to a release tag, `v` plus the
version in `plugins/agent-factory/.claude-plugin/plugin.json`. A version with no
tag behind it sets repositories up whose every check fails as an invalid
workflow reference - an error raised in the project, naming a ref in this
repository, describing neither. So after any merged pull request that bumps the
version:

> 1. Open `github.com/chamaya00/agent-factory/actions/workflows/release.yml`
> 2. Tap **Run workflow**, leave the input empty, then **Run workflow** again
> 3. Read the run summary: it lists the workflows callable at the new tag and
>    says that no project picked anything up

Check first: `github.com/chamaya00/agent-factory/tags` should list a tag
matching the manifest version. If it does, this step is done until the next
bump.

This is not a deploy. No existing project changes until someone runs
`/update-agents` in it and merges what it opens. No workflow here can move a
tag - none is granted `actions: write` - so a session that says it cut one did
not. `versioning.md` has the full model.

## 2. Clean up what earlier releases needed

Releases before 1.43.0 ran agents in GitHub Actions and needed credentials that
nothing reads any more. Once a project has taken 1.43.0 or later, delete from
its **Settings, Secrets and variables, Actions**:

- `CLAUDE_CODE_OAUTH_TOKEN`
- `AGENT_APP_ID`
- `AGENT_APP_PRIVATE_KEY`

and from this repository's `provision` environment, if you set one up, the same
three - keep `PROVISION_TOKEN`. The agent identity App itself can be
uninstalled at `github.com/settings/installations` and deleted under
`github.com/settings/apps` once no project on an older release still uses it.
None of this is required; a leftover secret does nothing.

## 3. Optional: provisioning, for many repositories

Setting a repository up hands back two steps: one tap to run `bootstrap`, and
one settings page for branch protection. If you set up many repositories, this
turns both into one approval: `/new-project` files an issue here, you approve
the run, and it starts `bootstrap`, waits for the two gates to report, and sets
branch protection from the names they reported, reading each back.

The cost is that this repository then holds a token with admin over every
repository you own, released only to a run you approve. ADR 0003 has the
trade. It only serves repositories on the same account as the factory.

**The token.**

> 1. Open `github.com/settings/personal-access-tokens/new`
> 2. Token name: `agent-factory provisioning`. Expiration: the longest offered,
>    and put the date somewhere you will see it.
> 3. Resource owner: your account
> 4. Repository access: **All repositories** - a token on selected
>    repositories cannot reach one created after it.
> 5. Repository permissions, exactly these, everything else **No access**:
>    - Actions: **Read and write** - starts `bootstrap`, re-runs a gate
>    - Administration: **Read and write** - branch protection
>    - Contents: **Read-only** - checks the files have landed
>    - Issues: **Read-only** - reads the labels back
>    - Metadata: **Read-only** (selects itself)
> 6. **Generate token** and copy it

**The environment**, on this repository:

> 1. Open `github.com/chamaya00/agent-factory/settings/environments`
> 2. **New environment**, named exactly `provision`, **Configure environment**
> 3. Tick **Required reviewers** and add yourself. Leave **Prevent
>    self-review** unticked: you are the one asking and the one approving.
> 4. Deployment branches and tags: **Selected branches and tags**, add a rule
>    for `main`
> 5. **Save protection rules**
> 6. **Add environment secret**: `PROVISION_TOKEN`, the token above

It has to be an **environment** secret, not a repository secret: a repository
secret reaches every workflow run here with nobody approving anything. The run
checks the reviewer and the branch rule before it asks you to approve anything,
and refuses in a comment if either is missing.

**The label.** At `github.com/chamaya00/agent-factory/labels`, **New label**,
named exactly `provision`.

From then on `/new-project` uses it on its own, and the only per-repository
step left is approving the deployment GitHub notifies you about. When the token
expires, generate a new one the same way and replace `PROVISION_TOKEN`.

## 4. Optional: publishing a project's work as a site

Reviewing from a phone is easier when an agent's work is a page you can open.
The cheapest version serves a project's default branch straight from GitHub.
On the project repository:

> 1. Open `github.com/<owner>/<repo>/settings/pages`
> 2. Source: **Deploy from a branch**
> 3. Branch: the default branch, folder **/ (root)**
> 4. **Save**

The URL shows a 404 until something lands at the root, which is expected, and
it covers merged work only - there is no per-pull-request preview.

## In an organization

Branch protection can be one org ruleset targeting the repositories, instead of
a page per repository, and org default labels cover a repository's labels at
creation (`bootstrap` still adds any a later release introduces). Moving the
factory itself to an organization means changing `repository` in its plugin
manifest in the same pull request; ADR 0001 has why.
