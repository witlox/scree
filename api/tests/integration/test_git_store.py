"""Integration — GitBackedDocStore against a real Git repo (DD-002, INV-ST-3/5).
Runs everywhere git is available (incl. CI)."""

from scree.knowledge.git_store import GitBackedDocStore


def test_reads_valid_docs_and_quarantines_invalid(repo):
    ids = {d.id for d in GitBackedDocStore(repo).all()}
    assert ids == {"doc-a", "doc-b"}  # doc-bad (no schema_version) is skipped


def test_timestamps_derived_from_git(repo):
    # INV-ST-5: created/updated are projections of Git history, not authored.
    d = GitBackedDocStore(repo).get("doc-a")
    assert d is not None
    assert d.created is not None
    assert d.updated is not None


def test_body_parsed_from_file(repo):
    d = GitBackedDocStore(repo).get("doc-a")
    assert "Alpha body" in d.body
