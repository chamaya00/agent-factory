#!/usr/bin/env bash
#
# Does the provisioning steps a cloud session cannot, from a terminal where
# `gh` is authenticated as a person.
#
# Run it in a Codespace on this repository, after `/new-project` has pushed
# the caller workflows:
#
#   bash scripts/setup-project.sh <owner/repo>
#
# Why it exists: those steps are not inherently manual, they are unavailable
# to a session. A session token is a GitHub App installation holding nothing
# at the account level, so creating a repository or changing a setting comes
# back 403 however it is asked for. `gh` here is you, with your scopes.
#
# What it does, in order: the Actions permission, the token secret, the
# labels, and branch protection - reading each one back after setting it,
# because the point is to leave nothing on trust.
#
# Everything printed is also appended to setup-project-output.txt, so a URL or
# a check name can be copied out of the editor. No secret value is written
# there. Safe to re-run: every step is idempotent and skips what is done.

set -uo pipefail # not -e: several steps have their own fallback path

REPO="${1:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO_ROOT/setup-project-output.txt"

log() { echo "$@" | tee -a "$OUT"; }

fail() {
  log ""
  log "STOPPED: $*"
  exit 1
}

echo "=== setup $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >>"$OUT"

if [ -z "$REPO" ]; then
  [ -t 0 ] || fail "Pass the repository: bash scripts/setup-project.sh owner/repo"
  read -r -p "Which repository? (owner/repo) " REPO
fi
case "$REPO" in */*) ;; *) fail "'$REPO' is not owner/repo." ;; esac

command -v gh >/dev/null 2>&1 || fail "No \`gh\` on PATH. This is meant for a Codespace, where it is preinstalled."

# Codespaces injects a token scoped to the repository the Codespace is on, so
# it cannot touch another repository's settings. Probe for real admin rather
# than trusting `gh auth status`, which calls a token fine when it is merely
# present.
admin() { gh api "repos/$REPO" --jq '.permissions.admin' 2>/dev/null; }

if [ "$(admin)" != "true" ]; then
  log "This terminal's token cannot administer $REPO."
  [ -t 0 ] || fail "Run: gh auth login -h github.com -s repo,workflow"
  log "Re-authenticating as you - open the URL it prints, paste the code, approve."
  gh auth login --hostname github.com --git-protocol https --scopes repo,workflow --web ||
    fail "gh auth login did not complete."
fi

if [ "$(admin)" != "true" ]; then
  log "$REPO is not visible. Creating it..."
  gh repo create "$REPO" --public --add-readme >>"$OUT" 2>&1
  [ "$(admin)" = "true" ] || fail "Still cannot administer $REPO. Check the name and that this account owns it."
fi

BRANCH="$(gh api "repos/$REPO" --jq '.default_branch')"
log "Repository: $REPO (default branch $BRANCH)"

if [ "$(gh api "repos/$REPO" --jq '.private')" = "true" ]; then
  log "WARNING: $REPO is private, so it cannot call the factory's reusable"
  log "workflows and every check will fail before it starts. Make it public at"
  log "github.com/$REPO/settings"
fi

# --- the Actions permission -------------------------------------------------
# Off by default on personal-account repositories. With it off every agent run
# goes green and silently opens no pull request, which is the most expensive
# misconfiguration here because nothing reports it.

log ""
log "Allowing Actions to create and approve pull requests..."
gh api -X PUT "repos/$REPO/actions/permissions/workflow" \
  -f default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true >>"$OUT" 2>&1

if [ "$(gh api "repos/$REPO/actions/permissions/workflow" --jq '.can_approve_pull_request_reviews' 2>/dev/null)" = "true" ]; then
  log "  confirmed: Actions may create and approve pull requests."
else
  log "  NOT SET. Agent pull requests will fail silently."
  log "  Set it by hand: github.com/$REPO/settings/actions"
fi

# --- the token secret -------------------------------------------------------

log ""
if gh secret list --repo "$REPO" --json name --jq '.[].name' 2>/dev/null | grep -qx CLAUDE_CODE_OAUTH_TOKEN; then
  log "CLAUDE_CODE_OAUTH_TOKEN is already set."
else
  token="${CLAUDE_CODE_OAUTH_TOKEN:-}"
  if [ -z "$token" ] && [ -t 0 ]; then
    log "CLAUDE_CODE_OAUTH_TOKEN is not set, and nothing agent-side runs without"
    log "it. It is the same value for every project - generate one once with"
    log "'claude setup-token' and reuse it."
    read -r -s -p "Paste it now (or press return to skip): " token
    echo
  fi
  if [ -n "$token" ]; then
    gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo "$REPO" --body "$token" >>"$OUT" 2>&1 &&
      log "CLAUDE_CODE_OAUTH_TOKEN set." ||
      log "Could not set it: github.com/$REPO/settings/secrets/actions/new"
    unset token
  else
    log "Skipped. Nothing agent-side runs until it is set:"
    log "  github.com/$REPO/settings/secrets/actions/new"
  fi
fi

# --- labels -----------------------------------------------------------------
# Created by the bootstrap workflow rather than here: their names are matched
# exactly by the agent-run preflight, and one definition beats two.

log ""
if gh api "repos/$REPO/contents/.github/workflows/bootstrap.yml?ref=$BRANCH" >/dev/null 2>&1; then
  log "Running bootstrap (creates the labels)..."
  if gh workflow run bootstrap.yml --repo "$REPO" --ref "$BRANCH" >>"$OUT" 2>&1; then
    sleep 10
    run_id="$(gh run list --repo "$REPO" --workflow bootstrap.yml --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null)"
    [ -n "$run_id" ] && gh run watch "$run_id" --repo "$REPO" --exit-status >>"$OUT" 2>&1
  fi

  missing=""
  for want in agent:queued role:engineer objective needs-human; do
    gh api "repos/$REPO/labels/${want//:/%3A}" >/dev/null 2>&1 || missing="$missing $want"
  done
  if [ -n "$missing" ]; then
    log "  labels still missing:$missing - see github.com/$REPO/actions"
  else
    log "  confirmed: labels exist (sampled agent:queued, role:engineer, objective, needs-human)."
  fi
else
  log "No .github/workflows/bootstrap.yml on $BRANCH yet."
  log "Run /new-project $REPO in a Claude session first, then re-run this."
  log "Everything above is already done and will be skipped."
  exit 0
fi

# --- branch protection ------------------------------------------------------
# Read the names back as they actually reported rather than assuming them. A
# required check that has never run blocks every merge, including the pull
# request that would fix it, so a guessed name is worse than no rule.

log ""
log "Reading the check names as they reported on $BRANCH..."
names="$(gh api "repos/$REPO/commits/$BRANCH/check-runs" --jq '.check_runs[].name' 2>/dev/null | sort -u | grep -v '^$' || true)"

if [ -z "$names" ]; then
  log "  nothing has reported yet, so there is nothing to require."
  log "  Let ci and guard run once (open any pull request), then re-run this."
else
  printf '%s\n' "$names" | sed 's/^/  /' | tee -a "$OUT"

  # `required_pull_request_reviews: null` leaves "require a pull request before
  # merging" off on purpose, so a gate can still be repaired by a direct commit.
  contexts="$(printf '%s\n' "$names" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')"
  gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" --input - >>"$OUT" 2>&1 <<JSON
{
  "required_status_checks": { "strict": true, "contexts": $contexts },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON

  got="$(gh api "repos/$REPO/branches/$BRANCH/protection" --jq '.required_status_checks.contexts[]' 2>/dev/null | sort -u)"
  if [ -n "$got" ]; then
    log "  confirmed: $BRANCH now requires them."
  else
    log "  could not set it: github.com/$REPO/settings/branches"
  fi
fi

# --- report -----------------------------------------------------------------

log ""
log "Done. github.com/$REPO"
log ""
log "Still manual, because creating a GitHub App has no API: the agent identity"
log "App (docs/checkpoint.md step 3). Without it every agent pull request needs"
log "an approval tap, and an orchestrator cannot queue its own children at all."
log "Once it exists, add AGENT_APP_ID and AGENT_APP_PRIVATE_KEY at"
log "github.com/$REPO/settings/secrets/actions/new"
log ""
log "Full output: $OUT"
