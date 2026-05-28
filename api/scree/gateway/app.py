import uuid

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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
from scree.planning.authority import PlanningAuthority
from scree.planning.index import PlanningIndex
from scree.planning.rollup import portfolio
from scree.risk.models import Risk, RiskCategory, Strategy
from scree.risk.store import RiskStore
from scree.risk.triggers import fires_critical_webhook
from scree.servicedesk.lifecycle import IllegalTransition
from scree.servicedesk.models import Origin
from scree.servicedesk.service import Forbidden, NotPromotable, TicketNotFound, TicketService
from scree.servicedesk.store import TicketStore


# G2-09: validate every external input at the boundary (422 on bad enum/range).
class RiskAssessIn(BaseModel):
    category: RiskCategory
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)


class RiskCreateIn(RiskAssessIn):
    title: str = Field(min_length=1)
    space: str = Field(min_length=1)
    strategy: Strategy = "mitigated"


class TicketCreateIn(BaseModel):
    origin: Origin
    requester: str | None = None


class TicketTransitionIn(BaseModel):
    status: str

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
    planning_index: PlanningIndex | None = None,
    planning_authority: PlanningAuthority | None = None,
    audit: AuditSink | None = None,
    allow_insecure_header_auth: bool = False,
) -> FastAPI:
    """The single enforcement point. Identity comes from a verified OIDC bearer
    token (INV-ID-1). Domain exceptions map to HTTP via central handlers; every
    action is audited (INV-ID-3).

    G2-03: fail closed. Without an authenticator the app refuses to start unless
    `allow_insecure_header_auth=True` is passed explicitly (spike/dev only), which
    enables the unauthenticated X-Spike-User header path."""
    if authenticator is None and not allow_insecure_header_auth:
        raise ValueError(
            "create_app requires an authenticator; pass allow_insecure_header_auth=True "
            "only for dev/spike (trusts the X-Spike-User header)."
        )
    # G3-03: planning needs both an index and an authority — refuse partial config
    # rather than silently 404-ing the route.
    if (planning_index is None) != (planning_authority is None):
        raise ValueError("planning requires both planning_index and planning_authority")
    # docs_url/redoc_url disabled: "/docs" is a Scree resource path, not Swagger UI.
    app = FastAPI(docs_url=None, redoc_url=None)

    for exc_type, status in _ERROR_STATUS.items():
        app.add_exception_handler(exc_type, _make_handler(status))

    if audit is not None:
        @app.middleware("http")
        async def audit_mw(request: Request, call_next):
            # G2-08: record in finally so 5xx (unhandled exceptions) are audited too.
            status_code = 500
            try:
                response = await call_next(request)
                status_code = response.status_code
                return response
            finally:
                audit.record(
                    getattr(request.state, "principal", None),
                    request.method, request.url.path, status_code,
                )

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
        elif allow_insecure_header_auth and x_spike_user:
            principal = x_spike_user  # spike/dev only (gated by allow_insecure_header_auth)
        else:
            raise HTTPException(status_code=401, detail="no identity")
        request.state.principal = principal  # I-08: record for the audit sink
        return principal

    @app.post("/risks/assess")
    def assess_risk(
        body: RiskAssessIn,
        principal: str = Depends(get_principal),  # G2-10: authenticated like every action
    ) -> dict:
        risk = Risk(id="(preview)", title="", space="", category=body.category,
                    likelihood=body.likelihood, impact=body.impact, strategy="mitigated")
        return {"score": risk.score, "severity": risk.severity,
                "fires_critical_webhook": fires_critical_webhook(risk)}

    if risk_store is not None:

        def _risk_view(r: Risk) -> dict:
            return {"id": r.id, "title": r.title, "space": r.space, "category": r.category,
                    "score": r.score, "severity": r.severity,
                    "fires_critical_webhook": fires_critical_webhook(r)}

        @app.post("/risks")
        def create_risk(
            body: RiskCreateIn,
            principal: str = Depends(get_principal),
        ) -> dict:
            if not authority.can_write(principal, body.space):
                raise HTTPException(status_code=403)
            risk = Risk(id=f"risk-{uuid.uuid4().hex[:8]}", title=body.title, space=body.space,
                        category=body.category, likelihood=body.likelihood,
                        impact=body.impact, strategy=body.strategy)
            risk_store.put(risk)
            return _risk_view(risk)

        @app.get("/risks")
        def list_risks(principal: str = Depends(get_principal)) -> list[dict]:
            readable = authority.readable_spaces(principal)  # INV-AGG over risks
            return [_risk_view(r) for r in risk_store.all() if r.space in readable]

    if planning_index is not None and planning_authority is not None:

        @app.get("/planning/portfolio")
        def portfolio_rollup(
            principal: str = Depends(get_principal),
            limit: int = Query(default=100, ge=1, le=500),  # G3-02: bound the page
            cursor: int = Query(default=0, ge=0),
        ) -> dict:
            # AR-08: resolve the readable groups ONCE, then filter every candidate.
            readable = planning_authority.readable_groups(principal)
            # INV-AGG: drop epics the viewer can't see entirely — no count/title/
            # capacity leak (indexer-design step 4); totals derive from visible only.
            #
            # G3-01 (accepted, bounded): an epic's group is taken from the index
            # (as of the last refresh), not live GitLab, so a group MOVE opens a
            # visibility-staleness window until reindex. It is disclosed via
            # as_of/never_indexed and closes when the real GitLab-group authority
            # replaces this stub (PR #54 follow-up); see impl-gate-3.md G3-01.
            visible = [e for e in planning_index.candidates() if e.group in readable]
            result = portfolio(visible, limit=limit, cursor=cursor)
            as_of = planning_index.as_of()
            result["as_of"] = as_of  # staleness marker (INV-IX-2)
            result["never_indexed"] = as_of is None  # G3-03: explicit unknown-staleness signal
            return result

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

        def _requester_for(t, principal: str) -> str | None:
            # G2-06: only agents/the requester/related parties see who filed it;
            # a community_visible-only viewer gets None.
            return t.requester if ticket_authority.can_see_identity(principal, t) else None

        @app.get("/tickets")
        def list_tickets(principal: str = Depends(get_principal)) -> list[dict]:
            tickets = ticket_store.all()
            readable = ticket_authority.readable_tickets(principal, tickets)
            return [{"id": t.id, "requester": _requester_for(t, principal)}
                    for t in tickets if t.id in readable]

        @app.get("/tickets/{ticket_id}")
        def get_ticket(ticket_id: str, principal: str = Depends(get_principal)) -> dict:
            t = ticket_store.get(ticket_id)
            if t is None or not ticket_authority.can_read(principal, t):
                raise HTTPException(status_code=404)
            return {"id": t.id, "requester": _requester_for(t, principal), "status": t.status,
                    "community_visible": t.community_visible}

        @app.post("/tickets")
        def create_ticket(
            body: TicketCreateIn,
            principal: str = Depends(get_principal),
        ) -> dict:
            # G2-02: bind the requester to the authenticated principal. Only an
            # agent may open a ticket on behalf of another requester.
            requester = body.requester
            if requester and requester != principal and not ticket_authority.is_agent(principal):
                raise HTTPException(status_code=403, detail="cannot create ticket for another requester")
            effective_requester = requester if (requester and ticket_authority.is_agent(principal)) else principal
            t = service.create(body.origin, effective_requester)
            return {"id": t.id, "requester": t.requester, "origin": t.origin,
                    "status": t.status, "community_visible": t.community_visible}

        @app.patch("/tickets/{ticket_id}")
        def transition_ticket(
            ticket_id: str,
            body: TicketTransitionIn,
            principal: str = Depends(get_principal),
        ) -> dict:
            t = service.transition(ticket_id, body.status, principal)
            return {"id": t.id, "status": t.status, "community_visible": t.community_visible}

        @app.post("/tickets/{ticket_id}/community-visible")
        def promote(ticket_id: str, principal: str = Depends(get_principal)) -> dict:
            t = service.promote_community_visible(ticket_id, principal)
            return {"id": t.id, "community_visible": t.community_visible}

    return app
