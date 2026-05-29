"""Shared wiring for the @api BDD tier.

The step modules in this directory bind the canonical `specs/features/*.feature`
files (via `bdd_features_base_dir`, set in pyproject). Each scenario's tags become
pytest markers; `@contract` and `@e2e` scenarios are skipped here — they belong to
the testcontainers contract tier and the Playwright browser tier — so the @api run
stays in-process while still *collecting* every canonical scenario for traceability.
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest

# @contract scenarios run against real disposable services (testcontainers). When
# testcontainers isn't installed — the fast `api-tests` job — they skip; the
# `contract-tests` job installs it (and has Docker), so they execute there.
_HAS_TESTCONTAINERS = importlib.util.find_spec("testcontainers") is not None


def pytest_bdd_apply_tag(tag, function):
    # @api/@security stay as normal pytest markers (handled by pytest-bdd's default).
    if tag == "e2e":
        pytest.mark.skip(reason="@e2e: exercised by the web Playwright harness, not the BDD run")(function)
        return True
    if tag == "contract" and not _HAS_TESTCONTAINERS:
        pytest.mark.skip(reason="@contract: needs testcontainers (runs in the contract-tests job)")(function)
        return True
    return None


@pytest.fixture
def git_repo(tmp_path: Path):
    """A factory for initialized Git working trees backing the doc/risk stores —
    so the doc/risk BDD scenarios exercise real persistence (INV-ST-1/2), not an
    in-memory stand-in."""

    def _make(name: str = "repo") -> Path:
        root = tmp_path / name
        root.mkdir()
        for args in (["init", "-q"], ["config", "user.email", "bdd@scree.test"], ["config", "user.name", "bdd"]):
            subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
        return root

    return _make


@pytest.fixture
def commit_doc():
    """Seed a doc as markdown + frontmatter and commit it (mirrors GitBackedDocStore's
    on-disk shape) so a GitBackedDocStore reads it back."""

    def _commit(root: Path, rel: str, *, doc_id: str, title: str, space: str, body: str = "body") -> None:
        content = f"---\nid: {doc_id}\nkind: doc\nschema_version: 1\ntitle: {title}\nspace: {space}\n---\n{body}\n"
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=seed", "-c", "user.email=seed@scree", "commit", "-qm", f"seed {doc_id}"],
            check=True, capture_output=True,
        )

    return _commit
