from fastapi import Body, Depends, FastAPI, Header, HTTPException

from scree.access.authority import Authority
from scree.access.oidc import AuthError, OidcAuthenticator
from scree.access.ticket_authority import TicketAuthority
from scree.knowledge.doc_service import Conflict, DocService, DuplicateId, MRRequired, WrongKind
from scree.knowledge.doc_service import Forbidden as DocForbidden
from scree.knowledge.frontmatter import InvalidFrontmatter
from scree.knowledge.store import DocStore
from scree.risk.models import Risk
from scree.risk.triggers import fires_critical_webhook
from scree.servicedesk.lifecycle import IllegalTransition
from scree.servicedesk.service import (
    Forbidden,
    NotPromotable,
    TicketNotFound,
    TicketService,
)
from scree.servicedesk.store import TicketStore


def create_app(
    store: DocStore,
    authority: Authority,
    *,
    ticket_store: TicketStore | None = None,
    ticket_authority: TicketAuthority | None = None,
    doc_writer: DocService | None = None,
    authenticator: OidcAuthenticator | None = None,
) -> FastAPI:
    """The single enforcement point. Identity comes from a verified OIDC bearer
    token (INV-ID-1) when an authenticator is configured; otherwise it falls back
    to the X-Spike-User header (spike/dev only)."""
    # docs_url/redoc_url disabled: "/docs" is a Scree resource path, not Swagger UI.
    app = FastAPI(docs_url=None, redoc_url=None)

    def get_principal(
        authorization: str | None = Header(default=None),
        x_spike_user: str | None = Header(default=None),
    ) -> str:
        if authenticator is not None:
            if not authorization or not authorization.lower().startswith("bearer "):
                raise HTTPException(status_code=401, detail="missing bearer token")
            try:
                return authenticator.principal(authorization.split(" ", 1)[1])
            except AuthError:
                raise HTTPException(status_code=401, detail="invalid token")
        if x_spike_user:
            return x_spike_user  # spike/dev fallback when no authenticator configured
        raise HTTPException(status_code=401, detail="no identity")

    @app.post("/risks/assess")
    def assess_risk(
        category: str = Body(..., embed=True),
        likelihood: int = Body(..., embed=True),
        impact: int = Body(..., embed=True),
    ) -> dict:
        # Stateless preview of derived score/severity + whether it fires the
        # critical webhook (INV-IX-1). Persistence reuses the doc-write path.
        risk = Risk(
            id="(preview)", title="", space="", category=category,
            likelihood=likelihood, impact=impact, strategy="mitigated",
        )
        return {
            "score": risk.score,
            "severity": risk.severity,
            "fires_critical_webhook": fires_critical_webhook(risk),
        }

    @app.get("/docs")
    def list_docs(principal: str = Depends(get_principal)) -> list[dict]:
        # INV-AGG: filter EVERY item by the requester's authority, per request.
        return [
            {"id": d.id, "title": d.title, "space": d.space}
            for d in store.all()
            if authority.can_read(principal, d)
        ]

    @app.get("/docs/{doc_id}")
    def get_doc(doc_id: str, principal: str = Depends(get_principal)) -> dict:
        d = store.get(doc_id)
        # Existence-leak-safe: 404 for absent OR unreadable (error-taxonomy).
        if d is None or not authority.can_read(principal, d):
            raise HTTPException(status_code=404)
        return {"id": d.id, "title": d.title, "space": d.space, "body": d.body}

    if doc_writer is not None:

        @app.post("/docs")
        def write_doc(
            path: str = Body(..., embed=True),
            content: str = Body(..., embed=True),
            base_rev: str | None = Body(default=None, embed=True),
            principal: str = Depends(get_principal),
        ) -> dict:
            try:
                return doc_writer.write(path, content, principal, base_rev)
            except (InvalidFrontmatter, WrongKind):
                raise HTTPException(status_code=422, detail="invalid document")
            except DocForbidden:
                raise HTTPException(status_code=403)
            except MRRequired:
                raise HTTPException(status_code=409, detail="MR required (governed path)")
            except DuplicateId:
                raise HTTPException(status_code=409, detail="id already in use")
            except Conflict:
                raise HTTPException(status_code=409, detail="stale base revision")

    if ticket_store is not None and ticket_authority is not None:

        @app.get("/tickets")
        def list_tickets(principal: str = Depends(get_principal)) -> list[dict]:
            # INV-AGG/ACC: relations ∪ desk membership ∪ community_visible.
            tickets = ticket_store.all()
            readable = ticket_authority.readable_tickets(principal, tickets)
            return [{"id": t.id, "requester": t.requester} for t in tickets if t.id in readable]

        @app.get("/tickets/{ticket_id}")
        def get_ticket(ticket_id: str, principal: str = Depends(get_principal)) -> dict:
            t = ticket_store.get(ticket_id)
            if t is None or not ticket_authority.can_read(principal, t):
                raise HTTPException(status_code=404)
            return {"id": t.id, "requester": t.requester, "status": t.status,
                    "community_visible": t.community_visible}

        service = TicketService(ticket_store, ticket_authority)

        @app.post("/tickets")
        def create_ticket(
            origin: str = Body(..., embed=True),
            requester: str = Body(..., embed=True),
            principal: str = Depends(get_principal),
        ) -> dict:
            t = service.create(origin, requester)
            return {"id": t.id, "requester": t.requester, "origin": t.origin,
                    "status": t.status, "community_visible": t.community_visible}

        @app.patch("/tickets/{ticket_id}")
        def transition_ticket(
            ticket_id: str,
            status: str = Body(..., embed=True),
            principal: str = Depends(get_principal),
        ) -> dict:
            try:
                t = service.transition(ticket_id, status, principal)
            except TicketNotFound:
                raise HTTPException(status_code=404)
            except Forbidden:
                raise HTTPException(status_code=403)
            except IllegalTransition:
                raise HTTPException(status_code=409, detail="illegal transition")
            return {"id": t.id, "status": t.status, "community_visible": t.community_visible}

        @app.post("/tickets/{ticket_id}/community-visible")
        def promote(ticket_id: str, principal: str = Depends(get_principal)) -> dict:
            try:
                t = service.promote_community_visible(ticket_id, principal)
            except TicketNotFound:
                raise HTTPException(status_code=404)
            except Forbidden:
                raise HTTPException(status_code=403)
            except NotPromotable:
                raise HTTPException(status_code=409, detail="only resolved tickets")
            return {"id": t.id, "community_visible": t.community_visible}

    return app
