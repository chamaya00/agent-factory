#!/usr/bin/env bash
#
# Does every provisioning step a cloud session cannot do, from a terminal
# where `gh` is authenticated as a person.
#
# ---------------------------------------------------------------------------
# Why this exists, and why the steps it does were ever manual
#
# `/new-project` hands five things back to a human: creating the repository,
# the Actions permission, running bootstrap, the secrets, and branch
# protection. Reading that list it looks as though those steps are inherently
# manual. They are not. They are unavailable *to a cloud session*, which is a
# different claim.
#
# A session token is a GitHub App installation on a set of repositories. It can
# act inside them within the permissions granted, and it holds nothing at the
# account level - so creating a repository and changing a repository setting
# both come back `403 Resource not accessible by integration`, no matter how
# they are asked for. `gh` in a Codespace is authenticated as you, with your
# scopes, against your account. Everything on that list is one API call from
# here.
#
# What stays manual after this runs is the part that is genuinely UI-only:
# creating the GitHub App for the agent identity. This script detects whether
# one is installed and says so rather than guessing.
#
# ---------------------------------------------------------------------------
# How to run it
#
#   bash scripts/setup-project.sh <owner/repo>
#
# It runs in two halves with a wait between them, because the middle belongs to
# the session rather than to you:
#
#   pre   - create the repository, set the Actions permission, set the secrets.
#           Everything `/new-project` needs in place before it pushes files.
#   wait  - poll until the caller workflows appear on the default branch, which
#           is how this knows `/new-project` has finished its half.
#   post  - run bootstrap, read the check names back as they actually reported,
#           and set branch protection to require them.
#
# Pass `--stage pre` or `--stage post` to run one half on its own, which is
# what to do if this is interrupted or if you would rather not leave a terminal
# blocked. `--no-wait` runs pre and stops.
#
# Everything it prints is also appended to setup-project-output.txt, so a URL
# or a check name can be copied out of the editor rather than off a phone
# screen. No secret value is ever written there.

set -uo pipefail # not -e: several steps have their own fallback path

REPO=""
STAGE="all"
WAIT_SECONDS=900

while [ $# -gt 0 ]; do
  case "$1" in
  --stage)
    STAGE="${2:-}"
    shift 2
    ;;
  --stage=*)
    STAGE="${1#*=}"
    shift
    ;;
  --no-wait)
    STAGE="pre"
    shift
    ;;
  --wait-seconds)
    WAIT_SECONDS="${2:-}"
    shift 2
    ;;
  -h | --help)
    sed -n '2,45p' "$0"
    exit 0
    ;;
  *)
    REPO="$1"
    shift
    ;;
  esac
done

case "$STAGE" in
all | pre | post) ;;
*)
  echo "--stage must be one of: all, pre, post (got '$STAGE')" >&2
  exit 2
  ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
OUTPUT_FILE="$REPO_ROOT/setup-project-output.txt"

log() {
  echo "$@" | tee -a "$OUTPUT_FILE"
}

fail() {
  log ""
  log "STOPPED: $*"
  log ""
  log "Nothing below this point ran. Fix the above and run this again - every"
  log "step is idempotent, so re-running costs nothing."
  exit 1
}

{
  echo "=================================================================="
  echo "agent-factory project setup: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "=================================================================="
} >>"$OUTPUT_FILE"

# --- inputs ----------------------------------------------------------------

if [ -z "$REPO" ]; then
  if [ ! -t 0 ]; then
    fail "No repository given and no terminal to ask on. Pass it: bash scripts/setup-project.sh owner/repo"
  fi
  read -r -p "Which repository is being provisioned? (owner/repo) " REPO
fi

case "$REPO" in
*/*) ;;
*) fail "'$REPO' is not owner/repo." ;;
esac

OWNER="${REPO%%/*}"

command -v gh >/dev/null 2>&1 || fail "No \`gh\` on PATH. This is meant to run in a GitHub Codespace, where it is preinstalled."

# --- authentication --------------------------------------------------------
#
# Codespaces injects a token scoped to the repository the Codespace is on. It
# can read this repository and nothing else, so every settings call below would
# come back 404 or 403 - indistinguishable, from here, from the repository not
# existing. Probe for real admin rather than trusting `gh auth status`, which
# reports a token as fine when it is merely present.

probe_admin() {
  gh api "repos/$REPO" --jq '.permissions.admin' 2>/dev/null
}

log ""
log "Checking what this terminal's GitHub token can do..."

admin="$(probe_admin)"

if [ "$admin" != "true" ]; then
  log "The current token cannot administer $REPO."
  log "(That is expected in a Codespace: its built-in token is scoped to the"
  log "repository the Codespace is on, not to $REPO.)"

  if [ ! -t 0 ]; then
    fail "No terminal to re-authenticate on. Run: gh auth login -h github.com -s repo,workflow"
  fi

  log ""
  log "Re-authenticating as you. A code and a URL appear below - open the URL,"
  log "paste the code, approve, then come back here."
  log ""
  if ! gh auth login --hostname github.com --git-protocol https --scopes repo,workflow --web; then
    fail "gh auth login did not complete."
  fi
  admin="$(probe_admin)"
fi

# --- stage: pre ------------------------------------------------------------

stage_pre() {
  log ""
  log "=== Creating the repository and its settings ==========================="

  if [ "$admin" != "true" ]; then
    # Either it does not exist, or it exists and this token still cannot see
    # it. Creating is the recoverable guess: if it already exists the create
    # fails harmlessly and the probe below says which case this was.
    log ""
    log "$REPO is not visible to this token. Creating it..."
    if gh repo create "$REPO" --public --add-readme >>"$OUTPUT_FILE" 2>&1; then
      log "Created $REPO (public, with a README so it has a default branch)."
    else
      log "Could not create it - it probably already exists under a different owner,"
      log "or this account cannot create repositories there. Checking..."
    fi
    admin="$(probe_admin)"
    [ "$admin" = "true" ] || fail "Still cannot administer $REPO. Check the name, and that this account owns it."
  else
    log "$REPO exists and this token can administer it."
  fi

  # A repository with no commit has no default branch, and every step after
  # this one needs a branch to act on.
  DEFAULT_BRANCH="$(gh api "repos/$REPO" --jq '.default_branch // ""' 2>/dev/null)"
  if [ -z "$DEFAULT_BRANCH" ]; then
    log "No default branch yet - the repository is empty. Adding a README..."
    gh api -X PUT "repos/$REPO/contents/README.md" \
      -f message="Add a README so the repository has a default branch" \
      -f content="$(printf '# %s\n' "${REPO##*/}" | base64 -w0 2>/dev/null || printf '# %s\n' "${REPO##*/}" | base64)" \
      >>"$OUTPUT_FILE" 2>&1 ||
      fail "Could not create a first commit."
    DEFAULT_BRANCH="$(gh api "repos/$REPO" --jq '.default_branch // ""')"
  fi
  log "Default branch: $DEFAULT_BRANCH"

  if [ "$(gh api "repos/$REPO" --jq '.private')" = "true" ]; then
    log ""
    log "WARNING: $REPO is private. A private repository cannot call the factory's"
    log "reusable workflows, so every check fails before it starts. Make it public"
    log "at github.com/$REPO/settings before running any agent here."
  fi

  # --- the Actions permission ---
  #
  # Off by default on personal-account repositories. With it off every agent
  # run appears to work and then silently fails to open a pull request, which
  # is the single most expensive misconfiguration in this system because
  # nothing reports it.
  log ""
  log "Allowing Actions to create and approve pull requests..."
  if gh api -X PUT "repos/$REPO/actions/permissions/workflow" \
    -f default_workflow_permissions=write \
    -F can_approve_pull_request_reviews=true >>"$OUTPUT_FILE" 2>&1; then
    log "Done. Verifying..."
    approve="$(gh api "repos/$REPO/actions/permissions/workflow" --jq '.can_approve_pull_request_reviews' 2>/dev/null)"
    perms="$(gh api "repos/$REPO/actions/permissions/workflow" --jq '.default_workflow_permissions' 2>/dev/null)"
    log "  default_workflow_permissions: $perms"
    log "  can_approve_pull_request_reviews: $approve"
    [ "$approve" = "true" ] || log "  NOT SET - agent pull requests will fail silently. Set it by hand at github.com/$REPO/settings/actions"
  else
    log "Could not set it. Do it by hand: github.com/$REPO/settings/actions"
    log "  Workflow permissions -> Read and write, and tick 'Allow GitHub Actions"
    log "  to create and approve pull requests'."
  fi

  # --- secrets ---
  #
  # Per repository, and nothing agent-side runs without the first one. The
  # other two are the agent identity App, which is optional only in the sense
  # that without it an orchestrator cannot queue its own children.
  log ""
  log "=== Secrets ============================================================"

  existing="$(gh secret list --repo "$REPO" --json name --jq '.[].name' 2>/dev/null || true)"
  has_secret() { printf '%s\n' "$existing" | grep -qx "$1"; }

  if has_secret CLAUDE_CODE_OAUTH_TOKEN; then
    log "CLAUDE_CODE_OAUTH_TOKEN is already set - left alone."
  else
    token="${CLAUDE_CODE_OAUTH_TOKEN:-}"
    if [ -z "$token" ] && [ -t 0 ]; then
      log ""
      log "CLAUDE_CODE_OAUTH_TOKEN is not set on $REPO, and nothing agent-side"
      log "runs without it. It is the same value for every project - generate it"
      log "once and reuse it."
      log ""
      read -r -p "Paste it now, or press return to generate one with 'claude setup-token': " -s token
      echo
      if [ -z "$token" ]; then
        if ! command -v claude >/dev/null 2>&1; then
          log "Installing the Claude Code CLI to generate one..."
          npm install -g @anthropic-ai/claude-code >>"$OUTPUT_FILE" 2>&1 ||
            log "Could not install it. Generate the token elsewhere and re-run."
        fi
        if command -v claude >/dev/null 2>&1; then
          log "Running 'claude setup-token'. Follow its prompts."
          token="$(claude setup-token 2>/dev/null | tr -d '[:space:]' | grep -o 'sk-ant-oat01-[A-Za-z0-9_-]*' | tail -1)"
        fi
      fi
    fi

    if [ -n "$token" ]; then
      if gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo "$REPO" --body "$token" >>"$OUTPUT_FILE" 2>&1; then
        log "CLAUDE_CODE_OAUTH_TOKEN set."
      else
        log "Could not set CLAUDE_CODE_OAUTH_TOKEN. Add it at github.com/$REPO/settings/secrets/actions/new"
      fi
      unset token
    else
      log "Skipped - no token given. Nothing agent-side will run until it is set:"
      log "  github.com/$REPO/settings/secrets/actions/new"
    fi
  fi

  if has_secret AGENT_APP_ID && has_secret AGENT_APP_PRIVATE_KEY; then
    log "AGENT_APP_ID and AGENT_APP_PRIVATE_KEY are already set - left alone."
  elif [ -n "${AGENT_APP_ID:-}" ] && [ -n "${AGENT_APP_PRIVATE_KEY:-}" ]; then
    gh secret set AGENT_APP_ID --repo "$REPO" --body "$AGENT_APP_ID" >>"$OUTPUT_FILE" 2>&1 &&
      log "AGENT_APP_ID set from the environment."
    gh secret set AGENT_APP_PRIVATE_KEY --repo "$REPO" --body "$AGENT_APP_PRIVATE_KEY" >>"$OUTPUT_FILE" 2>&1 &&
      log "AGENT_APP_PRIVATE_KEY set from the environment."
  else
    log ""
    log "AGENT_APP_ID / AGENT_APP_PRIVATE_KEY are not set. This is the one part"
    log "of setup that cannot be scripted - a GitHub App is created through the"
    log "web UI. Without it:"
    log "  - every agent pull request needs an 'Approve workflows to run' tap"
    log "  - an orchestrator cannot queue its own children, because events raised"
    log "    by GITHUB_TOKEN do not start workflow runs. You get a decomposition"
    log "    and then silence."
    log "Create it at github.com/settings/apps (see docs/checkpoint.md step 3),"
    log "then re-run this with AGENT_APP_ID and AGENT_APP_PRIVATE_KEY exported."
  fi

  log ""
  log "Pre-stage done."
}

# --- stage: wait -----------------------------------------------------------
#
# The middle of provisioning is the session's: it reads the templates, fills in
# CLAUDE.md, decides placeholder-versus-real gate, and pushes. This polls for
# the evidence that it finished rather than asking you to confirm it, because
# you confirming is a step, and a step that can be observed should be.

wait_for_workflows() {
  local branch deadline
  branch="$(gh api "repos/$REPO" --jq '.default_branch')"
  deadline=$(($(date +%s) + WAIT_SECONDS))

  log ""
  log "=== Waiting for /new-project to push the caller workflows =============="
  log ""
  log "Run this in your Claude session now, if you have not already:"
  log ""
  log "    /new-project $REPO"
  log ""
  log "Polling github.com/$REPO for .github/workflows/bootstrap.yml on $branch."
  log "Ctrl-C is safe - resume with: bash scripts/setup-project.sh $REPO --stage post"

  while [ "$(date +%s)" -lt "$deadline" ]; do
    if gh api "repos/$REPO/contents/.github/workflows/bootstrap.yml?ref=$branch" >/dev/null 2>&1; then
      log ""
      log "Found them. Continuing."
      return 0
    fi
    sleep 20
  done

  log ""
  log "Gave up after ${WAIT_SECONDS}s. If /new-project is still running, resume with:"
  log "    bash scripts/setup-project.sh $REPO --stage post"
  return 1
}

# --- stage: post -----------------------------------------------------------

stage_post() {
  log ""
  log "=== Labels and branch protection ======================================="

  local branch
  branch="$(gh api "repos/$REPO" --jq '.default_branch')"

  gh api "repos/$REPO/contents/.github/workflows/bootstrap.yml?ref=$branch" >/dev/null 2>&1 ||
    fail "No .github/workflows/bootstrap.yml on $branch yet. Run /new-project $REPO first, then re-run this with --stage post."

  # --- labels ---
  #
  # Created by the bootstrap workflow rather than here, because their names are
  # matched exactly by the agent-run preflight and one definition beats two.
  log ""
  log "Running the bootstrap workflow (creates the ten labels)..."
  if gh workflow run bootstrap.yml --repo "$REPO" --ref "$branch" >>"$OUTPUT_FILE" 2>&1; then
    log "Dispatched. Waiting for it to finish..."
    sleep 10
    run_id="$(gh run list --repo "$REPO" --workflow bootstrap.yml --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null)"
    if [ -n "$run_id" ]; then
      gh run watch "$run_id" --repo "$REPO" --exit-status >>"$OUTPUT_FILE" 2>&1 ||
        log "The bootstrap run did not finish green - see github.com/$REPO/actions"
    fi
  else
    log "Could not dispatch it. Run it by hand: github.com/$REPO/actions/workflows/bootstrap.yml"
  fi

  # Verify rather than trusting the run, same as /new-project does.
  missing=""
  for want in agent:queued role:engineer objective needs-human; do
    gh api "repos/$REPO/labels/${want//:/%3A}" >/dev/null 2>&1 || missing="$missing $want"
  done
  if [ -n "$missing" ]; then
    log "Labels still missing:$missing"
    log "Re-run github.com/$REPO/actions/workflows/bootstrap.yml and check its log."
  else
    log "Labels verified (sampled agent:queued, role:engineer, objective, needs-human)."
  fi

  # --- check names ---
  #
  # Read back as actually reported rather than assumed. A required check that
  # has never run blocks every merge, including the pull request that would fix
  # it, so a guessed name is worse than no rule at all.
  log ""
  log "Reading the check names as they actually reported on $branch..."

  names=""
  deadline=$(($(date +%s) + 300))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    names="$(gh api "repos/$REPO/commits/$branch/check-runs" --jq '.check_runs[].name' 2>/dev/null | sort -u | grep -v '^$' || true)"
    [ -n "$names" ] && break
    log "  nothing has reported yet - waiting..."
    sleep 20
  done

  if [ -z "$names" ]; then
    log ""
    log "No checks have reported on $branch, so there are no names to require."
    log "Let ci and guard run once (push anything, or open a pull request), then:"
    log "    bash scripts/setup-project.sh $REPO --stage post"
    return 0
  fi

  log "Found:"
  printf '%s\n' "$names" | sed 's/^/  /' | tee -a "$OUTPUT_FILE"

  # --- branch protection ---
  #
  # `required_pull_request_reviews: null` leaves "require a pull request before
  # merging" off on purpose, so a human can still commit directly when a gate
  # needs repairing. The gate this sets is about checks passing, not about
  # routing every change through review.
  log ""
  log "Setting branch protection on $branch to require them..."

  contexts="$(printf '%s\n' "$names" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')"

  if gh api -X PUT "repos/$REPO/branches/$branch/protection" --input - >>"$OUTPUT_FILE" 2>&1 <<JSON; then
{
  "required_status_checks": { "strict": true, "contexts": $contexts },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON
    log "Set. Verifying..."
    got="$(gh api "repos/$REPO/branches/$branch/protection" --jq '.required_status_checks.contexts[]' 2>/dev/null | sort -u)"
    if [ -n "$got" ]; then
      log "Now required on $branch:"
      printf '%s\n' "$got" | sed 's/^/  /' | tee -a "$OUTPUT_FILE"
    else
      log "Could not read the rule back - check github.com/$REPO/settings/branches"
    fi
  else
    log "Could not set it. Do it by hand at github.com/$REPO/settings/branches,"
    log "requiring exactly the names listed above."
  fi
}

# --- run -------------------------------------------------------------------

case "$STAGE" in
pre)
  stage_pre
  log ""
  log "Next: run /new-project $REPO in your Claude session, then come back and run:"
  log "    bash scripts/setup-project.sh $REPO --stage post"
  ;;
post)
  stage_post
  ;;
all)
  stage_pre
  if wait_for_workflows; then
    stage_post
  fi
  ;;
esac

# --- report ----------------------------------------------------------------

log ""
log "=== Where this leaves $REPO ============================================"
log ""
log "  Repository        github.com/$REPO"
log "  Actions settings  github.com/$REPO/settings/actions"
log "  Secrets           github.com/$REPO/settings/secrets/actions"
log "  Branch protection github.com/$REPO/settings/branches"
log "  Runs              github.com/$REPO/actions"
log ""
log "Still a human step, because it has no API: creating the agent identity"
log "GitHub App (docs/checkpoint.md step 3), if AGENT_APP_ID was reported"
log "missing above."
log ""
log "Full output: $OUTPUT_FILE"
log "Done: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
