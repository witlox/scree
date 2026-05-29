"""@contract — G-B3: GitLabAuthority.readable_spaces against a REAL GitLab CE, across a
PAGE BOUNDARY. The existing @contract only covers can_read; readable_spaces (the
x-next-page pagination that actually backs INV-AGG) was never run against real GitLab.
Driven by GITLAB_TEST_URL + GITLAB_TEST_TOKEN (admin PAT); skips otherwise."""

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
def member_of_two():
    admin = httpx.Client(
        base_url=GITLAB_URL.rstrip("/") + "/api/v4",
        headers={"PRIVATE-TOKEN": GITLAB_ADMIN_TOKEN},
        timeout=30,
    )
    suffix = uuid.uuid4().hex[:8]
    user = admin.post("/users", json={
        "email": f"p{suffix}@scree.test", "username": f"p{suffix}", "name": f"P {suffix}",
        "password": "Sup3r-Secret-Pw!", "skip_confirmation": True,
    })
    user.raise_for_status()
    user_id = user.json()["id"]
    tok = admin.post(f"/users/{user_id}/personal_access_tokens", json={"name": "t", "scopes": ["api"]})
    tok.raise_for_status()
    user_token = tok.json()["token"]

    member_paths = set()
    for i in range(2):  # two member projects → two pages at per_page=1
        proj = admin.post("/projects", json={"name": f"mem-{suffix}-{i}", "visibility": "private"})
        proj.raise_for_status()
        admin.post(f"/projects/{proj.json()['id']}/members",
                   json={"user_id": user_id, "access_level": 20}).raise_for_status()
        member_paths.add(proj.json()["path_with_namespace"])
    # A project the user is NOT a member of must never appear.
    other = admin.post("/projects", json={"name": f"other-{suffix}", "visibility": "private"})
    other.raise_for_status()
    other_path = other.json()["path_with_namespace"]

    yield {"user_token": user_token, "member_paths": member_paths, "other_path": other_path}
    admin.close()


def test_readable_spaces_follows_pagination_and_excludes_non_member(member_of_two):
    # per_page=1 forces an x-next-page boundary with only two member projects.
    authority = GitLabAuthority(GITLAB_URL, per_page=1)
    spaces = authority.readable_spaces(member_of_two["user_token"])
    assert member_of_two["member_paths"] <= spaces  # both pages fetched
    assert member_of_two["other_path"] not in spaces  # non-member excluded (INV-AGG)
