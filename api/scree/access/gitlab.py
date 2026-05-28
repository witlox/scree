from urllib.parse import quote

import httpx


class GitLabAuthority:
    """Coarse authority via GitLab project read access (DD-007 / INV-ACC-2).

    A principal can read a Space iff they can GET its GitLab project. GitLab
    returns 404 (not 403) when unauthorized to a private project — which matches
    our existence-leak-safe contract (error-taxonomy: NotFoundOrUnauthorized).
    """

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=10)

    def can_read(self, token: str, project: str) -> bool:
        resp = self._client.get(
            f"{self._base}/api/v4/projects/{quote(project, safe='')}",
            headers={"PRIVATE-TOKEN": token},
        )
        # Authorized iff GitLab returns the project (200). 404/403 => denied.
        return resp.status_code == 200
