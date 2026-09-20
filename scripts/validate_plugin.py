#!/usr/bin/env python3
"""Structural checks for the agent-factory plugin.

Deterministic only. Every failure here names a file and a fix; nothing in this
script requires judgment, because a check that requires judgment is not a gate.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "plugins" / "agent-factory"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"

# The clause every role definition has to end with, verbatim. Agents that do not
# carry it can read the wrong memory file or write where they must not.
#
# The path is `docs/memory/` and not `.claude/memory/` for a reason a run found
# the hard way: a file under `.claude/` is classified sensitive upstream, and
# that classification is consulted before any permission setting, so no
# allowlist this repository writes can lift it. Two runs were refused the edit
# the memory protocol asks them for, said so honestly in their pull requests,
# and spent an attempt each. See the memory-protocol skill for the whole of it.
REQUIRED_CLAUSE = """Before starting, read `docs/memory/<your-role>.md` if it exists.
It contains lessons specific to this repository.

Never write to files under the plugin directory.
Never modify anything under .github/workflows/ or CODEOWNERS."""

# Nouns that tie a file to one stack, one vendor, or one product. The plugin
# describes how we work, so none of these belong in it.
BANNED_NOUNS = [
    "react", "vue", "svelte", "angular", "nextjs", "next.js", "nuxt", "remix",
    "tailwind", "vercel", "netlify", "cloudflare", "heroku", "render.com",
    "supabase", "firebase", "planetscale", "postgres", "postgresql", "mysql",
    "sqlite", "mongodb", "dynamodb", "prisma", "drizzle", "sequelize", "redis",
    "stripe", "twilio", "sendgrid", "auth0", "clerk", "shopify",
    "expo", "swiftui", "flutter", "kotlin", "django", "rails", "laravel",
    "flask", "fastapi", "spring boot",
    "kubernetes", "docker", "terraform", "ansible",
    "aws", "gcp", "azure", "s3 bucket", "lambda function",
    "openai", "gemini", "llama",
    "jira", "notion", "linear.app", "asana", "trello", "figma", "slack",
    "sentry", "datadog", "amplitude", "mixpanel", "posthog", "segment",
]

MAX_AGENT_BODY_LINES = 45

# Capabilities a role either has or does not have, for the check that keeps
# prose and frontmatter telling the same story.
#
# `tools` is every tool that would let the role do the thing: holding any one of
# them makes a sentence saying it cannot a false statement.
#
# Entries are hand-written and the list is short on purpose. A denial has to be
# a claim about capability here, never a restriction on a tool the role holds -
# a role is legitimately handed `Write` and told never to touch source code, and
# that sentence must not fail the gate. So file writing is not in this table and
# must not be added to it, and neither may anything else a role is granted and
# then told not to use. The test for a new entry is whether "granted, but
# forbidden to use it" would be an incoherent arrangement for that capability.
#
# `runtime` is the second half of the same story, and it is the half that used
# to be missing. Frontmatter is not what gates a command inside a workflow run:
# `.github/workflows/agent-run.yml` builds a separate per-role allowlist, and
# that is what the action enforces. The two lists were maintained independently
# and nothing compared them, so a role could be told to do something, hold the
# frontmatter tool for it, and be refused at run time with every check green -
# which is the exact failure the instruction check exists to prevent, one layer
# down. Each entry therefore also names the allowlist entries that satisfy it in
# a run. They are matched verbatim, as strings: this check never reimplements
# the action's own prefix matcher, because a second implementation of a matcher
# is a second thing to be wrong, and the table is small enough to name entries
# exactly.
CAPABILITIES = [
    {
        "name": "open a pull request",
        "tools": {"mcp__github__create_pull_request", "Bash"},
        "object": r"pull\s+requests?",
        "verbs": r"(?:open|opens|opening|create|creates|creating|file|files|"
                 r"filing|raise|raises|raising|submit|submits|submitting)",
        # Imperative or gerund only. "nobody opened a pull request for it" is a
        # description of what went wrong, not an instruction to open one.
        "instruction": r"(?:\bopen(?:ing)?\s+(?:a|an|its\s+own|their\s+own|the|one)"
                       r"(?:\s+\w+){0,2}\s+pull\s+request|\bgh\s+pr\s+create\b)",
        "runtime": {"Bash(gh pr create:*)"},
    },
    {
        "name": "file an issue",
        # No Bash. A role holding a shell could in principle reach any of this,
        # which would make Bash a wildcard that claims every role capable of
        # everything - and the first sentence saying a role with a shell does
        # not file issues would fail the gate for being true. Bash is listed
        # only for pull requests, where a role file does instruct the shell form.
        "tools": {"mcp__github__issue_write", "mcp__github__sub_issue_write"},
        "object": r"\bissues?\b",
        "verbs": r"(?:file|files|filing|open|opens|opening|create|creates|"
                 r"creating|write|writes|writing|label|labels|labelling|labeling)",
        "instruction": r"\b(?:file|open|create)\s+(?:a|an|the|each|its\s+own)"
                       r"(?:\s+\w+){0,2}\s+issues?\b",
        "runtime": {"Bash(gh issue create:*)"},
    },
    {
        "name": "search the web",
        "tools": {"WebSearch"},
        "object": r"(?:\bthe\s+web\b|\bweb\s+search)",
        "verbs": r"(?:search|searches|searching|query|queries|querying|browse|"
                 r"browses|browsing|look|looks|looking)",
        "instruction": r"\bsearch\s+the\s+web\b",
        # The action lists WebSearch in its own disallowed set, so naming it in
        # the allowlist is what makes it reachable. Frontmatter alone does not.
        "runtime": {"WebSearch"},
    },
]

# A role name reaches prose as itself or as a plural.
ROLE_MENTION = r"\b{role}s?\b"

# Ways prose says a subject cannot do something. Deliberately explicit: "nobody
# opened one" and "no pull request exists" describe a state of the world and are
# not claims about what a role is able to do.
NEGATION = (
    r"(?:cannot|can\s+not|can't|could\s+not|couldn't|may\s+not|"
    r"is\s+unable\s+to|are\s+unable\s+to|is\s+not\s+able\s+to|"
    r"are\s+not\s+able\s+to|isn't\s+able\s+to|aren't\s+able\s+to|"
    r"has\s+no\s+way\s+to|have\s+no\s+way\s+to|"
    r"lacks\s+the\s+ability\s+to|lack\s+the\s+ability\s+to|"
    r"no\s+role\s+(?:\w+\s+){0,4}can)"
)

# Words that scope a claim to a condition rather than denying a capability.
QUALIFIER = r"\b(?:without|unless|until|except|before|only\s+(?:when|if|after))\b"

# Sentence ends, a blank line, a list item, or a heading. Prose here wraps
# mid-sentence, so a single newline is not a boundary.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n\s*\n+|\n(?=\s*[-*+]\s)|\n(?=\s*\#)")

# Suffixes carrying prose a session or an agent reads and believes.
PROSE_SUFFIXES = {".md", ".yml", ".yaml", ".py"}

# Comment markers stripped before a block is read as prose, so a claim spread
# over several comment lines reads as the one sentence it is.
COMMENT_PREFIX = re.compile(r"^\s*(?:\#+|//)\s?", re.M)

# The two files that contain false capability claims on purpose: this script,
# which carries the patterns, and the script that proves them. Kept to exactly
# these two by path - a wider exemption would hide the drift this is for.
CLAIM_FIXTURES = {
    "scripts/validate_plugin.py",
    "scripts/test_capability_claims.py",
}

# What a template writes instead of a release tag. Provisioning substitutes it.
PIN_PLACEHOLDER = "__FACTORY_VERSION__"
OWNER_PLACEHOLDER = "__PROJECT_OWNER__"
REPO_PLACEHOLDER = "__FACTORY_REPO__"
ROLES = ["orchestrator", "researcher", "analyst", "designer", "engineer"]

# The commands a provisioned project receives. `new-project` is deliberately not
# among them: provisioning is the factory's job, and a project that can
# provision another project is a second factory nobody is maintaining.
PROJECT_COMMANDS = ["objective", "retro", "decompose", "update-agents", "ship", "check-in"]

# Hooks a provisioned project receives. Unlike roles, skills and commands these
# are not mirrored into this repository's own `.claude/`: the factory runs its
# own session-start hook for its own reasons, and the two have nothing to say to
# each other.
PROJECT_HOOKS = ["session-start"]

errors: list[str] = []


def fail(path: Path, message: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {message}")


def split_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    """Parse the leading --- block as flat key: value pairs.

    Deliberately not a YAML parser: the frontmatter we require is flat, and a
    hand-rolled reader keeps this script runnable with no dependencies. Where
    PyYAML is available the block is parsed for real as well, since this reader
    happily accepts things a real YAML parser rejects - an unquoted value
    containing `: ` being the one that will actually happen.
    """
    if not text.startswith("---\n"):
        fail(path, "missing YAML frontmatter (file must start with ---)")
        return {}, text
    end = text.find("\n---\n", 3)
    if end == -1:
        fail(path, "frontmatter is never closed with ---")
        return {}, text
    block = text[4:end]
    body = text[end + 5 :]
    strict_parse(block, path)
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            fail(path, f"frontmatter line is not key: value -> {line!r}")
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body


def strict_parse(block: str, path: Path) -> None:
    """Second opinion from a real YAML parser, when there is one to ask."""
    try:
        import yaml
    except ImportError:
        return
    try:
        parsed = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        fail(path, f"frontmatter is not valid YAML: {exc}")
        return
    if not isinstance(parsed, dict):
        fail(path, "frontmatter does not parse to a mapping")


def check_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        errors.append(f"{path.relative_to(ROOT)}: missing")
    except json.JSONDecodeError as exc:
        fail(path, f"does not parse as JSON: {exc}")
    return None


def check_marketplace() -> None:
    data = check_json(MARKETPLACE)
    if data is None:
        return
    for field in ("name", "owner", "plugins"):
        if field not in data:
            fail(MARKETPLACE, f"missing required field {field!r}")
    owner = data.get("owner")
    if isinstance(owner, dict) and "name" not in owner:
        fail(MARKETPLACE, "owner is missing required field 'name'")
    for entry in data.get("plugins", []):
        for field in ("name", "source"):
            if field not in entry:
                fail(MARKETPLACE, f"plugin entry missing required field {field!r}")
        # Declared in both places, plugin.json wins with no warning - so an
        # edit here would look like a release and install as the version
        # already cached.
        if "version" in entry:
            fail(
                MARKETPLACE,
                f"plugin entry {entry.get('name')!r} declares a version; "
                "plugin.json is the single source and silently overrides this one",
            )
        source = entry.get("source")
        if isinstance(source, str):
            if not source.startswith("./"):
                fail(MARKETPLACE, f"relative source must start with ./ -> {source!r}")
            elif not (ROOT / source).is_dir():
                fail(MARKETPLACE, f"source path does not exist -> {source!r}")


def check_plugin_manifest() -> None:
    manifest = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
    data = check_json(manifest)
    if data is None:
        return
    # An explicit name is the whole point: without it plugin identity falls back
    # to the install directory name, which changes on every update.
    if not data.get("name"):
        fail(manifest, "must set an explicit 'name'")
    elif data["name"] != PLUGIN_DIR.name:
        fail(manifest, f"name {data['name']!r} does not match directory {PLUGIN_DIR.name!r}")
    if not data.get("version"):
        fail(manifest, "must set a 'version'")


def check_agents() -> None:
    agents_dir = PLUGIN_DIR / "agents"
    found = sorted(p.stem for p in agents_dir.glob("*.md"))
    for role in ROLES:
        if role not in found:
            errors.append(f"plugins/agent-factory/agents/{role}.md: missing")
    for path in sorted(agents_dir.glob("*.md")):
        text = path.read_text()
        fields, body = split_frontmatter(text, path)
        for field in ("name", "description"):
            if not fields.get(field):
                fail(path, f"frontmatter missing required field {field!r}")
        if fields.get("name") and fields["name"] != path.stem:
            fail(path, f"frontmatter name {fields['name']!r} does not match filename")
        if ":" in fields.get("name", ""):
            fail(path, "agent name may not contain ':'")
        body_lines = [line for line in body.strip().splitlines()]
        if len(body_lines) > MAX_AGENT_BODY_LINES:
            fail(path, f"body is {len(body_lines)} lines, cap is {MAX_AGENT_BODY_LINES}")
        if body.strip() != "" and not body.strip().endswith(REQUIRED_CLAUSE):
            fail(path, "does not end with the required memory and containment clause")


def check_skills() -> None:
    skills_dir = PLUGIN_DIR / "skills"
    for path in sorted(skills_dir.glob("*/SKILL.md")):
        fields, _ = split_frontmatter(path.read_text(), path)
        for field in ("name", "description"):
            if not fields.get(field):
                fail(path, f"frontmatter missing required field {field!r}")
        if fields.get("name") and fields["name"] != path.parent.name:
            fail(path, f"frontmatter name {fields['name']!r} does not match directory")
    for child in sorted(skills_dir.iterdir()):
        if child.is_dir() and not (child / "SKILL.md").exists():
            fail(child, "skill directory has no SKILL.md")


def check_commands() -> None:
    commands_dir = PLUGIN_DIR / "commands"
    if not commands_dir.is_dir():
        return
    for path in sorted(commands_dir.glob("*.md")):
        fields, _ = split_frontmatter(path.read_text(), path)
        if not fields.get("description"):
            fail(path, "frontmatter missing required field 'description'")


def check_named_project_commands() -> None:
    """A command a role is told the name of has to be a command that exists.

    The designer held a shell grant for rendering mocks through an entire
    objective and never rendered one. Nothing was broken: the grant was real,
    the role was told to render, and the two never met, because no project
    shipped anything to call and the role had no name to reach for. The design
    was specified, built and merged with no eye on a rendered page, and every
    check stayed green throughout - the failure mode of a capability is silence.

    So the moment a role names `./scripts/<thing>`, the project template owes
    every repository that file, executable. This is deliberately about the
    template rather than about any one project: a role file and the template
    ship together in a release, so if they disagree here they disagree
    everywhere at once, which is exactly the class of thing a gate should
    refuse before it is cut rather than after.
    """
    named: dict[str, list[str]] = {}
    granted = role_tools()
    runtime = runtime_allowlist()
    for path in sorted((PLUGIN_DIR / "agents").glob("*.md")):
        role = path.stem
        text = path.read_text()
        matches = list(re.finditer(r"`\./scripts/([A-Za-z0-9_.-]+)", text))
        for match in matches:
            named.setdefault(match.group(1), []).append(path.name)
        if not matches:
            continue
        # Naming the command is half of it. A role that cannot run anything is
        # told a name it will be refused, which is the same spent attempt the
        # unnamed version cost - and the two grants live in two different files,
        # so neither one of them can be read as covering the other.
        if "Bash" not in granted.get(role, set()):
            fail(
                path,
                f"tells the {role} to run './scripts/...' and its frontmatter "
                "grants no Bash. Add it, or stop naming the command",
            )
        if runtime and RUNTIME_SCRIPTS_GRANT not in runtime.get(role, set()):
            fail(
                path,
                f"tells the {role} to run './scripts/...' and "
                f".github/workflows/agent-run.yml does not grant "
                f"{RUNTIME_SCRIPTS_GRANT} in the {role} branch, so a run is "
                "refused the command this file names",
            )

    template_scripts = PLUGIN_DIR / "templates" / "project" / "scripts"
    for name, roles in sorted(named.items()):
        where = ", ".join(sorted(set(roles)))
        script = template_scripts / name
        if not script.is_file():
            fail(
                script,
                f"{where} tells a role to run './scripts/{name}', and the project "
                f"template does not ship it - every repository provisioned from "
                f"this release would name a command it does not have",
            )
            continue
        if not os.access(script, os.X_OK):
            fail(
                script,
                f"is not executable; {where} calls it as './scripts/{name}', "
                f"which refuses without the execute bit - present, silent, and "
                f"indistinguishable from having run",
            )


def check_template_memory_files() -> None:
    """The template ships one memory file per role, and none for a role that is gone.

    A graduated lesson rather than a convention. The template shipped four of
    the five for as long as there have been five roles, so every repository
    provisioned in that time had an analyst reading a path that was not there -
    silently, because a missing memory file reads exactly like an empty one, and
    the role's own clause says "if it exists". The cap in `project-guard.yml`
    could not catch it either: a file that is absent is inside any cap.
    """
    memory = PLUGIN_DIR / "templates" / "project" / "docs" / "memory"
    if not memory.is_dir():
        fail(memory, "does not exist; provisioning would leave every role reading nothing")
        return
    for role in ROLES:
        path = memory / f"{role}.md"
        if not path.is_file():
            fail(
                path,
                f"is missing, so a provisioned repository gives the {role} no "
                "memory file. An absent file reads as an empty one, which is "
                "how this went unnoticed through several releases",
            )
    for path in sorted(memory.glob("*.md")):
        if path.stem not in ROLES:
            fail(path, f"is a memory file for '{path.stem}', which is not a role")


def check_portability() -> None:
    """The check that keeps this plugin reusable a year from now."""
    for path in sorted(PLUGIN_DIR.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".json"}:
            continue
        lowered = path.read_text().lower()
        for noun in BANNED_NOUNS:
            # Word-ish boundary so "aws" does not fire inside "flaws".
            if re.search(rf"(?<![a-z0-9]){re.escape(noun)}(?![a-z0-9])", lowered):
                fail(path, f"project-specific noun {noun!r} does not belong in the plugin")


EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002190-\U000021FF\U00002300-\U000027BF"
    "\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0001F1E6-\U0001F1FF]"
)


def check_no_emoji() -> None:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git/" in str(path.relative_to(ROOT)) or path.suffix not in {".md", ".json", ".yml", ".yaml", ".py"}:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            found = EMOJI.search(line)
            if found:
                fail(path, f"line {number} contains emoji {found.group()!r}")


def check_label_vocabulary_is_declared() -> None:
    """A project has to be able to find out which labels it is missing.

    Only `bootstrap` creates a label, it is workflow_dispatch only, and only a
    person can run it. So a release that adds one ships the name in files and
    leaves the label itself absent until somebody notices - and the failure is
    silent: the preflight matches on a label nothing can apply, the run that
    should have started does not, and nothing reports it. It cost a real
    release here before anything checked.

    The fix needs the required set to exist somewhere a project carries, which
    is the template manifest. This keeps that copy honest against the one place
    the labels are really created. Order matters too: the manifest is read by a
    person comparing it with `bootstrap.yml`, and two lists in different orders
    are far harder to diff by eye than two lists in the same one.
    """
    manifest = PLUGIN_DIR / "templates" / "project" / ".claude" / "agent-factory.json"
    bootstrap = ROOT / ".github" / "workflows" / "bootstrap.yml"
    if not manifest.is_file() or not bootstrap.is_file():
        return
    data = check_json(manifest)
    if data is None:
        return
    created = re.findall(r"^\s*label\s+([a-z:-]+)", bootstrap.read_text(), re.M)
    if not created:
        fail(bootstrap, "no `label` lines, so nothing here creates the vocabulary a project needs.")
        return
    declared = data.get("labels")
    if declared is None:
        fail(
            manifest,
            "declares no `labels`, so nothing shipped to a project can say which "
            "labels it is missing after a release adds one.",
        )
        return
    if declared != created:
        missing = [name for name in created if name not in declared]
        extra = [name for name in declared if name not in created]
        if missing:
            fail(manifest, f"does not declare label(s) bootstrap.yml creates: {', '.join(missing)}")
        if extra:
            fail(manifest, f"declares label(s) bootstrap.yml never creates: {', '.join(extra)}")
        if not missing and not extra:
            fail(manifest, "declares the same labels as bootstrap.yml in a different order; keep them in step so the two can be read side by side.")


def check_template_pins() -> None:
    """Every caller a project receives names the factory by placeholder, twice.

    Two things in a `uses:` line could be hardcoded, and both ship silently to
    every repository provisioned afterwards.

    The ref, which this check was written for: a template that hardcodes one
    pins every later project to that release, and a moving one puts them all
    back on a live pointer, which is the thing the pinning is for.

    The owner, which it used to be blind to. The pattern held the factory's own
    account inside itself, so it matched `uses:` lines naming that account and
    nothing else. In a fork where the owner had been changed it matched
    nothing - and a check that matches nothing does not fail, it goes quiet. A
    fork could hardcode a ref in all four callers and the gate stayed green.
    The same literal was the larger bug underneath: a fork that changed nothing
    provisioned repositories calling *upstream's* reusable workflows, with
    every check green and every run succeeding, none of it the code the person
    thought they were running.

    So this is anchored on the shape of a reusable workflow reference rather
    than on anybody's account, and both halves have to be a placeholder.
    `docs/decisions/0001-factory-repo-is-declared-in-the-manifest.md` records
    where the substituted values come from.
    """
    templates = PLUGIN_DIR / "templates"
    if not templates.is_dir():
        return
    # `<something>/.github/workflows/<file>` is the shape of a reusable
    # workflow call and nothing else, so this finds every caller without
    # knowing who owns it. The ref group is optional on purpose: a reference
    # with no `@` at all is also wrong, and a pattern that simply failed to
    # match it would be the quiet failure this check exists to stop.
    pattern = re.compile(
        r"uses:\s*(?P<repo>[^@\s]+?)/\.github/workflows/[^@\s]+?(?:@(?P<ref>\S+))?\s*$"
    )
    for path in sorted(templates.rglob("*.yml")) + sorted(templates.rglob("*.yaml")):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            found = pattern.search(line)
            if not found:
                continue
            if found.group("repo") != REPO_PLACEHOLDER:
                fail(
                    path,
                    f"line {number} addresses the factory as "
                    f"{found.group('repo')!r}; templates must use "
                    f"{REPO_PLACEHOLDER} so provisioning substitutes the "
                    "factory this session is running out of. A literal here "
                    "means a fork provisions repositories that call somebody "
                    "else's workflows, silently and greenly",
                )
            ref = found.group("ref")
            if ref is None:
                fail(
                    path,
                    f"line {number} calls a reusable workflow with no `@ref` "
                    f"at all; it must end {PIN_PLACEHOLDER} so provisioning "
                    "substitutes the installed release",
                )
            elif ref != PIN_PLACEHOLDER:
                fail(
                    path,
                    f"line {number} pins the factory at {ref!r}; templates "
                    f"must use {PIN_PLACEHOLDER} so provisioning substitutes "
                    "the installed release",
                )


def factory_repo() -> str | None:
    """The `owner/repo` this factory declares itself to be, or None.

    Read out of the plugin manifest's `repository`, which already existed and
    already had to be right - making it the declaration costs a fork one line
    it was going to edit anyway.
    """
    manifest = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return None
    try:
        declared = json.loads(manifest.read_text()).get("repository") or ""
    except json.JSONDecodeError:
        return None
    found = re.search(r"github\.com[/:]([^/\s]+/[^/\s.]+)", declared)
    return found.group(1) if found else None


def check_factory_repo_is_declared() -> None:
    """The factory says which repository it is, and its remote does not disagree.

    The callers a project receives address the factory through
    `__FACTORY_REPO__`, and provisioning substitutes the `owner/repo` in the
    manifest's `repository` field. ADR 0001 has the reasoning. What matters
    here is the one failure that choice leaves open: a fork that never edits
    the field provisions repositories pointing at upstream, which is silent,
    green, and precisely the bug the placeholder was added to fix.

    So the declaration is cross-checked against this checkout's own `origin`.
    The remote is deliberately not the source - a detached or mirrored checkout
    has none, or has an unhelpful one, and the manifest still has to be
    authoritative there. It is a witness. Where a remote is readable and
    disagrees, a fork hears about it in one line at its own first build,
    instead of hearing nothing and finding out from a provisioned repository
    that quietly runs somebody else's code.

    A pull request from a fork to this repository does not trip it: the
    checkout for that run is this repository, so `origin` is this repository.
    """
    manifest = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
    declared = factory_repo()
    if declared is None:
        fail(
            manifest,
            "declares no parseable `repository`, so provisioning has nothing "
            f"to substitute for {REPO_PLACEHOLDER} in the four caller "
            "templates. It must be the factory's own GitHub URL",
        )
        return

    try:
        done = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return
    if done.returncode != 0:
        return
    found = re.search(r"github\.com[/:]([^/\s]+/[^/\s]+?)(?:\.git)?$", done.stdout.strip())
    if found is None:
        return
    remote = found.group(1)
    if remote.lower() != declared.lower():
        fail(
            manifest,
            f"declares this factory as {declared!r}, but `origin` is "
            f"{remote!r}. Provisioning writes the declared value into every "
            "caller it creates, so projects provisioned from this checkout "
            "would call a factory nobody here can edit. If this is a fork, "
            "change `repository` to this fork; if the remote is the odd one "
            "out, leave the manifest alone",
        )


def check_runbooks_name_every_project_command() -> None:
    """The two runbooks that copy commands must name the set actually copied.

    `PROJECT_COMMANDS` is the real list - the template manifest is checked
    against it and every name in it must have a file - but the prose that does
    the copying was checked by nothing, and both copies had drifted.
    `new-project.md` named five and `update-agents.md` named three. The one
    missing from both was `check-in`, which `templates/project/CLAUDE.md` tells
    every provisioned repository to run by name, so a session following either
    runbook literally shipped a repository whose own instructions point at a
    command that is not there.

    Checked as prose rather than generated from the list, because the sentences
    around these names carry the reasons - which command stays in the factory,
    and why - that a generated list would drop.
    """
    for name in ("new-project.md", "update-agents.md"):
        path = PLUGIN_DIR / "commands" / name
        if not path.is_file():
            continue
        text = path.read_text()
        missing = [command for command in PROJECT_COMMANDS if f"{command}.md" not in text]
        if missing:
            fail(
                path,
                f"tells a session which commands a project receives but never "
                f"names {sorted(missing)}. A command left out here is one that "
                "does not get copied, while the project's own CLAUDE.md may "
                "still call it",
            )


def check_template_owner_placeholder() -> None:
    """The CODEOWNERS a project receives names its owner, never this one.

    It used to ship a literal handle with a line of prose telling the session
    to change it, which works until the once it does not - and a skipped
    substitution is invisible, because what lands is a syntactically perfect
    gate file naming an account that owns nothing here. It reviews nothing and
    reads as though somebody configured it.

    Same reasoning as the version pin, same fix: a placeholder cannot be
    forgotten quietly, because the string is still sitting there to be found.
    """
    codeowners = PLUGIN_DIR / "templates" / "project" / ".github" / "CODEOWNERS"
    if not codeowners.is_file():
        errors.append(
            f"{codeowners.relative_to(ROOT)}: missing, but projects are provisioned with it"
        )
        return
    text = codeowners.read_text()
    if OWNER_PLACEHOLDER not in text:
        fail(
            codeowners,
            f"carries no {OWNER_PLACEHOLDER}, so provisioning has nothing to "
            "substitute the repository's own owner into",
        )
    # A handle starts with an alphanumeric, so the placeholder's leading
    # underscore keeps it out of this on purpose.
    for number, line in enumerate(text.splitlines(), start=1):
        found = re.search(r"@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", line)
        if found:
            fail(
                codeowners,
                f"line {number} names {found.group()!r}; use {OWNER_PLACEHOLDER} "
                "so provisioning substitutes the owner of the repository being "
                "provisioned",
            )


PLACEHOLDER_STEP = "CLAUDE.md carries no unfilled placeholder"
WHOLE_LINE_BRACKET = re.compile(r"^\[.*\]$")
ANY_BRACKET = re.compile(r"\[[^\[\]]*\]")


def check_template_placeholders_are_visible() -> None:
    """Every placeholder the template ships has to be one the guard can see.

    `project-guard.yml` fails a provisioned repository whose `CLAUDE.md` still
    carries a bracketed line, which is what stops a skipped substitution being
    invisible - and invisible is what it is otherwise, because a placeholder
    reads as prose and the file it sits in is the first thing every agent run
    loads.

    It matches a bracket that is the whole line, and only that, because that is
    the one shape ordinary markdown never takes: a link, a reference definition
    and a task list item all carry brackets mid-line, and a check that failed
    those would fail projects for writing sentences and be deleted within the
    week.

    Which puts one obligation on this side. A placeholder tucked into a line
    with anything else on it - `- Install: [command]`, as this template shipped
    for a year - would provision, read as configured, and walk straight past
    the guard that exists to catch exactly it. So the template may only place a
    placeholder on a line of its own, and that is what this checks.
    """
    template = PLUGIN_DIR / "templates" / "project" / "CLAUDE.md"
    guard = ROOT / ".github" / "workflows" / "project-guard.yml"

    if not template.is_file():
        errors.append(
            f"{template.relative_to(ROOT)}: missing, but projects are provisioned with it"
        )
        return

    if guard.is_file() and PLACEHOLDER_STEP not in guard.read_text():
        fail(
            guard,
            f"has no {PLACEHOLDER_STEP!r} step, so nothing stops a provisioned "
            "CLAUDE.md keeping the template's placeholder. Either restore the "
            "step or stop shipping placeholders in the template",
        )

    for number, line in enumerate(template.read_text().splitlines(), start=1):
        if WHOLE_LINE_BRACKET.match(line.strip()):
            continue
        for found in ANY_BRACKET.finditer(line):
            # A markdown link and a reference definition are what the guard
            # deliberately ignores, so they are not placeholders here either.
            if line[found.end():found.end() + 1] in ("(", ":"):
                continue
            fail(
                template,
                f"line {number} puts {found.group()!r} on a line with other "
                "text. project-guard only sees a bracket that is the whole "
                "line, so this one provisions and is never caught - give it a "
                "line of its own, or write the guidance as prose",
            )


def check_vendored_roles() -> None:
    """The roles get copied into each project, so they have to be copyable.

    If the plugin stopped shipping one, the copy would succeed and write
    nothing. That surfaces as an agent with no rules rather than as an error
    here, which is the expensive way to find out.
    """
    manifest = PLUGIN_DIR / "templates" / "project" / ".claude" / "agent-factory.json"
    if not manifest.is_file():
        errors.append(f"{manifest.relative_to(ROOT)}: missing")
        return
    data = check_json(manifest)
    if data is None:
        return
    if data.get("version") != PIN_PLACEHOLDER:
        fail(manifest, f"version must be {PIN_PLACEHOLDER}, substituted at provision time")
    if set(data.get("roles") or []) != set(ROLES):
        fail(manifest, f"roles {sorted(data.get('roles') or [])} do not match the plugin's {sorted(ROLES)}")
    on_disk = {p.parent.name for p in (PLUGIN_DIR / "skills").glob("*/SKILL.md")}
    if set(data.get("skills") or []) != on_disk:
        fail(manifest, f"skills {sorted(data.get('skills') or [])} do not match {sorted(on_disk)} on disk")
    if set(data.get("commands") or []) != set(PROJECT_COMMANDS):
        fail(
            manifest,
            f"commands {sorted(data.get('commands') or [])} do not match the "
            f"set a project is provisioned with, {sorted(PROJECT_COMMANDS)}",
        )
    for name in PROJECT_COMMANDS:
        if not (PLUGIN_DIR / "commands" / f"{name}.md").is_file():
            errors.append(f"plugins/agent-factory/commands/{name}.md: missing, but projects are provisioned with it")

    if set(data.get("hooks") or []) != set(PROJECT_HOOKS):
        fail(
            manifest,
            f"hooks {sorted(data.get('hooks') or [])} do not match the set a "
            f"project is provisioned with, {sorted(PROJECT_HOOKS)}",
        )
    template_claude = PLUGIN_DIR / "templates" / "project" / ".claude"
    for name in PROJECT_HOOKS:
        hook = template_claude / "hooks" / f"{name}.sh"
        if not hook.is_file():
            errors.append(f"{hook.relative_to(ROOT)}: missing, but projects are provisioned with it")
        elif not hook.stat().st_mode & 0o111:
            fail(hook, "is not executable, so the hook it is wired to will never run")

    # The factory ships this file, and it is the file where permissions live.
    # That makes it a channel by which a release could widen what automation may
    # do in every project at once - the thing project-guard exists to catch, and
    # which it cannot see here because it reads workflow YAML. So the shipped
    # copy carries hooks and nothing else, enforced rather than promised.
    settings = template_claude / "settings.json"
    if not settings.is_file():
        errors.append(f"{settings.relative_to(ROOT)}: missing, but projects are provisioned with it")
    else:
        shipped = check_json(settings)
        if shipped is not None and set(shipped) - {"hooks"}:
            fail(
                settings,
                f"declares {sorted(set(shipped) - {'hooks'})}; the shipped copy carries "
                "hooks and nothing else. Permissions and env belong to the project, "
                "and a factory release must not be able to widen them everywhere at once.",
            )


def check_self_vendored() -> None:
    """This repository has to carry its own copy of what it ships.

    A marketplace declared in a repository's `.claude/settings.json` is dropped
    unless the folder has been trusted for project plugins, and a cloud session
    has nobody to answer the trust prompt. So a session opened here loads
    commands, agents, and skills from `.claude/` or it loads none of them, and
    `/new-project` is not offered - which is how the factory stops being able
    to provision anything.

    The copies are real files rather than links because that is what a session
    reads, so the only thing keeping them honest is this check.
    """
    for kind in ("commands", "agents", "skills"):
        source = PLUGIN_DIR / kind
        vendored = ROOT / ".claude" / kind
        if not vendored.is_dir():
            errors.append(
                f".claude/{kind}: missing; copy plugins/agent-factory/{kind}/ here, "
                "or a session on this repository gets none of them"
            )
            continue
        expected = {p.relative_to(source): p for p in sorted(source.rglob("*")) if p.is_file()}
        actual = {p.relative_to(vendored): p for p in sorted(vendored.rglob("*")) if p.is_file()}
        for rel in sorted(set(expected) - set(actual)):
            errors.append(f".claude/{kind}/{rel}: missing; it exists in the plugin and has to be copied here")
        for rel in sorted(set(actual) - set(expected)):
            errors.append(f".claude/{kind}/{rel}: not in the plugin; delete it or add it to plugins/agent-factory/{kind}/")
        for rel in sorted(set(expected) & set(actual)):
            if expected[rel].read_bytes() != actual[rel].read_bytes():
                errors.append(
                    f".claude/{kind}/{rel}: differs from plugins/agent-factory/{kind}/{rel}; "
                    "the plugin is the source, copy it over rather than editing the copy"
                )


def role_tools() -> dict[str, set[str]]:
    """What each role is actually granted, read off its own frontmatter."""
    granted: dict[str, set[str]] = {}
    for path in sorted((PLUGIN_DIR / "agents").glob("*.md")):
        fields, _ = split_frontmatter(path.read_text(), path)
        granted[path.stem] = {
            tool.strip() for tool in fields.get("tools", "").split(",") if tool.strip()
        }
    return granted


ALLOWLIST_STEP = "Resolve the tool allowlist for this role"
RUNTIME_SCRIPTS_GRANT = "Bash(./scripts/*)"


def runtime_allowlist() -> dict[str, set[str]]:
    """What each role is granted inside a run, read off `agent-run.yml`.

    The workflow builds the allowlist in shell, from a `common` prefix, an
    `authoring_pr` fragment, and one `case` branch per role. This reads that
    shell rather than a copy of it, because a copy is the thing that drifts -
    and it reads it as text rather than through a YAML parser so the guard's
    first script keeps needing nothing installed.

    A shape it cannot read is a failure and not a skip. This check exists
    because two lists disagreed silently; a parser that silently returns
    nothing would be the same bug wearing the check's own clothes.
    """
    workflow = ROOT / ".github" / "workflows" / "agent-run.yml"
    if not workflow.exists():
        fail(workflow, "does not exist, so no role's runtime grants can be read")
        return {}

    lines = workflow.read_text().splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if ALLOWLIST_STEP in line)
    except StopIteration:
        fail(
            workflow,
            f"has no step named {ALLOWLIST_STEP!r}. The capability check reads "
            "that step to learn what each role may run; rename it here and in "
            "scripts/validate_plugin.py together, or the check goes quiet "
            "while still reporting",
        )
        return {}

    variables: dict[str, str] = {}
    grants: dict[str, set[str]] = {}
    role: str | None = None
    in_case = False

    def expand(value: str) -> str:
        def one(match: re.Match[str]) -> str:
            name = match.group(1) or match.group(2)
            if name not in variables:
                fail(
                    workflow,
                    f"builds the allowlist from ${name}, which this check "
                    "cannot resolve. Keep the assignment in the same step, or "
                    "teach scripts/validate_plugin.py the new shape",
                )
                return ""
            return variables[name]

        return re.sub(r"\$\{(\w+)\}|\$(\w+)", one, value)

    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("esac"):
            break
        if stripped.startswith('case "$ROLE" in'):
            in_case = True
            continue
        if in_case:
            branch = re.match(r"^([a-z*|]+)\)$", stripped)
            if branch:
                role = branch.group(1)
                # Cleared per branch: every branch opens by assigning `tools`
                # from `$common`, and a branch that started from `$tools`
                # instead would otherwise inherit the role above it.
                variables.pop("tools", None)
                if role != "*":
                    grants.setdefault(role, set())
                continue
            if stripped.startswith(";;"):
                role = None
                continue
        assignment = re.match(r"""^(\w+)=(['"])(.*)\2$""", stripped)
        if not assignment:
            continue
        name, _, raw = assignment.groups()
        value = expand(raw)
        variables[name] = value
        if name == "tools" and role and role != "*":
            grants[role] = {entry for entry in value.split(",") if entry}

    if not grants:
        fail(workflow, "the role allowlist case block read as empty; the check cannot run")
    return grants


def prose_sentences(text: str):
    """Yield the text one flattened sentence at a time."""
    for chunk in SENTENCE_SPLIT.split(COMMENT_PREFIX.sub("", text)):
        yield " ".join(chunk.split())


def denial_pattern(capability: dict) -> str:
    """A sentence saying a subject cannot do this capability.

    The object has to follow the verb, and nothing but a word or two may sit
    between them: that is what makes the match a claim rather than two words
    that happen to share a sentence. Without it "may not edit this file, and
    the first pull request" reads "file" as the verb, and this repository is
    full of the noun. Commas and semicolons are excluded for the same reason -
    they mark the clause boundary the noun reading needs.
    """
    return (
        NEGATION
        + r"[^.,;:]{0,40}?\b"
        + capability["verbs"]
        + r"\b[^.,;:]{0,25}?"
        + capability["object"]
    )


def capability_claim_violations(
    sentence: str, granted: dict[str, set[str]]
) -> list[tuple[str, str, str]]:
    """Which roles a sentence falsely says cannot do something.

    Returns (role, capability name, the tool it holds) for each. Empty when the
    sentence makes no such claim, or makes one that is true.
    """
    found: list[tuple[str, str, str]] = []
    for capability in CAPABILITIES:
        if not re.search(denial_pattern(capability), sentence, re.I):
            continue
        # "no role can open one" is a claim about every role at once and names
        # none of them, so the named-role search would miss it entirely. Not
        # when it is qualified though: "no role can file an issue without the
        # label" is a claim about a condition, and reading it as a capability
        # denial would fail the gate for a sentence that is true. This form is
        # the loose one, so it is the one that gets the guard.
        if re.search(r"\bno\s+role\b", sentence, re.I):
            if re.search(QUALIFIER, sentence, re.I):
                continue
            subjects = sorted(granted)
        else:
            subjects = [
                role
                for role in sorted(granted)
                if re.search(ROLE_MENTION.format(role=role), sentence, re.I)
            ]
        for role in subjects:
            held = sorted(granted[role] & capability["tools"])
            if held:
                found.append((role, capability["name"], held[0]))
    return found


def instruction_violations(body: str, tools: set[str]) -> list[str]:
    """Capabilities the text asks for that none of these tools can perform."""
    return [
        capability["name"]
        for capability in CAPABILITIES
        if re.search(capability["instruction"], body, re.I)
        and not tools & capability["tools"]
    ]


def check_capability_claims() -> None:
    """No file may say a role cannot do something it is granted a tool for.

    This is the failure the check exists for, and it has happened. The
    researcher and the designer were given `create_pull_request` and told to
    open one; the role files and the orchestrator's readiness paragraph were
    updated, and four other places kept the old sentence. One of them was the
    shared block in the project template's CLAUDE.md, so every repository
    provisioned or updated afterwards was handed a false statement about what
    two of its own agents could do - and because `/update-agents` rewrites that
    block, a human correcting it in a project lost the correction on the next
    update.

    Prose is the product here, so prose drifting from frontmatter is a product
    bug rather than a documentation one, and nothing else in this repository
    would have caught it: the mirror check compares two copies of one file and
    both copies were equally wrong.

    The whole repository is in scope. Three of the four survivors were outside
    `plugins/` - comments explaining a workflow trigger, and a docstring - and a
    session that reads one believes it.

    What this does not catch: prose that implies the limit without stating it.
    Those same three comments said the two roles "push a branch and a human
    merges it later", which is not a denial of anything and matches nothing
    here. Separating that from true prose needs judgment, and a check that needs
    judgment is not a gate. This catches the assertion, not the insinuation.
    """
    granted = role_tools()
    for path in sorted(ROOT.rglob("*")):
        relative = str(path.relative_to(ROOT))
        if not path.is_file() or relative.startswith(".git/"):
            continue
        if path.suffix not in PROSE_SUFFIXES or relative in CLAIM_FIXTURES:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for sentence in prose_sentences(text):
            for role, capability, tool in capability_claim_violations(sentence, granted):
                fail(
                    path,
                    f"says the {role} cannot {capability}, but "
                    f"agents/{role}.md grants {tool}. One of the two is wrong: "
                    f"correct the sentence, or drop the tool. "
                    f"Sentence: {sentence[:100]!r}",
                )


def check_roles_can_do_what_they_are_told() -> None:
    """A role told to do something must hold a tool that can do it.

    The other direction of the same drift, and the one that came first: the
    engineer's text argued for opening a pull request before writing code long
    before the researcher and the designer were granted the tool, and their own
    text asked them for a pull request they had no way to open. A run told to do
    something it has no tool for spends one of three attempts finding out.
    """
    granted = role_tools()
    for path in sorted((PLUGIN_DIR / "agents").glob("*.md")):
        _, body = split_frontmatter(path.read_text(), path)
        for capability in instruction_violations(body, granted[path.stem]):
            wanted = " or ".join(
                sorted(
                    tool
                    for entry in CAPABILITIES
                    if entry["name"] == capability
                    for tool in entry["tools"]
                )
            )
            fail(
                path,
                f"tells the {path.stem} to {capability} but grants no tool that "
                f"can: add one of {wanted} to the frontmatter, or stop asking.",
            )


def check_roles_can_run_what_they_are_told() -> None:
    """The same drift one layer down: frontmatter says yes, the run says no.

    `check_roles_can_do_what_they_are_told` reads the `tools:` line in a role
    file. That line is what an interactive session honours and not what gates a
    command inside a workflow run, where `agent-run.yml`'s per-role allowlist
    is what the action enforces. Both lists are hand-maintained and nothing
    compared them until this.

    The gap was reachable with the gate green, and nearly shipped: the designer
    was given `Bash` in frontmatter and four method steps telling it to build a
    page and open it, while its runtime allowlist held `gh` and `git` and
    nothing that runs anything. Every check passed. A run would have read those
    steps, been refused, and - following its role correctly - stopped and
    reported the refusal, having spent one of the issue's three attempts.

    The cheap version of this check does not work, which is why it is written
    against the capability table rather than against the two lists: the
    designer already held scoped `Bash(gh ...)` entries, so "frontmatter says
    Bash, the allowlist has Bash entries" agreed with itself while granting
    nothing that could build anything. The lists are not 1:1 by design -
    frontmatter names tool classes, the allowlist names scoped commands - and
    the table is where the two are allowed to meet, one capability at a time.

    What this deliberately does not do is read a role's prose for loose
    instructions like "run the repo's own checks". Matching English against
    command prefixes is inference, a check that fires on prose it should not is
    worse than no check, and the cure for one is usually deleting it. The
    entries here are matched by literal allowlist string, and the loose end of
    the same problem is handled by naming commands instead: a role told to run
    `./scripts/<thing>` is checked by `check_named_project_commands`, because a
    fixed name is a fact rather than a reading.
    """
    granted = role_tools()
    runtime = runtime_allowlist()
    if not runtime:
        return
    for path in sorted((PLUGIN_DIR / "agents").glob("*.md")):
        role = path.stem
        if role not in runtime:
            fail(
                path,
                "has no branch in agent-run.yml's role allowlist, so a run of "
                "it is refused before it starts. Add the branch, or drop the "
                "role",
            )
            continue
        _, body = split_frontmatter(path.read_text(), path)
        for capability in CAPABILITIES:
            if not re.search(capability["instruction"], body, re.I):
                continue
            if runtime[role] & capability["runtime"]:
                continue
            wanted = " or ".join(sorted(capability["runtime"]))
            fail(
                path,
                f"tells the {role} to {capability['name']}, and "
                f".github/workflows/agent-run.yml grants it nothing that can at "
                f"run time: add {wanted} to the {role} branch of the allowlist, "
                f"or stop asking. Frontmatter is not what gates a run",
            )


def check_gate_inventory() -> None:
    """Every check script is run by the gate and named in both inventories.

    A script nobody runs proves nothing, and an inventory that omits one sends a
    reader looking for a check that is already there. Both have happened:
    `test_project_guard.py` ran in `guard.yml` and appeared in neither
    `CLAUDE.md` nor `docs/what-is-checked.md`, and `docs/what-is-checked.md`
    announced five scripts and listed five while the gate ran seven.

    This is the same drift as a capability claim - prose restating something
    that has a real source - and it gets the same treatment. The counts came out
    of both files, because a count cannot be checked against anything without
    guessing at the sentence around it, and a list of names can.
    """
    workflow = ROOT / ".github" / "workflows" / "guard.yml"
    inventories = [ROOT / "CLAUDE.md", ROOT / "docs" / "what-is-checked.md"]
    if not workflow.exists():
        return
    on_disk = {path.name for path in (ROOT / "scripts").glob("*.py")}
    workflow_text = workflow.read_text()
    run_by_gate = set(re.findall(r"scripts/([a-z_]+\.py)", workflow_text))

    for name in sorted(on_disk - run_by_gate):
        fail(
            ROOT / "scripts" / name,
            "is not run by .github/workflows/guard.yml, so nothing it proves is "
            "enforced: add a step for it, or delete the script.",
        )
    for name in sorted(run_by_gate - on_disk):
        fail(workflow, f"runs scripts/{name}, which does not exist.")

    for inventory in inventories:
        if not inventory.exists():
            continue
        text = inventory.read_text()
        for name in sorted(run_by_gate & on_disk):
            if name not in text:
                fail(
                    inventory,
                    f"does not name scripts/{name}, which guard.yml runs. Every "
                    "check script belongs in this inventory.",
                )


def check_no_stale_marketplace_pin() -> None:
    """Nothing should declare a marketplace to get these commands loaded.

    It reads like it works: the key is valid, the tag resolves, and a trusted
    terminal session does install the plugin. It just does nothing in the one
    place this repository is used from, and it fails silently there, which is
    why it survived two releases.
    """
    for path in [ROOT / ".claude" / "settings.json", PLUGIN_DIR / "templates" / "project" / ".claude" / "settings.json"]:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        for key in ("extraKnownMarketplaces", "enabledPlugins"):
            if key in data:
                fail(
                    path,
                    f"declares {key!r} to load the factory's own commands; that is "
                    "dropped in an untrusted folder and a cloud session never "
                    "trusts one. Vendor the files into .claude/ instead",
                )


def main() -> int:
    check_marketplace()
    check_plugin_manifest()
    check_agents()
    check_skills()
    check_commands()
    check_template_pins()
    check_factory_repo_is_declared()
    check_template_owner_placeholder()
    check_template_placeholders_are_visible()
    check_runbooks_name_every_project_command()
    check_label_vocabulary_is_declared()
    check_vendored_roles()
    check_self_vendored()
    check_no_stale_marketplace_pin()
    check_gate_inventory()
    check_capability_claims()
    check_roles_can_do_what_they_are_told()
    check_roles_can_run_what_they_are_told()
    check_named_project_commands()
    check_template_memory_files()
    check_portability()
    check_no_emoji()
    if errors:
        print(f"guard: {len(errors)} problem(s)\n")
        for error in errors:
            print(f"  {error}")
        return 1
    print("guard: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
