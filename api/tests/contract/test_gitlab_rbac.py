"""@contract — GitLabAuthority against a REAL GitLab CE.

Validates coarse authority (DD-007): a non-member cannot read a private project
(GitLab returns 404 — existence-leak-safe), a member can. Driven by a running
GitLab provided via env (GITLAB_TEST_URL + GITLAB_TEST_TOKEN = admin PAT);
skips otherwise so CI stays green."""

import os
import uuid

import httpx
import pytest

from scree.access.gitlab import GitLabAuthority

GITLAB_URL = os.environ.get("GITLAB_TEST_URL")
GITLAB_ADMIN_TOKEN = os.environ.get("GITLAB_TEST_TOKEN")

pytestmark = [
    pytest.mark.contract,
    pytest.mark.skipif(
        not (GITLAB_URL and GITLAB_ADMIN_TOKEN),
        reason="GITLAB_TEST_URL / GITLAB_TEST_TOKEN not set",
    ),
]


@pytest.fixture(scope="module")
def gitlab():
    admin = httpx.Client(
        base_url=GITLAB_URL.rstrip("/") + "/api/v4",
        headers={"PRIVATE-TOKEN": GITLAB_ADMIN_TOKEN},
        timeout=30,
    )
    suffix = uuid.uuid4().hex[:8]

    project = admin.post("/projects", json={"name": f"private-{suffix}", "visibility": "private"})
    project.raise_for_status()
    project_id = str(project.json()["id"])

    user = admin.post(
        "/users",
        json={
            "email": f"u{suffix}@scree.test",
            "username": f"u{suffix}",
            "name": f"User {suffix}",
            "password": "Sup3r-Secret-Pw!",
            "skip_confirmation": True,
        },
    )
    user.raise_for_status()
    user_id = user.json()["id"]

    tok = admin.post(f"/users/{user_id}/personal_access_tokens", json={"name": "t", "scopes": ["api"]})
    tok.raise_for_status()
    user_token = tok.json()["token"]

    yield {"project_id": project_id, "user_id": user_id, "user_token": user_token, "admin": admin}
    admin.close()


def test_non_member_cannot_read_private_project_then_member_can(gitlab):
    authority = GitLabAuthority(GITLAB_URL)

    # Non-member → GitLab 404 → must be denied (existence-leak-safe).
    assert authority.can_read(gitlab["user_token"], gitlab["project_id"]) is False
    # Admin token → allowed.
    assert authority.can_read(GITLAB_ADMIN_TOKEN, gitlab["project_id"]) is True

    # Grant membership, then the same user can read.
    add = gitlab["admin"].post(
        f"/projects/{gitlab['project_id']}/members",
        json={"user_id": gitlab["user_id"], "access_level": 20},
    )
    add.raise_for_status()
    assert authority.can_read(gitlab["user_token"], gitlab["project_id"]) is True
