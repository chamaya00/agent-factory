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

# What a template writes instead of a release tag. Provisioning substitutes it.
PIN_PLACEHOLDER = "__FACTORY_VERSION__"
ROLES = ["orchestrator", "researcher", "designer", "engineer"]

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


def main() -> int:
    check_marketplace()
    check_plugin_manifest()
    check_agents()
    check_skills()
    check_commands()
    check_template_pins()
    check_vendored_roles()
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
