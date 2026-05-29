"""Production ASGI entrypoint. Wires the Gateway's real components from the
environment and serves the built web SPA from the same image (one-image deploy):
the API is mounted at `/api` and the static web at `/`.

Fail-closed: in production (SCREE_DEV unset) the OIDC authenticator, token exchange,
GitLab authority, Vault crypto and OpenFGA are required — a missing one raises at
startup rather than silently degrading. Set SCREE_DEV=1 for a local/demo run that
uses the dev header-auth path and in-memory stores (no external services needed).

Run: `uvicorn scree.asgi:app`. Config: see .env.example / docker-compose.yml.
"""

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
from scree.knowledge.store import DocStore
from scree.portal.stores import AttachmentStore, FileAttachmentStore
from scree.risk.git_store import GitBackedRiskStore
from scree.risk.store import RiskStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.git_comments import GitBackedCommentStore
from scree.servicedesk.git_store import GitBackedTicketStore
from scree.servicedesk.store import TicketStore


def _csv(name: str) -> set[str]:
    return {x.strip() for x in os.environ.get(name, "").split(",") if x.strip()}


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required in production (set SCREE_DEV=1 for a dev run)")
    return value


def build_app() -> FastAPI:
    dev = os.environ.get("SCREE_DEV") == "1"

    # Storage: durable when a path is configured, else in-memory (dev/demo).
    docs_repo = os.environ.get("SCREE_DOCS_REPO")
    risks_repo = os.environ.get("SCREE_RISKS_REPO")
    tickets_repo = os.environ.get("SCREE_TICKETS_REPO")  # tickets + comments live here
    identity_db = os.environ.get("SCREE_IDENTITY_DB")  # PII map, off Git (INV-DP-1)
    attachments_dir = os.environ.get("SCREE_ATTACHMENTS_DIR")  # object storage, not Git
    doc_store = GitBackedDocStore(docs_repo) if docs_repo else DocStore([])
    risk_store = GitBackedRiskStore(risks_repo) if risks_repo else RiskStore()
    doc_writer = DocService(doc_store, Authority({}), governed_prefixes=_csv("SCREE_GOVERNED_PREFIXES")) if docs_repo else None

    common = dict(
        ticket_store=GitBackedTicketStore(tickets_repo) if tickets_repo else TicketStore(),
        comment_store=GitBackedCommentStore(tickets_repo) if tickets_repo else CommentStore(),
        identity_directory=FileIdentityDirectory(identity_db) if identity_db else IdentityDirectory(),
        attachment_store=FileAttachmentStore(attachments_dir) if attachments_dir else AttachmentStore(),
        risk_store=risk_store,
        doc_writer=doc_writer,
        audit=AuditSink(),
        service_principals=_csv("SCREE_SERVICE_PRINCIPALS"),
        compliance_principals=_csv("SCREE_COMPLIANCE_PRINCIPALS"),
        gitlab_audience=os.environ.get("GITLAB_AUDIENCE", "gitlab"),
    )
    agents = _csv("SCREE_AGENT_PRINCIPALS")

    if dev:
        api = create_app(
            doc_store, Authority({}),
            ticket_authority=TicketAuthority(FakeOpenFga(), agents=agents),
            ticket_crypto=FernetCrypto(),
            token_exchanger=StaticTokenExchanger(),
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
