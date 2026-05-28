import uuid

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from scree.access.audit import AuditSink
from scree.access.authority import Authority
from scree.access.oidc import AuthError, OidcAuthenticator
from scree.access.ticket_authority import TicketAuthority
from scree.knowledge.doc_service import (
    Conflict,
    DocService,
    DuplicateId,
    InvalidPath,
    MRRequired,
    SpaceMismatch,
    WrongKind,
)
from scree.knowledge.doc_service import Forbidden as DocForbidden
from scree.knowledge.frontmatter import InvalidFrontmatter
from scree.knowledge.git_store import GitWriteError
from scree.knowledge.store import DocStore
from scree.risk.models import Risk
from scree.risk.store import RiskStore
from scree.risk.triggers import fires_critical_webhook
from scree.servicedesk.lifecycle import IllegalTransition
from scree.servicedesk.service import Forbidden, NotPromotable, TicketNotFound, TicketService
from scree.servicedesk.store import TicketStore

# Central error taxonomy: domain exception -> HTTP status (error-taxonomy.md, I-10).
_ERROR_STATUS: dict[type[Exception], int] = {
    InvalidFrontmatter: 422,
    WrongKind: 422,
    InvalidPath: 422,
    DocForbidden: 403,
    SpaceMismatch: 403,
    Forbidden: 403,
    MRRequired: 409,
    DuplicateId: 409,
    Conflict: 409,
    GitWriteError: 409,
    IllegalTransition: 409,
    NotPromotable: 409,
    TicketNotFound: 404,
}


def _make_handler(status: int):
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status, content={"detail": type(exc).__name__})
    return handler


def create_app(
    store: DocStore,
    authority: Authority,
    *,
    ticket_store: TicketStore | None = None,
    ticket_authority: TicketAuthority | None = None,
    doc_writer: DocService | None = None,
    authenticator: OidcAuthenticator | None = None,
    risk_store: RiskStore | None = None,
    audit: AuditSink | None = None,
) -> FastAPI:
    """The single enforcement point. Identity comes from a verified OIDC bearer
    token (INV-ID-1) when an authenticator is configured; otherwise it falls back
    to the X-Spike-User header (spike/dev only). Domain exceptions map to HTTP via
    central handlers; every action is audited (INV-ID-3)."""
    # docs_url/redoc_url disabled: "/docs" is a Scree resource path, not Swagger UI.
    app = FastAPI(docs_url=None, redoc_url=None)

    for exc_type, status in _ERROR_STATUS.items():
        app.add_exception_handler(exc_type, _make_handler(status))

    if audit is not None:
        @app.middleware("http")
        async def audit_mw(request: Request, call_next):
            response = await call_next(request)
            audit.record(
                getattr(request.state, "principal", None),
                request.method, request.url.path, response.status_code,
            )
            return response

    def get_principal(
        request: Request,
        authorization: str | None = Header(default=None),
        x_spike_user: str | None = Header(default=None),
    ) -> str:
        if authenticator is not None:
            if not authorization or not authorization.lower().startswith("bearer "):
                raise HTTPException(status_code=401, detail="missing bearer token")
            try:
                principal = authenticator.principal(authorization.split(" ", 1)[1])
            except AuthError:
                raise HTTPException(status_code=401, detail="invalid token")
        elif x_spike_user:
            principal = x_spike_user  # spike/dev fallback when no authenticator
        else:
            raise HTTPException(status_code=401, detail="no identity")
        request.state.principal = principal  # I-08: record for the audit sink
        return principal

    @app.post("/risks/assess")
    def assess_risk(
        category: str = Body(..., embed=True),
        likelihood: int = Body(..., embed=True),
        impact: int = Body(..., embed=True),
    ) -> dict:
        risk = Risk(id="(preview)", title="", space="", category=category,
                    likelihood=likelihood, impact=impact, strategy="mitigated")
        return {"score": risk.score, "severity": risk.severity,
                "fires_critical_webhook": fires_critical_webhook(risk)}

    if risk_store is not None:

        def _risk_view(r: Risk) -> dict:
            return {"id": r.id, "title": r.title, "space": r.space, "category": r.category,
                    "score": r.score, "severity": r.severity,
                    "fires_critical_webhook": fires_critical_webhook(r)}

        @app.post("/risks")
        def create_risk(
            title: str = Body(..., embed=True),
            space: str = Body(..., embed=True),
            category: str = Body(..., embed=True),
            likelihood: int = Body(..., embed=True),
            impact: int = Body(..., embed=True),
            strategy: str = Body("mitigated", embed=True),
            principal: str = Depends(get_principal),
        ) -> dict:
            if not authority.can_write(principal, space):
                raise HTTPException(status_code=403)
            risk = Risk(id=f"risk-{uuid.uuid4().hex[:8]}", title=title, space=space,
                        category=category, likelihood=likelihood, impact=impact, strategy=strategy)
            risk_store.put(risk)
            return _risk_view(risk)

        @app.get("/risks")
        def list_risks(principal: str = Depends(get_principal)) -> list[dict]:
            readable = authority.readable_spaces(principal)  # INV-AGG over risks
            return [_risk_view(r) for r in risk_store.all() if r.space in readable]

    @app.get("/docs")
    def list_docs(principal: str = Depends(get_principal)) -> list[dict]:
        # INV-AGG: filter EVERY item by the requester's authority, per request.
        return [{"id": d.id, "title": d.title, "space": d.space}
                for d in store.all() if authority.can_read(principal, d)]

    @app.get("/docs/{doc_id}")
    def get_doc(doc_id: str, principal: str = Depends(get_principal)) -> dict:
        d = store.get(doc_id)
        if d is None or not authority.can_read(principal, d):
            raise HTTPException(status_code=404)  # existence-leak-safe
        return {"id": d.id, "title": d.title, "space": d.space, "body": d.body}

    if doc_writer is not None:

        @app.post("/docs")
        def write_doc(
            path: str = Body(..., embed=True),
            content: str = Body(..., embed=True),
            base_rev: str | None = Body(default=None, embed=True),
            principal: str = Depends(get_principal),
        ) -> dict:
            return doc_writer.write(path, content, principal, base_rev)

    if ticket_store is not None and ticket_authority is not None:
        service = TicketService(ticket_store, ticket_authority)

        @app.get("/tickets")
        def list_tickets(principal: str = Depends(get_principal)) -> list[dict]:
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
            t = service.transition(ticket_id, status, principal)
            return {"id": t.id, "status": t.status, "community_visible": t.community_visible}

        @app.post("/tickets/{ticket_id}/community-visible")
        def promote(ticket_id: str, principal: str = Depends(get_principal)) -> dict:
            t = service.promote_community_visible(ticket_id, principal)
            return {"id": t.id, "community_visible": t.community_visible}

    return app
