"""TDD — governed (MR-required) path detection (INV-GOV-1)."""

from scree.knowledge.doc_service import is_governed

GOVERNED = {"policy/", "hr/"}


def test_governed_prefixes_match():
    assert is_governed("policy/security.md", GOVERNED) is True
    assert is_governed("hr/handbook.md", GOVERNED) is True


def test_non_governed_paths():
    assert is_governed("docs/onboarding.md", GOVERNED) is False
    assert is_governed("policies-faq.md", GOVERNED) is False
