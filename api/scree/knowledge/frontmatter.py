import yaml


class InvalidFrontmatter(ValueError):
    """Raised when a resource file's YAML frontmatter is missing or invalid."""


# Required core keys (INV-ST-3 / INV-ST-4 / domain-model). Spike: doc kind.
REQUIRED_KEYS = ("id", "kind", "schema_version", "title", "space")


def parse(text: str) -> dict:
    """Parse `---\\nYAML\\n---\\nbody` into a metadata dict with a `body` key.

    Full schema in specs/frontmatter-schemas.
    """
    if not text.startswith("---"):
        raise InvalidFrontmatter("missing frontmatter")
    _, raw_meta, body = text.split("---", 2)
    meta = yaml.safe_load(raw_meta) or {}
    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        raise InvalidFrontmatter(f"missing required keys: {missing}")
    meta["body"] = body.lstrip("\n")
    return meta
