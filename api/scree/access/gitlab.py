from typing import Protocol
from urllib.parse import quote

import httpx


class SpaceAuthority(Protocol):
    """Resolves a user's readable GitLab Spaces (projects) and groups from their
    token — the real backing for INV-AGG filtering (replaces the spike stub when
    configured). Resolved ONCE per request (AR-08)."""

    def readable_spaces(self, token: str) -> set[str]: ...

    def readable_groups(self, token: str) -> set[str]: ...


class GitLabAuthority:
    """Coarse authority via GitLab membership (DD-007 / INV-ACC-2). A user can read
    a Space iff they are a member of its GitLab project; a planning group likewise.
    GitLab returns 404 (not 403) for unauthorized private projects — matching our
    existence-leak-safe contract (error-taxonomy: NotFoundOrUnauthorized)."""

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=10)

    def can_read(self, token: str, project: str) -> bool:
        resp = self._client.get(
            f"{self._base}/api/v4/projects/{quote(project, safe='')}",
            headers={"PRIVATE-TOKEN": token},
        )
        return resp.status_code == 200

    def _paginate(self, path: str, token: str, key: str) -> set[str]:
        out: set[str] = set()
        page = 1
        while True:
            resp = self._client.get(
                f"{self._base}{path}",
                headers={"PRIVATE-TOKEN": token},
                params={"membership": "true", "simple": "true", "per_page": 100, "page": page},
            )
            resp.raise_for_status()
            rows = resp.json()
            out.update(r[key] for r in rows if key in r)
            next_page = resp.headers.get("x-next-page")
            if not next_page:
                break
            page = int(next_page)
        return out

    def readable_spaces(self, token: str) -> set[str]:
        # Projects the user is a MEMBER of, by full path (path_with_namespace ==
        # Space id). G9-03 (accepted): Scree Spaces are member-access private
        # projects (INV-ACC-2); visibility-only (public/internal non-member) read is
        # intentionally not a "Space" here. Widen the query if that model changes.
        return self._paginate("/api/v4/projects", token, "path_with_namespace")

    def readable_groups(self, token: str) -> set[str]:
        return self._paginate("/api/v4/groups", token, "full_path")


class FakeGitLabAuthority:
    """In-memory SpaceAuthority for the @api tier: maps a GitLab token to the
    Spaces/groups it can read (faithful stand-in; the @contract tier validates the
    real GitLab membership resolution)."""

    def __init__(
        self,
        spaces: dict[str, set[str]] | None = None,
        groups: dict[str, set[str]] | None = None,
    ) -> None:
        self._spaces = spaces or {}
        self._groups = groups or {}

    def readable_spaces(self, token: str) -> set[str]:
        return set(self._spaces.get(token, set()))

    def readable_groups(self, token: str) -> set[str]:
        return set(self._groups.get(token, set()))
