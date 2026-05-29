"""@api — storage-invariant depth (real Git):
- G-A8 / INV-ST-4: an id is stable — a write may not rename the doc at an existing path.
- G-A9 / INV-ST-5: created/updated are projections of Git history (created=first commit,
  updated=latest), so an edit advances `updated`.
- G-A10 / INV-ST-6: a stale-base_rev write is surfaced as a Conflict and never silently
  merged — the prior content is preserved."""

import os
import subprocess
from pathlib import Path

import pytest

from scree.access.authority import Authority
from scree.knowledge.doc_service import Conflict, DocService, IdChanged
from scree.knowledge.git_store import GitBackedDocStore

SPACE = "platform/handbook"


def _doc(doc_id: str, *, space: str = SPACE, body: str = "body") -> str:
    return f"---\nid: {doc_id}\nkind: doc\nschema_version: 1\ntitle: T\nspace: {space}\n---\n{body}\n"


def _svc(repo) -> tuple[DocService, GitBackedDocStore]:
    store = GitBackedDocStore(repo)
    svc = DocService(store, Authority({"rivera": {SPACE}}, {"rivera": {SPACE}}))
    return svc, store


def test_id_at_an_existing_path_is_immutable(repo):
    svc, _ = _svc(repo)
    rev1 = svc.write("docs/x.md", _doc("doc-x"), "rivera")["rev"]
    # Rewriting the same path with a different id (a rename) is refused (INV-ST-4).
    with pytest.raises(IdChanged):
        svc.write("docs/x.md", _doc("doc-y"), "rivera", base_rev=rev1)


def test_stale_write_is_surfaced_not_silently_merged(repo):
    svc, store = _svc(repo)
    svc.write("docs/y.md", _doc("doc-z", body="original"), "rivera")
    with pytest.raises(Conflict):
        svc.write("docs/y.md", _doc("doc-z", body="loser"), "rivera", base_rev="deadbeef")
    # The conflict is surfaced; the prior content stands (never silently merged).
    assert store.get("doc-z").body.strip() == "original"
    assert "loser" not in store.get("doc-z").body


def test_timestamps_are_git_projections_and_updated_advances(tmp_path: Path):
    def git(*args, date=None):
        env = {**os.environ}
        if date:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, env=env)

    git("init", "-q")
    git("config", "user.email", "t@scree.test")
    git("config", "user.name", "t")
    p = tmp_path / "docs" / "p.md"
    p.parent.mkdir(parents=True)
    p.write_text(_doc("doc-p", body="v1"))
    git("add", "-A")
    git("commit", "-qm", "create", date="2020-01-01T00:00:00+00:00")
    p.write_text(_doc("doc-p", body="v2"))
    git("add", "-A")
    git("commit", "-qm", "edit", date="2021-06-15T12:00:00+00:00")

    d = GitBackedDocStore(tmp_path).get("doc-p")
    assert d.body.strip() == "v2"  # reflects the edit
    assert d.created.startswith("2020-01-01")  # first commit
    assert d.updated.startswith("2021-06-15")  # latest commit — advanced past created
    assert d.created < d.updated
