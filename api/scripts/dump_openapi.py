"""Dump the Gateway's OpenAPI schema to a file for frontend type generation.

The web client's API types are GENERATED from this schema (never hand-written) —
see .claude/coding/typescript.md. Wires a fully-featured app (all in-memory stores)
so every route is registered. Run with a Python that has the api deps installed:

    python api/scripts/dump_openapi.py web/openapi.json

Then `openapi-typescript openapi.json -o src/api/schema.d.ts` (the web `gen:api` script).
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `scree` importable

from scree.access.authority import Authority  # noqa: E402
from scree.access.audit import AuditSink  # noqa: E402
from scree.access.identity import IdentityDirectory  # noqa: E402
from scree.access.openfga import FakeOpenFga  # noqa: E402
from scree.access.ticket_authority import TicketAuthority  # noqa: E402
from scree.crypto.transit import FernetCrypto  # noqa: E402
from scree.gateway.app import create_app  # noqa: E402
from scree.integration.slack.capture import CaptureRateLimiter, SlackDirectory  # noqa: E402
from scree.knowledge.doc_service import DocService  # noqa: E402
from scree.knowledge.git_store import GitBackedDocStore  # noqa: E402
from scree.knowledge.store import DocStore  # noqa: E402
from scree.planning.authority import PlanningAuthority  # noqa: E402
from scree.planning.index import PlanningIndex  # noqa: E402
from scree.platform.health import Availability  # noqa: E402
from scree.portal.stores import AttachmentStore, PreferenceStore  # noqa: E402
from scree.risk.store import RiskStore  # noqa: E402
from scree.servicedesk.comments import CommentStore  # noqa: E402
from scree.servicedesk.quarantine import QuarantineStore  # noqa: E402
from scree.servicedesk.store import TicketStore  # noqa: E402


def build_app():
    tmp = tempfile.mkdtemp()
    for args in (["init", "-q"], ["config", "user.email", "a@scree.test"], ["config", "user.name", "a"]):
        subprocess.run(["git", "-C", tmp, *args], check=True, capture_output=True)
    git_store = GitBackedDocStore(tmp)
    return create_app(
        DocStore([]), Authority({}),
        ticket_store=TicketStore(), ticket_authority=TicketAuthority(FakeOpenFga(), set()),
        doc_writer=DocService(git_store, Authority({})),
        risk_store=RiskStore(), comment_store=CommentStore(),
        identity_directory=IdentityDirectory(), quarantine_store=QuarantineStore(),
        compliance_principals={"dpo"}, service_principals={"svc"},
        slack_directory=SlackDirectory({}), slack_rate_limiter=CaptureRateLimiter(),
        ticket_crypto=FernetCrypto(),
        planning_index=PlanningIndex(), planning_authority=PlanningAuthority({}),
        preference_store=PreferenceStore(), attachment_store=AttachmentStore(),
        availability=Availability(), audit=AuditSink(),
        allow_insecure_header_auth=True,
    )


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    schema = build_app().openapi()
    out.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"wrote {out} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
