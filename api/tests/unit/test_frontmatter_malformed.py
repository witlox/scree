"""I-05 — malformed frontmatter must raise InvalidFrontmatter (→ 422), not a
bare ValueError (→ 500)."""

import pytest

from scree.knowledge.frontmatter import InvalidFrontmatter, parse


def test_missing_closing_delimiter_is_invalid_not_500():
    text = "---\nid: x\nkind: doc\nschema_version: 1\ntitle: t\nspace: s\nno closing fence\n"
    with pytest.raises(InvalidFrontmatter):
        parse(text)
