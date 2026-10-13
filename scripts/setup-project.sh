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
# Or, to read every one of those settings back and change nothing - for the
# person who set them by hand and wants them proved rather than trusted:
#
#   bash scripts/setup-project.sh --verify <owner/repo>
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

USAGE="bash scripts/setup-project.sh [--verify] <owner/repo>"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO_ROOT/setup-project-output.txt"

log() { echo "$@" | tee -a "$OUT"; }

fail() {
  log ""
  log "STOPPED: $*"
  exit 1
}

# `--verify` may come before or after the repository. Any other dash argument
# is refused, and so is a second repository. A mistyped `--verify` is the case
# that matters: read as a repository name it fails three steps later as
# something about permissions, and ignored as a trailing extra - the way this
# script once ignored everything after `$1` - it runs the setup path, the one
# that writes, for a person who asked to change nothing.
REPO=""
MODE=setup
BAD_ARGS=""
for arg in "$@"; do
  case "$arg" in
    --verify) MODE=verify ;;
    -h | --help)
      echo "Usage: $USAGE"
      exit 0
      ;;
    -*) BAD_ARGS="Unknown option '$arg'. Usage: $USAGE" ;;
    *)
      if [ -n "$REPO" ]; then
        BAD_ARGS="One repository at a time, not '$REPO' and '$arg'. Usage: $USAGE"
      else
        REPO="$arg"
      fi
      ;;
  esac
done

echo "=== $MODE $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >>"$OUT"
[ -z "$BAD_ARGS" ] || fail "$BAD_ARGS"

if [ -z "$REPO" ]; then
  [ -t 0 ] || fail "Pass the repository: $USAGE"
  read -r -p "Which repository? (owner/repo) " REPO
fi
case "$REPO" in */*) ;; *) fail "'$REPO' is not owner/repo." ;; esac

command -v gh >/dev/null 2>&1 || fail "No \`gh\` on PATH. This is meant for a Codespace, where it is preinstalled."

# Codespaces injects a token scoped to the repository the Codespace is on, so
# it cannot touch another repository's settings. Probe for real admin rather
# than trusting `gh auth status`, which calls a token fine when it is merely
# present.
admin() { gh api "repos/$REPO" --jq '.permissions.admin' 2>/dev/null; }

# --- verify: read everything back, write nothing ----------------------------
# For the person who did the handover steps by hand. Two of them - the Actions
# permission and branch protection - sit behind the same administration
# permission that stops a session writing them, so a session cannot read them
# back either, and done by hand they used to stay taken on trust for good. This
# reads every item the setup path below sets, with the person's own `gh`.
#
# It changes nothing: no setting, no secret, no workflow run, and no
# re-authentication either, so it can be pointed at any repository at any time
# without deciding anything first. scripts/test_setup_project.py holds it to
# that by failing on any call that is not a read.
#
# Three answers, kept apart because running them together is the problem this
# exists to solve: set, not set, and cannot read. A 403 is "cannot read", and
# never reported as "off".

problems=0

# report <tag> <message>. Anything but ok, optional, and note counts as a
# problem, and any problem makes the exit status non-zero.
report() {
  local tag="$1"
  shift
  case "$tag" in ok | optional | note) ;; *) problems=$((problems + 1)) ;; esac
  log "$(printf '  %-12s %s' "$tag" "$*")"
}

# The label names a JSON manifest on stdin declares, one per line.
labels_in() {
  python3 -c 'import json, sys; print("\n".join(json.load(sys.stdin).get("labels") or []))' 2>/dev/null
}

verify() {
  log "Verifying $REPO. Every line below is a read; nothing is changed."

  if ! gh api "repos/$REPO" >/dev/null 2>&1; then
    log ""
    log "  $REPO is not visible to this login. It does not exist yet, or it is"
    log "  private and this account cannot see it."
    return 1
  fi

  local branch is_admin
  branch="$(gh api "repos/$REPO" --jq '.default_branch')"
  is_admin="$(admin)"
  log "Repository: $REPO (default branch $branch)"
  if [ "$is_admin" != "true" ]; then
    log ""
    log "This login cannot administer $REPO, so the two settings behind that"
    log "permission read as CANNOT READ below - unknown, not off. To read them:"
    log "  gh auth login -h github.com -s repo,workflow"
    log "then run this again."
  fi

  log ""
  log "Visibility"
  if [ "$(gh api "repos/$REPO" --jq '.private')" = "true" ]; then
    report WRONG "private, so it cannot call the factory's reusable workflows and every check fails before it starts. github.com/$REPO/settings"
  else
    report ok "public, so it can call the factory's reusable workflows"
  fi

  log ""
  log "Actions permission - github.com/$REPO/settings/actions"
  local approve perms
  if approve="$(gh api "repos/$REPO/actions/permissions/workflow" --jq '.can_approve_pull_request_reviews' 2>/dev/null)" &&
    perms="$(gh api "repos/$REPO/actions/permissions/workflow" --jq '.default_workflow_permissions' 2>/dev/null)"; then
    if [ "$perms" = "write" ]; then
      report ok "workflows get read and write permissions"
    else
      report "NOT SET" "workflows get read-only permissions by default"
    fi
    if [ "$approve" = "true" ]; then
      report ok "Actions may create and approve pull requests"
    else
      report "NOT SET" "Actions may not create pull requests, so every agent run goes green and opens nothing"
    fi
  else
    report "CANNOT READ" "needs administration on $REPO"
  fi

  # Names only. `gh secret list` never returns a value, and nothing here asks.
  log ""
  log "Secrets - github.com/$REPO/settings/secrets/actions"
  local secrets has_token="" has_id="" has_key=""
  if secrets="$(gh secret list --repo "$REPO" --json name --jq '.[].name' 2>/dev/null)"; then
    printf '%s\n' "$secrets" | grep -qx CLAUDE_CODE_OAUTH_TOKEN && has_token=1
    printf '%s\n' "$secrets" | grep -qx AGENT_APP_ID && has_id=1
    printf '%s\n' "$secrets" | grep -qx AGENT_APP_PRIVATE_KEY && has_key=1
    if [ -n "$has_token" ]; then
      report ok "CLAUDE_CODE_OAUTH_TOKEN exists"
    else
      report "NOT SET" "CLAUDE_CODE_OAUTH_TOKEN, and nothing agent-side runs without it"
    fi
    # Half an App is worse than none. With the id and no key, minting the
    # token fails and so does every run; with the key and no id, the minting
    # step is skipped and the App is never used.
    if [ -n "$has_id" ] && [ -n "$has_key" ]; then
      report ok "AGENT_APP_ID and AGENT_APP_PRIVATE_KEY exist"
    elif [ -n "$has_id" ]; then
      report WRONG "AGENT_APP_ID without AGENT_APP_PRIVATE_KEY, so every agent run fails minting the App token"
    elif [ -n "$has_key" ]; then
      report WRONG "AGENT_APP_PRIVATE_KEY without AGENT_APP_ID, so the App is never used"
    else
      report optional "no agent identity App: every agent pull request needs an approval tap, and an orchestrator cannot queue its own children (docs/checkpoint.md step 3)"
    fi
  else
    report "CANNOT READ" "this login cannot list the secrets on $REPO"
  fi

  # Checked against what this repository's own release needs, which is what its
  # preflight matches on. A repository with no manifest yet has not been
  # provisioned, and gets this factory's current list instead.
  log ""
  log "Labels - created by github.com/$REPO/actions/workflows/bootstrap.yml"
  local wanted have name missing=""
  if wanted="$(gh api "repos/$REPO/contents/.claude/agent-factory.json?ref=$branch" -H 'Accept: application/vnd.github.raw' 2>/dev/null | labels_in)" &&
    [ -n "$wanted" ]; then
    log "  (the set $REPO's own .claude/agent-factory.json declares)"
  else
    wanted="$(labels_in <"$REPO_ROOT/plugins/agent-factory/templates/project/.claude/agent-factory.json")"
    log "  (no .claude/agent-factory.json on $branch, so not provisioned yet; checked against this factory's set)"
  fi
  if [ -z "$wanted" ]; then
    report "CANNOT READ" "no label list to check against: neither $REPO nor this checkout declares one"
  elif have="$(gh api "repos/$REPO/labels?per_page=100" --jq '.[].name' 2>/dev/null)"; then
    while IFS= read -r name; do
      [ -n "$name" ] || continue
      printf '%s\n' "$have" | grep -qxF -- "$name" || missing="$missing $name"
    done <<<"$wanted"
    if [ -n "$missing" ]; then
      report "NOT SET" "missing:$missing. Run bootstrap from the Actions tab; it creates whichever are absent"
    else
      report ok "every label the preflight matches on exists"
    fi
  else
    report "CANNOT READ" "this login cannot list the labels on $REPO"
  fi

  # Compared against what actually reported, because the drift that matters
  # reads as green: a required name that never reports blocks every merge, and
  # a renamed job silently stops being required at all.
  #
  # Two places can require a check, and the settings page offers both: a classic
  # protection rule, which only an administrator can read, and a ruleset, which
  # anyone who can read the repository can. Reading only the first reported a
  # repository protected by a ruleset as unprotected - the false alarm this mode
  # exists to get rid of.
  log ""
  log "Branch protection on $branch - github.com/$REPO/settings/branches"
  local reported required="" classic="" rulesets="" rule_read=""
  reported="$(gh api "repos/$REPO/commits/$branch/check-runs" --jq '.check_runs[].name' 2>/dev/null | sort -u | grep -v '^$' || true)"
  rulesets="$(gh api "repos/$REPO/rules/branches/$branch" --jq '.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context' 2>/dev/null || true)"
  if [ "$is_admin" = "true" ]; then
    # A 404 here is GitHub's answer for "no classic rule", which an
    # administrator is entitled to read as exactly that.
    classic="$(gh api "repos/$REPO/branches/$branch/protection" --jq '(.required_status_checks.contexts // [])[]' 2>/dev/null || true)"
    rule_read=1
  else
    report "CANNOT READ" "a classic protection rule needs administration on $REPO to read"
  fi
  required="$(printf '%s\n%s\n' "$classic" "$rulesets" | grep -v '^$' | sort -u || true)"
  if [ -z "$required" ] && [ -n "$rule_read" ]; then
    report "NOT SET" "nothing requires a status check - no classic rule and no ruleset - so a red check does not block a merge"
  fi
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    if printf '%s\n' "$reported" | grep -qxF -- "$name"; then
      report ok "requires '$name', which reports on $branch"
    else
      report WRONG "requires '$name', which has never reported on $branch, so every merge blocks on it - including the one that would fix it"
    fi
  done <<<"$required"
  # Without the classic rule, a reported name cannot be called unrequired, so
  # it is listed as-is for the person to compare against the settings page.
  if [ -z "$reported" ]; then
    report note "nothing has reported on $branch yet. Let ci and guard run once (open any pull request)"
  else
    while IFS= read -r name; do
      [ -n "$name" ] || continue
      if printf '%s\n' "$required" | grep -qxF -- "$name"; then
        continue
      elif [ -n "$rule_read" ]; then
        report note "'$name' reports on $branch and is not required"
      else
        report note "'$name' reports on $branch"
      fi
    done <<<"$reported"
  fi

  log ""
  if [ "$problems" -eq 0 ]; then
    log "Everything the setup path sets is in place on $REPO."
  else
    log "$problems item(s) above need attention. CANNOT READ means unknown, not off."
  fi
  log "Not readable with a personal login: whether the agent identity App is"
  log "installed on $REPO. github.com/settings/installations"
  log ""
  log "Full output: $OUT"
  [ "$problems" -eq 0 ]
}

if [ "$MODE" = "verify" ]; then
  verify
  exit $?
fi

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
log "To read all of this back later, changing nothing:"
log "  bash scripts/setup-project.sh --verify $REPO"
log ""
log "Full output: $OUT"
