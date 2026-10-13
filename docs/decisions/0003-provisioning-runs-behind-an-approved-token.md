# ADR 0003: per-repository setup runs in the factory, behind an approved token

Date: 2026-10-13
Status: accepted

## Context

Provisioning a project has always ended in a list handed to a person: the
Actions permission, three secrets, installing the agent identity App, starting
`bootstrap`, and branch protection. None of those is inherently manual. Each
needs an identity with admin on the new repository, and a session token is a
GitHub App installation holding nothing at the account level, so every one of
them comes back `403 Resource not accessible by integration` from a session
however it is asked.

The only identity that could do them was the person. Either they did them by
hand, from a phone, a settings page at a time - pasting the same OAuth token and
the same private key into every repository - or they opened a Codespace on the
factory and ran `scripts/setup-project.sh`, which still asked for the token on
every run and still could not touch the App. Two of those steps, the Actions
permission and branch protection, could not even be read back from a session, so
done by hand they stayed taken on trust for the life of the repository.

Moving that work somewhere that needs nobody at a terminal means storing an
identity with admin over the person's repositories where a workflow can reach
it. That changes a category - until now only a human ever held admin anywhere in
this system, and that was the stated reason branch protection was never
automated - so the house rules want it recorded rather than settled inside a
pull request.

## Decision

`.github/workflows/provision.yml` does the per-repository setup, with a
fine-grained personal access token the person creates once and keeps as a
secret of a `provision` environment on the factory. The same environment holds
the three values every project needs, so they are pasted once, ever, rather than
once per repository.

It starts from a `provision` label on an issue titled `provision <owner/repo>`,
which is what `/new-project` files, or from Run workflow on the Actions tab. A
session can label an issue but cannot dispatch a workflow, which is why the
label path exists at all.

The token reaches a job only after the person approves that job. The
environment requires a reviewer and only lets the default branch use it, and a
job with no secrets checks both before the approval is ever requested, together
with the shape of the requested name. That check confirms the configuration; it
is not the protection. An edited copy of the workflow on a branch can delete it,
and what stops that copy reaching the token is the environment's branch policy.

The agent identity App stays installed on selected repositories, and the
workflow adds each new one. Installing it on all repositories would remove that
step and was declined: the App's private key sits in every project's secrets, so
"all repositories" would let a key leaked from any one project mint a token for
every other repository the person owns, the factory included.

Every step is read back after it is set, and the result is posted on the request.

## Consequences

Provisioning a repository becomes: create it, run `/new-project`, approve one
deployment. Nothing is pasted, no Codespace is opened, and the two settings that
used to be taken on trust are now read back.

The factory now holds a token with admin over every repository the person owns,
itself included. The bounds on it are the approval, the branch policy, the
token's own expiry, and its permission list, which names nothing beyond what the
steps need: Administration, Secrets, and Actions read and write, Contents and
Issues read, and GitHub App installation repository access. It cannot write
code or workflow files anywhere. It can rename, transfer, or delete a
repository, because GitHub puts those under the same Administration permission
as the Actions setting and branch protection, and there is no narrower grant
that covers the two. Anybody who can merge to the factory's default branch can
change what an approved run does, which was already true of what every project
runs.

Branch protection is now set by an automated identity, which this repository
used to refuse on the grounds that an identity that can set a gate can remove
one. That reasoning was about agents. This identity runs nothing but this
workflow, only when a person approves it, and does not exist inside any project.
No agent holds it.

The token expires within a year. Renewing it is one secret updated in the
environment; a renewed `CLAUDE_CODE_OAUTH_TOKEN` reaches existing projects by
re-running provisioning on each, because every run re-sets the secrets.

`scripts/setup-project.sh` and the hand path stay, for a factory that has not
set the environment up. A request against an environment that is missing or
lacks a reviewer is refused, in a comment on the request, before anybody is
asked to approve anything.

Nothing about GitHub Pages is done here. Publishing is not part of what a new
repository needs, and the workflow does not ask for the permission.

## Alternatives rejected

**A provisioning GitHub App instead of a personal token.** No expiry, which is
a real advantage this loses. But to reach a repository created after it, it has
to be installed on all repositories - an App on selected ones needs each new
repository added by hand, which is the step being removed - and then it holds
the same admin over everything the token does, with no expiry bounding it. It
is also a second App to create, and a second private key to keep, from a phone.
Whether an App's own token can add a repository to another App's installation
was not settled; a personal token can, which made it unnecessary to find out.

**Install the agent App on all repositories.** Removes the per-repository
install outright. Declined for the blast radius above.

**Give the cloud session an admin token.** The simplest wiring, since
`/new-project` already says to use `gh` when it is authenticated. Declined
because the token would then sit in every session in that environment, each of
which reads text it did not write, with no approval between a request and its
use.

**Codespaces secrets with `setup-project.sh`.** Removes the pasting and keeps a
person at a terminal, which is the whole of its safety and the whole of its
cost. It is still available, and nothing here removes it.

**Move the account to an organization.** Org secrets, an org-wide App
installation and rulesets remove most per-repository steps with no new code.
`docs/checkpoint.md` describes that path and its costs. It remains open, and if
it is taken this workflow shrinks to the steps an organization does not cover.
