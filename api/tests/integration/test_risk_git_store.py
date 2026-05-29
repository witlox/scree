"""@api — risks persisted to Git (#79 / INV-ST-1): a created risk is a commit and is
rebuildable from Git (INV-ST-2). Replaces the in-memory-only risk persistence so the
storage invariants are actually exercised for risks, not just docs."""

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.risk.git_store import GitBackedRiskStore
from scree.risk.models import Risk

SPACE = "org/risk-portfolio"
U = "owner-1"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for args in (["init", "-q"], ["config", "user.email", "t@scree.test"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    return tmp_path


def _commits(repo: Path) -> int:
    out = subprocess.run(["git", "-C", str(repo), "rev-list", "--count", "--all"],
                         capture_output=True, text=True).stdout.strip()
    return int(out or "0")


def test_put_commits_and_is_rebuildable_from_git(repo):
    store = GitBackedRiskStore(repo)
    store.put(Risk(id="risk-1", title="Vendor lock-in", space=SPACE, category="strategic",
                   likelihood=4, impact=4, strategy="mitigated", owner=U))
    assert _commits(repo) == 1  # INV-ST-1: the mutation is a commit

    # A fresh store instance reads it back from Git alone (INV-ST-2).
    fresh = GitBackedRiskStore(repo)
    r = fresh.get("risk-1")
    assert r is not None
    assert r.title == "Vendor lock-in" and r.likelihood == 4 and r.impact == 4
    assert r.score == 16 and r.severity == "critical"  # derived, not stored
    assert r.owner == U


def test_create_via_gateway_persists_and_lists(repo):
    authority = Authority({U: {SPACE}}, {U: {SPACE}})
    client = TestClient(create_app(DocStore([]), authority, risk_store=GitBackedRiskStore(repo),
                                   allow_insecure_header_auth=True))
    created = client.post(
        "/risks",
        json={"title": "Migration slip", "space": SPACE, "category": "delivery", "likelihood": 3, "impact": 3, "strategy": "owned"},
        headers={"X-Spike-User": U},
    )
    assert created.status_code == 200
    assert _commits(repo) == 1  # the POST committed to Git

    listed = client.get("/risks", headers={"X-Spike-User": U}).json()
    assert created.json()["id"] in {r["id"] for r in listed}


def test_malformed_risk_file_is_quarantined(repo):
    # A file missing required risk fields must be skipped, never surfaced.
    (repo / "risks").mkdir()
    (repo / "risks" / "bad.md").write_text("---\nid: x\nkind: risk\nschema_version: 1\ntitle: t\nspace: s\n---\n")
    assert GitBackedRiskStore(repo).all() == []  # no category/likelihood/impact/strategy → quarantined
