"""Production ASGI entrypoint. Wires the Gateway's real components from the
environment and serves the built web SPA from the same image (one-image deploy):
the API is mounted at `/api` and the static web at `/`.

Fail-closed: in production (SCREE_DEV unset) the OIDC authenticator, token exchange,
GitLab authority, Vault crypto and OpenFGA are required — a missing one raises at
startup rather than silently degrading. Set SCREE_DEV=1 for a local/demo run that
uses the dev header-auth path and in-memory stores (no external services needed).

Run: `uvicorn scree.asgi:app`. Config: see .env.example / docker-compose.yml.
"""

import datetime as dt
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from scree.access.audit import AuditSink
from scree.access.authority import Authority
from scree.access.gitlab import GitLabAuthority
from scree.access.identity import FileIdentityDirectory, IdentityDirectory
from scree.access.oidc import OidcAuthenticator
from scree.access.openfga import FakeOpenFga, RealOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.access.token_exchange import KeycloakTokenExchanger, StaticTokenExchanger
from scree.crypto.transit import FernetCrypto, VaultTransitCrypto
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.git_store import GitBackedDocStore
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.planning.authority import PlanningAuthority
from scree.planning.index import PlanningIndex
from scree.planning.models import Epic
from scree.portal.stores import AttachmentStore, FileAttachmentStore, GitBackedAttachmentStore
from scree.risk.git_store import GitBackedRiskStore
from scree.risk.models import Risk
from scree.risk.store import RiskStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.git_comments import GitBackedCommentStore
from scree.servicedesk.git_store import GitBackedTicketStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore


def _csv(name: str) -> set[str]:
    return {x.strip() for x in os.environ.get(name, "").split(",") if x.strip()}


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required in production (set SCREE_DEV=1 for a dev run)")
    return value


def _seed_demo(common: dict, agents_env: set[str]) -> tuple:
    """Populate the in-memory stores so every surface shows content in SCREE_DEV mode.
    Default actor `rivera` is a member + agent (sees docs/risk/portfolio/admin + the
    full ticket queue); `ext-okafor` is a customer who owns two tickets (the portal
    view). Returns the demo (authority, doc_store, ticket_authority, planning_index,
    planning_authority)."""
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    HB, RP, DESK = "platform/handbook", "org/risk-portfolio", "support/service-desk"
    authority = Authority({"rivera": {HB, RP, DESK}, "agent:dani": {HB, DESK}})
    docs = DocStore([
        Doc("doc-onboarding", "Platform Onboarding", HB, "# Welcome\n\nGetting started on the platform.\n"),
        Doc("doc-runbook", "Incident Runbook", HB, "## When paged\n\n1. Acknowledge.\n2. Triage.\n3. Mitigate.\n"),
        Doc("doc-risk-policy", "Risk Management Policy", RP, "Risks are scored 5x5 with a ROAM strategy.\n"),
    ])
    for r in (
        Risk("risk-2026-001", "Vendor lock-in", RP, "strategic", 4, 4, "mitigated", owner="rivera"),
        Risk("risk-2026-014", "Migration slip", HB, "delivery", 3, 4, "owned", owner="rivera"),
        Risk("risk-2026-022", "Credential exposure", RP, "security", 2, 5, "mitigated", owner="agent:dani"),
    ):
        common["risk_store"].put(r)

    agents = {"rivera", "agent:dani"} | agents_env
    fga = FakeOpenFga()
    ticket_authority = TicketAuthority(fga, agents=agents)
    for t in (
        Ticket("ticket-2026-000123", requester="ext-okafor", space=DESK, status="open",
               assignee="agent:dani", origin="web", created_at=now),
        Ticket("ticket-2026-000200", requester="ext-lind", space=DESK, status="resolved", origin="email",
               created_at=now, community_visible=True,
               community_snapshot=(("agent:dani", "To reset your API key, open Portal → Settings.", "web"),)),
        Ticket("ticket-2026-000211", requester="ext-okafor", space=DESK, status="open", origin="slack", created_at=now),
    ):
        common["ticket_store"].put(t)
        fga.write(t.requester, "requester", t.id)  # so the customer sees their own tickets

    epics = [
        Epic("EPIC-100", "group/platform", "Platform v2", 21),
        Epic("EPIC-200", "group/portfolio", "Customer Portal GA", 13),
        Epic("EPIC-300", "group/secret", "Confidential initiative", 8),  # rivera not in group → hidden (INV-AGG)
    ]
    planning_index = PlanningIndex(epics, last_indexed=now)
    planning_authority = PlanningAuthority({"rivera": {"group/platform", "group/portfolio"}})
    return authority, docs, ticket_authority, planning_index, planning_authority


def build_app() -> FastAPI:
    dev = os.environ.get("SCREE_DEV") == "1"

    # Storage: durable when a path is configured, else in-memory (dev/demo).
    docs_repo = os.environ.get("SCREE_DOCS_REPO")
    risks_repo = os.environ.get("SCREE_RISKS_REPO")
    tickets_repo = os.environ.get("SCREE_TICKETS_REPO")  # tickets + comments + attachments live here
    identity_db = os.environ.get("SCREE_IDENTITY_DB")  # PII map, off Git (INV-DP-1)
    attachments_dir = os.environ.get("SCREE_ATTACHMENTS_DIR")  # S3/object-store alternative
    doc_store = GitBackedDocStore(docs_repo) if docs_repo else DocStore([])
    risk_store = GitBackedRiskStore(risks_repo) if risks_repo else RiskStore()
    doc_writer = DocService(doc_store, Authority({}), governed_prefixes=_csv("SCREE_GOVERNED_PREFIXES")) if docs_repo else None

    # Attachments (DD-002, revised): default to Git LFS in the ticket repo; an explicit
    # SCREE_ATTACHMENTS_DIR selects the S3/object-store alternative; in-memory in dev.
    if attachments_dir:
        attachment_store = FileAttachmentStore(attachments_dir)
    elif tickets_repo:
        attachment_store = GitBackedAttachmentStore(tickets_repo)
    else:
        attachment_store = AttachmentStore()

    common = dict(
        ticket_store=GitBackedTicketStore(tickets_repo) if tickets_repo else TicketStore(),
        comment_store=GitBackedCommentStore(tickets_repo) if tickets_repo else CommentStore(),
        identity_directory=FileIdentityDirectory(identity_db) if identity_db else IdentityDirectory(),
        attachment_store=attachment_store,
        risk_store=risk_store,
        doc_writer=doc_writer,
        audit=AuditSink(),
        service_principals=_csv("SCREE_SERVICE_PRINCIPALS"),
        compliance_principals=_csv("SCREE_COMPLIANCE_PRINCIPALS"),
        gitlab_audience=os.environ.get("GITLAB_AUDIENCE", "gitlab"),
    )
    agents = _csv("SCREE_AGENT_PRINCIPALS")

    if dev:
        # Seed a populated demo unless the dev run points at real stores.
        if not (docs_repo or risks_repo or tickets_repo):
            authority, doc_store, ticket_authority, planning_index, planning_authority = _seed_demo(common, agents)
        else:
            authority = Authority({})
            ticket_authority = TicketAuthority(FakeOpenFga(), agents=agents)
            planning_index = planning_authority = None
        api = create_app(
            doc_store, authority,
            ticket_authority=ticket_authority,
            ticket_crypto=FernetCrypto(),
            token_exchanger=StaticTokenExchanger(),
            planning_index=planning_index, planning_authority=planning_authority,
            allow_insecure_header_auth=True,
            **common,
        )
    else:
        openfga = RealOpenFga(_require("OPENFGA_URL"), _require("OPENFGA_STORE_ID"), _require("OPENFGA_MODEL_ID"))
        api = create_app(
            doc_store, Authority({}),
            authenticator=OidcAuthenticator(
                issuer=_require("OIDC_ISSUER"), audience=_require("OIDC_AUDIENCE"), jwks_url=_require("OIDC_JWKS_URL")
            ),
            token_exchanger=KeycloakTokenExchanger(
                token_url=_require("OIDC_TOKEN_URL"),
                client_id=_require("OIDC_CLIENT_ID"),
                client_secret=_require("OIDC_CLIENT_SECRET"),
            ),
            gitlab_authority=GitLabAuthority(_require("GITLAB_URL")),
            ticket_authority=TicketAuthority(openfga, agents=agents),
            ticket_crypto=VaultTransitCrypto(_require("VAULT_ADDR"), _require("VAULT_TOKEN")),
            **common,
        )

    root = FastAPI(title="Scree", docs_url=None, redoc_url=None)
    root.mount("/api", api)
    web_dir = os.environ.get("SCREE_WEB_DIR", "/app/web")
    if os.path.isdir(web_dir):
        root.mount("/", StaticFiles(directory=web_dir, html=True))  # the built SPA
    return root


app = build_app()
