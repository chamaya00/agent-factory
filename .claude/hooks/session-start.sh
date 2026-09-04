#!/bin/bash
#
# Tells a session, before its first edit, the two things about this repository
# it cannot see and reliably gets wrong: which release the manifest is on, and
# whether plugins/agent-factory/ and its .claude/ mirror still agree.
#
# Both are cheap to check and expensive to discover in CI, because the mirror
# failure looks like a passing edit until guard.yml rejects it.
#
# Deliberately not `set -e`: this reports, it does not gate. A session that
# cannot start because a validator failed is worse than the failure it found.

set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}" || exit 0

# pyyaml is the only dependency any check here has, and only
# validate_workflows.py needs it. Installed in a throwaway container, never on
# somebody's own machine.
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  python3 -m pip install --quiet --disable-pip-version-check pyyaml >/dev/null 2>&1 || true
fi

manifest="plugins/agent-factory/.claude-plugin/plugin.json"
version="$(python3 -c "import json; print(json.load(open('$manifest'))['version'])" 2>/dev/null || echo unreadable)"

echo "agent-factory: manifest version $version. Releases are cut by hand from the Actions tab."

if output="$(python3 scripts/validate_plugin.py 2>&1)"; then
  echo "validate_plugin.py: clean. plugins/agent-factory/ and .claude/ agree."
else
  echo "validate_plugin.py: FAILING already, before this session changed anything."
  echo "$output"
  echo "Fix or report this before editing. The source is plugins/agent-factory/; .claude/ is the copy."
fi

exit 0
