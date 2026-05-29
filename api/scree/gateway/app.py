import time
import uuid

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from scree.access.audit import AuditSink
from scree.access.authority import Authority
from scree.access.cache import TtlCache
from scree.access.gitlab import SpaceAuthority
from scree.access.oidc import AuthError, OidcAuthenticator
from scree.access.ticket_authority import TicketAuthority
from scree.access.token_exchange import TokenExchanger
from scree.knowledge.doc_service import (
    Conflict,
    DocService,
    DuplicateId,
    IdChanged,
    InvalidPath,
    MRRequired,
    SpaceMismatch,
    WrongKind,
)
from scree.knowledge.doc_service import Forbidden as DocForbidden
from scree.knowledge.frontmatter import InvalidFrontmatter
from scree.knowledge.git_store import GitWriteError
from scree.knowledge.store import DocStore
from scree.indexing.orphans import OrphanCache, detect_orphans
from scree.planning.authority import PlanningAuthority
from scree.planning.index import PlanningIndex
from scree.planning.rollup import portfolio
from scree.risk.models import Risk, RiskCategory, Strategy
from scree.risk.store import RiskStore
from scree.risk.triggers import fires_critical_webhook
from scree.access.erasure import ErasureReceiptStore, ErasureService
from scree.access.identity import IdentityDirectory
from scree.crypto.transit import FernetCrypto, TicketCrypto
from scree.integration.o365.inbound import parse_inbound
from scree.integration.slack.capture import CaptureRateLimiter, SlackDirectory
from scree.migration.models import ArchiveStore, IdMap, SourceItem, SourceKind
from scree.migration.pipeline import MigrationPipeline
from scree.platform.health import Availability
from scree.portal.stores import AttachmentStore, PreferenceStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.lifecycle import IllegalTransition
from scree.servicedesk.quarantine import QuarantineStore
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
    encrypt: bool = False  # create-time decision (ADR-0005)
    body: str | None = None  # initial description, encrypted at rest if encrypt


class TicketTransitionIn(BaseModel):
    status: str


class SourceItemIn(BaseModel):
    kind: SourceKind
    old_id: str
    title: str = ""
    content: str = ""
    marked: bool = False
    reporter: str | None = None
    space: str = "support/service-desk"


class MigrationRunIn(BaseModel):
    items: list[SourceItemIn]


class PreferenceIn(BaseModel):
    preference: str


class AttachmentIn(BaseModel):
    filename: str
    content: str  # text payload for the spike (real impl streams bytes to object storage)


# Response models — so the OpenAPI schema is precise and the web client's types are
# GENERATED (not hand-written). See .claude/coding/typescript.md.
class DocSummaryOut(BaseModel):
    id: str
    title: str
    space: str


class DocDetailOut(BaseModel):
    id: str
    title: str
    space: str
    body: str
    schema_version: int
    path: str | None
    rev: str | None
    created: str | None
    updated: str | None


class DocVersionOut(BaseModel):
    rev: str
    author: str
    date: str
    message: str


class DocWriteOut(BaseModel):
    id: str
    path: str
    space: str
    rev: str | None

MAX_INBOUND_EMAIL_BYTES = 1_000_000  # G4-06: bound inbound email like doc content (G2-07)
MAX_COMMENT_BYTES = 1_000_000  # G8-03: bound ticket body / Slack snapshot comments
LAST_KNOWN_MAX_AGE = 900.0  # G-A2: outage staleness bound (s) before membership fails closed


def _check_comment_size(text: str | None) -> None:
    if text is not None and len(text.encode("utf-8")) > MAX_COMMENT_BYTES:
        raise HTTPException(status_code=413, detail="comment body too large")


# G11-03: reject executable/script attachment types from external uploads. (AV
# scanning at the object-storage boundary is a deployment concern.)
_BLOCKED_ATTACHMENT_EXT = {
    ".exe", ".dll", ".bat", ".cmd", ".com", ".sh", ".ps1", ".scr", ".msi",
    ".js", ".jar", ".vbs", ".app", ".deb", ".rpm",
}


def _safe_attachment(filename: str) -> bool:
    name = (filename or "").lower()
    return not any(name.endswith(ext) for ext in _BLOCKED_ATTACHMENT_EXT)

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
    IdChanged: 409,
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
    comment_store: CommentStore | None = None,
    identity_directory: IdentityDirectory | None = None,
    quarantine_store: QuarantineStore | None = None,
    compliance_principals: set[str] | None = None,
    service_principals: set[str] | None = None,
    archived_spaces: set[str] | None = None,
    slack_directory: SlackDirectory | None = None,
    slack_rate_limiter: CaptureRateLimiter | None = None,
    ticket_crypto: TicketCrypto | None = None,
    planning_index: PlanningIndex | None = None,
    planning_authority: PlanningAuthority | None = None,
    gitlab_authority: SpaceAuthority | None = None,
    token_exchanger: TokenExchanger | None = None,
    gitlab_audience: str = "gitlab",
    preference_store: PreferenceStore | None = None,
    attachment_store: AttachmentStore | None = None,
    availability: Availability | None = None,
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
    # G9-02: the composed GitLab authority needs a token source, else every request
    # silently resolves to empty authority. Require a token_exchanger unless on the
    # dev header path.
    if gitlab_authority is not None and token_exchanger is None and not allow_insecure_header_auth:
        raise ValueError("gitlab_authority requires a token_exchanger (or the dev header path)")
    # docs_url/redoc_url disabled: "/docs" is a Scree resource path, not Swagger UI.
    app = FastAPI(docs_url=None, redoc_url=None)

    # Dedicated ingestion/batch service principals (G6-02), archived Spaces, and the
    # batch-computed orphan report cache (G7-03) — shared across endpoints.
    services = service_principals or set()
    archived = archived_spaces or set()
    orphan_cache = OrphanCache()
    id_map = IdMap()  # migration old→new id mapping (INV-MIG-1), survives the app's lifetime
    archive_store = ArchiveStore()
    prefs = preference_store or PreferenceStore()  # portal self-service preferences
    attachments = attachment_store or AttachmentStore()  # object storage (NOT Git)
    health = availability or Availability()

    def _require_gitlab() -> None:
        # INV-DEG-1: refuse writes clearly when GitLab is down — never silently drop.
        if not health.gitlab_up:
            raise HTTPException(status_code=503, detail="GitLab is unavailable; write refused")
    # G9-01 (AR-08): short-TTL caches so a busy Gateway doesn't exchange tokens /
    # resolve GitLab membership on every request.
    _token_cache: TtlCache[str] = TtlCache(ttl=60.0)
    _space_cache: TtlCache[set] = TtlCache(ttl=60.0)
    _group_cache: TtlCache[set] = TtlCache(ttl=60.0)
    # G12-01: last-known membership, served stale-OK while GitLab is unreachable so
    # authorized reads survive an outage (INV-DEG-1). G-A2: bounded by
    # LAST_KNOWN_MAX_AGE — past that we fail closed (INV-ACC-5) rather than honor a
    # possibly-revoked grant for the whole outage. The bound is the explicit point
    # where availability yields to not-over-exposing; the cached value is timestamped.
    _last_spaces: dict[str, tuple[set, float]] = {}
    _last_groups: dict[str, tuple[set, float]] = {}

    def _last_known(store: dict[str, tuple[set, float]], token: str) -> set:
        entry = store.get(token)
        if entry is None or (time.monotonic() - entry[1]) > LAST_KNOWN_MAX_AGE:
            return set()  # fail closed: no membership, or staler than the bound
        return entry[0]

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
            bearer = authorization.split(" ", 1)[1]
            try:
                principal = authenticator.principal(bearer)
            except AuthError:
                raise HTTPException(status_code=401, detail="invalid token")
            if token_exchanger is not None:
                # I-03: trade the inbound token for a GitLab-scoped one (RFC 8693),
                # so the Gateway resolves authority as the user against GitLab.
                # G9-01: cache the exchange (short TTL) to avoid a round-trip/request.
                gitlab_token = _token_cache.get(bearer)
                if gitlab_token is None:
                    try:
                        gitlab_token = token_exchanger.exchange(bearer, gitlab_audience)
                    except AuthError:
                        raise HTTPException(status_code=401, detail="token exchange failed")
                    _token_cache.put(bearer, gitlab_token)
                request.state.gitlab_token = gitlab_token
        elif allow_insecure_header_auth and x_spike_user:
            principal = x_spike_user  # spike/dev only (gated by allow_insecure_header_auth)
            if gitlab_authority is not None:
                request.state.gitlab_token = x_spike_user  # dev: header doubles as the GitLab token
        else:
            raise HTTPException(status_code=401, detail="no identity")
        request.state.principal = principal  # I-08: record for the audit sink
        return principal

    def _readable_spaces(principal: str, request: Request) -> set[str]:
        # Composed authority: real GitLab membership when configured (resolved ONCE
        # per request AND cached short-TTL across requests, AR-08), else the stub.
        if gitlab_authority is not None:
            token = getattr(request.state, "gitlab_token", None)
            if not token:
                return set()
            cached = _space_cache.get(token)
            if cached is None:
                if not health.gitlab_up:  # G12-01: outage → serve last-known (bounded)
                    return _last_known(_last_spaces, token)
                cached = gitlab_authority.readable_spaces(token)
                _space_cache.put(token, cached)
                _last_spaces[token] = (cached, time.monotonic())
            return cached
        return authority.readable_spaces(principal)

    def _readable_groups(principal: str, request: Request) -> set[str]:
        if gitlab_authority is not None:
            token = getattr(request.state, "gitlab_token", None)
            if not token:
                return set()
            cached = _group_cache.get(token)
            if cached is None:
                if not health.gitlab_up:  # G12-01: outage → serve last-known (bounded)
                    return _last_known(_last_groups, token)
                cached = gitlab_authority.readable_groups(token)
                _group_cache.put(token, cached)
                _last_groups[token] = (cached, time.monotonic())
            return cached
        return planning_authority.readable_groups(principal) if planning_authority else set()

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
            _require_gitlab()
            if not authority.can_write(principal, body.space):
                raise HTTPException(status_code=403)
            risk = Risk(id=f"risk-{uuid.uuid4().hex[:8]}", title=body.title, space=body.space,
                        category=body.category, likelihood=body.likelihood,
                        impact=body.impact, strategy=body.strategy, owner=principal)
            risk_store.put(risk)
            return _risk_view(risk)

        @app.get("/risks")
        def list_risks(request: Request, principal: str = Depends(get_principal)) -> list[dict]:
            readable = _readable_spaces(principal, request)  # INV-AGG over risks
            return [_risk_view(r) for r in risk_store.all() if r.space in readable]

    @app.post("/orphans/refresh")
    def refresh_orphans(principal: str = Depends(get_principal)) -> dict:
        # G7-03: the "hourly batch" / manual trigger. A service principal recomputes
        # the report once into the cache; reads then don't re-resolve every owner.
        if principal not in services:
            raise HTTPException(status_code=403, detail="orphan refresh is service-principal only")
        risks_list = risk_store.all() if risk_store is not None else []
        can_tickets = ticket_store is not None and ticket_authority is not None
        tickets_list = ticket_store.all() if can_tickets else []
        report = detect_orphans(
            risks_list, tickets_list, authority=authority,
            ticket_authority=ticket_authority, archived_spaces=archived,
        )
        orphan_cache.report = report
        return {"refreshed": True, "as_of": report.as_of}

    @app.get("/portal/preferences")
    def get_preferences(principal: str = Depends(get_principal)) -> dict:
        return {"preference": prefs.get(principal)}

    @app.put("/portal/preferences")
    def set_preferences(body: PreferenceIn, principal: str = Depends(get_principal)) -> dict:
        prefs.set(principal, body.preference)  # self-service, applies to future notifications
        return {"preference": body.preference}

    @app.get("/migration/resolve/{legacy_id:path}")
    def resolve_legacy(legacy_id: str, principal: str = Depends(get_principal)) -> dict:
        # INV-MIG-1: a legacy reference resolves to its migrated item (no broken links).
        new_id = id_map.resolve(legacy_id)
        if new_id is None:
            raise HTTPException(status_code=404, detail="no mapping for legacy id")
        return {"legacy_id": legacy_id, "resolved": new_id}

    @app.get("/orphans")
    def orphans(principal: str = Depends(get_principal)) -> dict:
        # INV-ORPH: serve the batch-computed report, filtered to the requester's
        # scope — resources to the Space's maintainers, tickets to the desk's leads
        # (both = can_write, G7-02). Never auto-reassigned.
        report = orphan_cache.report
        if report is None:
            return {"resources": {}, "tickets": {}, "as_of": None, "computed": False}
        resources = {sp: ids for sp, ids in report.resources.items() if authority.can_write(principal, sp)}
        tickets = {sp: ids for sp, ids in report.tickets.items() if authority.can_write(principal, sp)}
        return {"resources": resources, "tickets": tickets, "as_of": report.as_of, "computed": True}

    if planning_index is not None and planning_authority is not None:

        @app.get("/planning/portfolio")
        def portfolio_rollup(
            request: Request,
            principal: str = Depends(get_principal),
            limit: int = Query(default=100, ge=1, le=500),  # G3-02: bound the page
            cursor: int = Query(default=0, ge=0),
        ) -> dict:
            # AR-08: resolve the readable groups ONCE, then filter every candidate.
            # With the composed GitLab authority configured, this is LIVE group
            # membership (closing the G3-01 stale-group window); else the stub.
            readable = _readable_groups(principal, request)
            # INV-AGG: drop epics the viewer can't see entirely — no count/title/
            # capacity leak (indexer-design step 4); totals derive from visible only.
            visible = [e for e in planning_index.candidates() if e.group in readable]
            result = portfolio(visible, limit=limit, cursor=cursor)
            as_of = planning_index.as_of()
            result["as_of"] = as_of  # staleness marker (INV-IX-2)
            result["never_indexed"] = as_of is None  # G3-03: explicit unknown-staleness signal
            return result

    @app.get("/docs", response_model=list[DocSummaryOut])
    def list_docs(request: Request, principal: str = Depends(get_principal)) -> list[dict]:
        # INV-AGG: filter EVERY item by the requester's authority, per request.
        readable = _readable_spaces(principal, request)
        return [{"id": d.id, "title": d.title, "space": d.space}
                for d in store.all() if d.space in readable]

    @app.get("/docs/{doc_id}", response_model=DocDetailOut)
    def get_doc(doc_id: str, request: Request, principal: str = Depends(get_principal)) -> dict:
        d = store.get(doc_id)
        if d is None or d.space not in _readable_spaces(principal, request):
            raise HTTPException(status_code=404)  # existence-leak-safe
        # path + rev + schema_version let an editor round-trip an edit safely
        # (rebuild frontmatter; base_rev for optimistic concurrency, INV-ST-6). The
        # in-memory store has no rev(); only the Git-backed store does.
        rev = store.rev(d.path) if hasattr(store, "rev") and d.path else None
        return {"id": d.id, "title": d.title, "space": d.space, "body": d.body,
                "schema_version": d.schema_version, "path": d.path, "rev": rev,
                "created": d.created, "updated": d.updated}

    @app.get("/docs/{doc_id}/versions", response_model=list[DocVersionOut])
    def get_doc_versions(doc_id: str, request: Request, principal: str = Depends(get_principal)) -> list[dict]:
        d = store.get(doc_id)
        if d is None or d.space not in _readable_spaces(principal, request):
            raise HTTPException(status_code=404)  # existence-leak-safe
        # Versions are Git commits (INV-ST-5). Only the Git-backed store has history.
        if not hasattr(store, "history") or d.path is None:
            return []
        return store.history(d.path)

    if doc_writer is not None:

        @app.post("/docs", response_model=DocWriteOut)
        def write_doc(
            path: str = Body(..., embed=True),
            content: str = Body(..., embed=True),
            base_rev: str | None = Body(default=None, embed=True),
            principal: str = Depends(get_principal),
        ) -> dict:
            _require_gitlab()
            return doc_writer.write(path, content, principal, base_rev)

    if ticket_store is not None and ticket_authority is not None:
        identity = identity_directory or IdentityDirectory()
        quarantine = quarantine_store or QuarantineStore()
        compliance = compliance_principals or set()  # fail-closed: no one erases unless configured
        slack_dir = slack_directory or SlackDirectory()
        slack_limiter = slack_rate_limiter or CaptureRateLimiter()
        # G8-01: durable per-requester crypto (Vault Transit) is required in prod;
        # FernetCrypto's in-memory keys are lost on restart, so only allow it under
        # the same dev/spike opt-in as header auth.
        if ticket_crypto is None and not allow_insecure_header_auth:
            raise ValueError(
                "ticket_crypto (durable per-requester crypto, e.g. Vault Transit) is required; "
                "FernetCrypto is in-memory and dev-only (allow_insecure_header_auth)."
            )
        crypto = ticket_crypto or FernetCrypto()
        receipts = ErasureReceiptStore()
        service = TicketService(
            ticket_store, ticket_authority, comment_store=comment_store,
            identity=identity, quarantine=quarantine, crypto=crypto,
        )
        erasure = ErasureService(identity, ticket_authority, quarantine=quarantine,
                                 receipts=receipts, crypto=crypto)

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

        # Declared before /tickets/{ticket_id} so the static path isn't shadowed.
        @app.get("/tickets/quarantine")
        def list_quarantine(principal: str = Depends(get_principal)) -> list[dict]:
            # G4-05: quarantined mail held for agent review.
            if not ticket_authority.is_agent(principal):
                raise HTTPException(status_code=403, detail="quarantine review is agent-only")
            return [{"claimed_from": q.claimed_from, "subject": q.subject,
                     "reason": q.reason, "candidate_ticket": q.candidate_ticket}
                    for q in quarantine.all()]

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
            _require_gitlab()  # INV-DEG-1: refuse creation when GitLab is down
            # G2-02: bind the requester to the authenticated principal. Only an
            # agent may open a ticket on behalf of another requester.
            requester = body.requester
            if requester and requester != principal and not ticket_authority.is_agent(principal):
                raise HTTPException(status_code=403, detail="cannot create ticket for another requester")
            effective_requester = requester if (requester and ticket_authority.is_agent(principal)) else principal
            _check_comment_size(body.body)  # G8-03
            t = service.create(body.origin, effective_requester, encrypted=body.encrypt)
            if body.body:  # initial description, encrypted at rest if the ticket is encrypted
                service.add_comment(t.id, principal, body.body, "api")
            return {"id": t.id, "requester": t.requester, "origin": t.origin,
                    "status": t.status, "community_visible": t.community_visible, "encrypted": t.encrypted}

        @app.get("/tickets/{ticket_id}/comments")
        def get_comments(ticket_id: str, principal: str = Depends(get_principal)) -> list[dict]:
            t = ticket_store.get(ticket_id)
            if t is None or not ticket_authority.can_read(principal, t):
                raise HTTPException(status_code=404)
            # INV-LC-2: a community-only viewer (can read solely because the ticket is
            # community_visible, not a participant) sees the curated snapshot frozen at
            # promotion — never the live thread, so later private replies don't leak.
            if t.community_visible and not ticket_authority.can_see_identity(principal, t):
                return service.community_snapshot(ticket_id)
            # Gateway-mediated decryption (ADR-0008): bodies are ciphertext at rest.
            return service.read_comments(ticket_id)

        @app.get("/community/search")
        def community_search(q: str, principal: str = Depends(get_principal)) -> list[dict]:
            # Portal community KB: ONLY community_visible tickets (curated public
            # snapshot, INV-LC-2); a private/non-promoted ticket NEVER appears.
            needle = q.lower()
            out = []
            for t in ticket_store.all():
                if not t.community_visible or t.encrypted:
                    continue  # G11-01: never decrypt encrypted content into the public KB
                # INV-LC-2: the public KB indexes the curated snapshot, not the live
                # thread, so a post-promotion private reply never becomes searchable.
                bodies = [c["body"] for c in service.community_snapshot(t.id)]
                if any(needle in (b or "").lower() for b in bodies):
                    out.append({"id": t.id})  # requester not disclosed (G2-06)
            return out

        def _attachment_ticket(ticket_id: str, principal: str):
            # G11-02: uploads/listing are participant-only (requester/agent/related),
            # NOT mere community read — else any authenticated user could attach.
            t = ticket_store.get(ticket_id)
            if t is None or not ticket_authority.can_see_identity(principal, t):
                raise HTTPException(status_code=404)
            return t

        @app.post("/tickets/{ticket_id}/attachments")
        def add_attachment(ticket_id: str, body: AttachmentIn,
                           principal: str = Depends(get_principal)) -> dict:
            _attachment_ticket(ticket_id, principal)
            if not _safe_attachment(body.filename):  # G11-03: reject executable types
                raise HTTPException(status_code=415, detail="attachment type not allowed")
            raw = body.content.encode("utf-8")
            if len(raw) > MAX_COMMENT_BYTES:
                raise HTTPException(status_code=413, detail="attachment too large")
            # Stored in OBJECT STORAGE, not Git (external-attachment decision).
            att = attachments.put(ticket_id, body.filename, raw)
            return {"filename": att.filename, "object_key": att.object_key}

        @app.get("/tickets/{ticket_id}/attachments")
        def list_attachments(ticket_id: str, principal: str = Depends(get_principal)) -> list[dict]:
            _attachment_ticket(ticket_id, principal)
            return [{"filename": a.filename, "object_key": a.object_key}
                    for a in attachments.for_ticket(ticket_id)]

        @app.post("/tickets/{ticket_id}/encrypt")
        def encrypt_ticket(ticket_id: str, principal: str = Depends(get_principal)) -> dict:
            t = ticket_store.get(ticket_id)
            if t is None or not ticket_authority.can_read(principal, t):
                raise HTTPException(status_code=404)
            if not (ticket_authority.is_agent(principal) or principal == t.assignee):
                raise HTTPException(status_code=403)
            # Feature: encryption is a create-time decision; refuse retroactively and
            # warn that prior cleartext remains in Git history.
            raise HTTPException(
                status_code=409,
                detail="encryption is create-time only; prior cleartext remains in Git history",
            )

        @app.patch("/tickets/{ticket_id}")
        def transition_ticket(
            ticket_id: str,
            body: TicketTransitionIn,
            principal: str = Depends(get_principal),
        ) -> dict:
            _require_gitlab()
            t = service.transition(ticket_id, body.status, principal)
            return {"id": t.id, "status": t.status, "community_visible": t.community_visible}

        @app.post("/tickets/{ticket_id}/community-visible")
        def promote(ticket_id: str, principal: str = Depends(get_principal)) -> dict:
            _require_gitlab()
            t = service.promote_community_visible(ticket_id, principal)
            return {"id": t.id, "community_visible": t.community_visible}

        @app.post("/tickets/inbound-email")
        def inbound_email(
            raw: str = Body(..., embed=True),
            verified: bool = Body(default=False, embed=True),
            sender: str | None = Body(default=None, embed=True),
            principal: str = Depends(get_principal),
        ) -> dict:
            # DD-006: the email poller is a separate trusted service that posts here.
            # Only an agent/service principal may ingest mail, and the DKIM/DMARC
            # verdict (`verified`) + aligned `sender` come from the poller, NOT the
            # attacker-controlled raw message (G4-01). The verified sender — not the
            # caller — becomes the (opaque) requester (INV-EMAIL-1 / G2-02).
            if principal not in services:  # G6-02: dedicated poller service principal
                raise HTTPException(status_code=403, detail="email ingestion is service-principal only")
            if not health.email_up:  # INV-DEG-2: O365 down → fail visibly, no silent loss
                raise HTTPException(status_code=503, detail="email/O365 is unavailable")
            _require_gitlab()  # ticket creation also needs GitLab
            if len(raw.encode("utf-8")) > MAX_INBOUND_EMAIL_BYTES:  # G4-06
                raise HTTPException(status_code=413, detail="inbound email too large")
            return service.ingest_email(parse_inbound(raw), verified=verified, sender=sender)

        @app.post("/slack/capture")
        def slack_capture(
            reactor: str = Body(..., embed=True),
            author: str = Body(..., embed=True),
            snapshot: str = Body(default="", embed=True),
            principal: str = Depends(get_principal),
        ) -> dict:
            # DD-006: the Slack bot is a separate service that posts here as an
            # agent/service principal; the user identities ride in the event.
            if principal not in services:
                raise HTTPException(status_code=403, detail="slack capture is service-principal only")
            _require_gitlab()  # INV-DEG-1: capture creates a ticket
            _check_comment_size(snapshot)  # G8-03
            return service.capture_from_slack(reactor, author, snapshot, slack_dir=slack_dir, limiter=slack_limiter)

        @app.post("/slack/link-ticket")
        def slack_link(
            reactor: str = Body(..., embed=True),
            ticket_id: str = Body(..., embed=True),
            snapshot: str = Body(default="", embed=True),
            principal: str = Depends(get_principal),
        ) -> dict:
            if principal not in services:
                raise HTTPException(status_code=403, detail="slack link is service-principal only")
            _require_gitlab()  # G12-02: appends a Git-backed comment
            _check_comment_size(snapshot)  # G8-03
            return service.link_from_slack(reactor, ticket_id, snapshot, slack_dir=slack_dir)

        @app.get("/identities/erasures")
        def list_erasures(principal: str = Depends(get_principal)) -> list[dict]:
            # G5-03: durable erasure receipts for compliance evidence (DPO only).
            if principal not in compliance:
                raise HTTPException(status_code=403, detail="erasure log is compliance-only")
            return [{"subject": r.subject, "actor": r.actor, "at": r.at,
                     "identity_removed": r.identity_removed, "relations_purged": r.relations_purged,
                     "quarantine_purged": r.quarantine_purged} for r in receipts.all()]

        @app.delete("/identities/{opaque_id}")
        def erase_identity(opaque_id: str, principal: str = Depends(get_principal)) -> dict:
            # GDPR erasure (INV-DP-2): compliance/DPO role only. Anonymizes by
            # deleting the identity record, purging OpenFGA tuples, and scrubbing
            # the quarantine queue; Git untouched (residual disclosed in response).
            if principal not in compliance:
                raise HTTPException(status_code=403, detail="erasure is compliance-only")
            return erasure.erase(opaque_id, actor=principal)

        migration = MigrationPipeline(service, id_map, archive_store,
                                      doc_writer=doc_writer, identity=identity)

        @app.post("/migration/run")
        def run_migration(body: MigrationRunIn, principal: str = Depends(get_principal)) -> dict:
            # Big-bang cutover batch — service principal only (DD-006/DD-014).
            if principal not in services:
                raise HTTPException(status_code=403, detail="migration is service-principal only")
            _require_gitlab()  # G12-02: bulk-creates Git-backed tickets/docs
            items = [SourceItem(kind=i.kind, old_id=i.old_id, title=i.title, content=i.content,
                                marked=i.marked, reporter=i.reporter, space=i.space)
                     for i in body.items]
            return migration.run(items)

    return app
