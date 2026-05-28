from fastapi import FastAPI, Header, HTTPException

from scree.access.authority import Authority
from scree.access.ticket_authority import TicketAuthority
from scree.knowledge.store import DocStore
from scree.servicedesk.store import TicketStore


def create_app(
    store: DocStore,
    authority: Authority,
    *,
    ticket_store: TicketStore | None = None,
    ticket_authority: TicketAuthority | None = None,
) -> FastAPI:
    """The single enforcement point (spike). Identity is a stub header
    (X-Spike-User) — real OIDC/token-exchange comes later."""
    # docs_url/redoc_url disabled: "/docs" is a Scree resource path, not Swagger UI.
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.get("/docs")
    def list_docs(x_spike_user: str = Header(...)) -> list[dict]:
        # INV-AGG: filter EVERY item by the requester's authority, per request.
        return [
            {"id": d.id, "title": d.title, "space": d.space}
            for d in store.all()
            if authority.can_read(x_spike_user, d)
        ]

    @app.get("/docs/{doc_id}")
    def get_doc(doc_id: str, x_spike_user: str = Header(...)) -> dict:
        d = store.get(doc_id)
        # Existence-leak-safe: 404 for absent OR unreadable (error-taxonomy).
        if d is None or not authority.can_read(x_spike_user, d):
            raise HTTPException(status_code=404)
        return {"id": d.id, "title": d.title, "space": d.space, "body": d.body}

    if ticket_store is not None and ticket_authority is not None:

        @app.get("/tickets")
        def list_tickets(x_spike_user: str = Header(...)) -> list[dict]:
            # INV-AGG for tickets: union of OpenFGA relations and desk membership.
            all_ids = {t.id for t in ticket_store.all()}
            readable = ticket_authority.readable_tickets(x_spike_user, all_ids)
            return [
                {"id": t.id, "requester": t.requester}
                for t in ticket_store.all()
                if t.id in readable
            ]

        @app.get("/tickets/{ticket_id}")
        def get_ticket(ticket_id: str, x_spike_user: str = Header(...)) -> dict:
            t = ticket_store.get(ticket_id)
            if t is None or not ticket_authority.can_read(x_spike_user, ticket_id):
                raise HTTPException(status_code=404)
            return {"id": t.id, "requester": t.requester}

    return app
