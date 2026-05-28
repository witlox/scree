"""TDD — validates frontmatter parsing + INV-ST-3 (schema_version required)."""

import pytest

from scree.knowledge.frontmatter import InvalidFrontmatter, parse

VALID = """---
id: doc-a
kind: doc
schema_version: 1
title: Alpha
space: platform/handbook
---

# Alpha
body here
"""


def test_parses_valid_frontmatter():
    meta = parse(VALID)
    assert meta["id"] == "doc-a"
    assert meta["schema_version"] == 1
    assert meta["space"] == "platform/handbook"
    assert "Alpha" in meta["body"]


def test_rejects_missing_schema_version():
    # INV-ST-3: every resource carries schema_version.
    text = VALID.replace("schema_version: 1\n", "")
    with pytest.raises(InvalidFrontmatter):
        parse(text)
