import yaml


class InvalidFrontmatter(ValueError):
    """Raised when a resource file's YAML frontmatter is missing or invalid."""


# Required core keys (INV-ST-3 / INV-ST-4 / domain-model). Spike: doc kind.
REQUIRED_KEYS = ("id", "kind", "schema_version", "title", "space")

# G2-07: bound external input. Frontmatter is small by nature; the body cap is a
# coarse guard against unbounded uploads (real limits live at the gateway/storage).
MAX_CONTENT_BYTES = 1_000_000
MAX_FRONTMATTER_BYTES = 64 * 1024


class _NoAliasLoader(yaml.SafeLoader):
    """SafeLoader that refuses YAML anchors/aliases — defeats alias-expansion
    ("billion laughs") DoS, which SafeLoader otherwise resolves (G2-07)."""

    def compose_node(self, parent, index):
        if self.check_event(yaml.events.AliasEvent):
            raise InvalidFrontmatter("YAML aliases are not allowed in frontmatter")
        return super().compose_node(parent, index)


def parse(text: str) -> dict:
    """Parse `---\\nYAML\\n---\\nbody` into a metadata dict with a `body` key.

    Full schema in specs/frontmatter-schemas.
    """
    if len(text.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise InvalidFrontmatter("content exceeds maximum size")
    if not text.startswith("---"):
        raise InvalidFrontmatter("missing frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise InvalidFrontmatter("malformed frontmatter (missing closing ---)")
    _, raw_meta, body = parts
    if len(raw_meta.encode("utf-8")) > MAX_FRONTMATTER_BYTES:
        raise InvalidFrontmatter("frontmatter exceeds maximum size")
    try:
        meta = yaml.load(raw_meta, Loader=_NoAliasLoader) or {}
    except yaml.YAMLError as exc:
        raise InvalidFrontmatter(f"unparseable frontmatter: {exc}") from exc
    if not isinstance(meta, dict):
        raise InvalidFrontmatter("frontmatter must be a mapping")
    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        raise InvalidFrontmatter(f"missing required keys: {missing}")
    meta["body"] = body.lstrip("\n")
    return meta
