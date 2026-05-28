"""Integration — a Space (repo) is a folder tree: folder path = page hierarchy,
and per-folder uploads are the colocated non-.md files (DD-002 attachments)."""

from scree.knowledge.git_store import GitBackedDocStore


def test_nested_docs_and_hierarchy(tree_repo):
    store = GitBackedDocStore(tree_repo)
    by_id = {d.id: d for d in store.all()}
    # Both the top page and the nested page are docs; the .png is not.
    assert set(by_id) == {"doc-onboarding", "doc-deep"}
    # Folder path carries the hierarchy.
    assert by_id["doc-onboarding"].path == "onboarding/index.md"
    assert by_id["doc-deep"].path == "onboarding/sub/deep.md"


def test_per_folder_attachments_exclude_docs(tree_repo):
    store = GitBackedDocStore(tree_repo)
    attachments = store.attachments("doc-onboarding")
    assert attachments == ["onboarding/diagram.png"]  # only the upload, not index.md


def test_attachments_empty_for_unknown_doc(tree_repo):
    assert GitBackedDocStore(tree_repo).attachments("doc-missing") == []
