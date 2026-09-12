#!/usr/bin/env python3
"""Structural checks for the agent-factory plugin.

Deterministic only. Every failure here names a file and a fix; nothing in this
script requires judgment, because a check that requires judgment is not a gate.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "plugins" / "agent-factory"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"

# The clause every role definition has to end with, verbatim. Agents that do not
# carry it can read the wrong memory file or write where they must not.
REQUIRED_CLAUSE = """Before starting, read `.claude/memory/<your-role>.md` if it exists.
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
    },
    {
        "name": "search the web",
        "tools": {"WebSearch"},
        "object": r"(?:\bthe\s+web\b|\bweb\s+search)",
        "verbs": r"(?:search|searches|searching|query|queries|querying|browse|"
                 r"browses|browsing|look|looks|looking)",
        "instruction": r"\bsearch\s+the\s+web\b",
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
ROLES = ["orchestrator", "researcher", "designer", "engineer"]

# The commands a provisioned project receives. `new-project` is deliberately not
# among them: provisioning is the factory's job, and a project that can
# provision another project is a second factory nobody is maintaining.
PROJECT_COMMANDS = ["objective", "retro", "decompose", "update-agents", "ship"]

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


def check_template_pins() -> None:
    """Every caller a project receives must be pinned through the placeholder.

    A template that hardcodes a ref ships that ref to every repository
    provisioned afterwards, and a moving one puts them all back on a live
    pointer, which is the thing the pinning is for. The placeholder is
    substituted at provision time, so it is the only correct value here.
    """
    templates = PLUGIN_DIR / "templates"
    if not templates.is_dir():
        return
    pattern = re.compile(r"uses:\s*chamaya00/agent-factory/[^@\s]+@(\S+)")
    for path in sorted(templates.rglob("*.yml")) + sorted(templates.rglob("*.yaml")):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            found = pattern.search(line)
            if found and found.group(1) != PIN_PLACEHOLDER:
                fail(
                    path,
                    f"line {number} pins the factory at {found.group(1)!r}; "
                    f"templates must use {PIN_PLACEHOLDER} so provisioning "
                    "substitutes the installed release",
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
    check_vendored_roles()
    check_self_vendored()
    check_no_stale_marketplace_pin()
    check_gate_inventory()
    check_capability_claims()
    check_roles_can_do_what_they_are_told()
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
