from typing import Protocol

import httpx


def fga_user(user: str) -> str:
    return f"user:{user}"


def fga_object(ticket_id: str) -> str:
    return f"ticket:{ticket_id}"


def strip_type(obj: str) -> str:
    """`ticket:ticket-1` -> `ticket-1` (OpenFGA typed id -> domain id)."""
    return obj.split(":", 1)[1]


class TicketRelations(Protocol):
    """Read side of ticket ReBAC (OpenFGA in prod, ADR-0007). Models the
    `viewer` relation = requester ∪ watcher ∪ assignee."""

    def list_readable(self, user: str) -> set[str]: ...

    def can_read(self, user: str, ticket_id: str) -> bool: ...

    def write(self, user: str, relation: str, ticket_id: str) -> None: ...

    def purge_user(self, user: str) -> int: ...  # GDPR erasure: drop all tuples for a user (AR-05)


class FakeOpenFga:
    """Faithful in-memory stand-in for OpenFGA's `viewer` relation, used by the
    @api tier. The @contract tier validates the real engine matches this
    contract (assumption A-5)."""

    VIEWER_RELATIONS = frozenset({"requester", "watcher", "assignee"})

    def __init__(self) -> None:
        self._tuples: set[tuple[str, str, str]] = set()

    def write(self, user: str, relation: str, ticket_id: str) -> None:
        self._tuples.add((user, relation, ticket_id))

    def list_readable(self, user: str) -> set[str]:
        return {
            t for (u, r, t) in self._tuples
            if u == user and r in self.VIEWER_RELATIONS
        }

    def can_read(self, user: str, ticket_id: str) -> bool:
        return any(
            u == user and r in self.VIEWER_RELATIONS and t == ticket_id
            for (u, r, t) in self._tuples
        )

    def purge_user(self, user: str) -> int:
        # AR-05: erasure must remove the subject's relation tuples, not just the
        # identity record, or the (now-orphaned) relations linger.
        doomed = {t for t in self._tuples if t[0] == user}
        self._tuples -= doomed
        return len(doomed)


class RealOpenFga:
    """OpenFGA-backed TicketRelations (ADR-0007): ListObjects/Check on the
    `viewer` relation, mapping domain ids to OpenFGA's typed ids."""

    RELATION = "viewer"

    def __init__(self, base_url: str, store_id: str, model_id: str, client: httpx.Client | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._store = store_id
        self._model = model_id
        self._client = client or httpx.Client(timeout=10)

    def list_readable(self, user: str) -> set[str]:
        resp = self._client.post(
            f"{self._base}/stores/{self._store}/list-objects",
            json={
                "authorization_model_id": self._model,
                "type": "ticket",
                "relation": self.RELATION,
                "user": fga_user(user),
            },
        )
        resp.raise_for_status()
        return {strip_type(obj) for obj in resp.json()["objects"]}

    def can_read(self, user: str, ticket_id: str) -> bool:
        resp = self._client.post(
            f"{self._base}/stores/{self._store}/check",
            json={
                "authorization_model_id": self._model,
                "tuple_key": {
                    "user": fga_user(user),
                    "relation": self.RELATION,
                    "object": fga_object(ticket_id),
                },
            },
        )
        resp.raise_for_status()
        return bool(resp.json().get("allowed"))

    def write(self, user: str, relation: str, ticket_id: str) -> None:
        resp = self._client.post(
            f"{self._base}/stores/{self._store}/write",
            json={
                "authorization_model_id": self._model,
                "writes": {"tuple_keys": [
                    {"user": fga_user(user), "relation": relation, "object": fga_object(ticket_id)}
                ]},
            },
        )
        resp.raise_for_status()

    def purge_user(self, user: str) -> int:
        # AR-05: read the subject's stored tuples, then delete them. (Deletes need
        # the exact (user, relation, object), not the derived `viewer` relation.)
        # OpenFGA Read requires an object filter, so scope by the `ticket:` type.
        read = self._client.post(
            f"{self._base}/stores/{self._store}/read",
            json={"tuple_key": {"object": "ticket:", "user": fga_user(user)}},
        )
        read.raise_for_status()
        keys = [t["key"] for t in read.json().get("tuples", [])]
        if not keys:
            return 0
        delete = self._client.post(
            f"{self._base}/stores/{self._store}/write",
            json={"deletes": {"tuple_keys": [
                {"user": k["user"], "relation": k["relation"], "object": k["object"]} for k in keys
            ]}},
        )
        delete.raise_for_status()
        return len(keys)
