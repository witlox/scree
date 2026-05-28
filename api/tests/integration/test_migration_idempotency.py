"""@api — gate-10 fixes: migration idempotency derives from the durable store, not
the in-memory IdMap, so a re-run after a "restart" (fresh IdMap) creates no
duplicates (G10-01/02); confluence-without-doc_writer is counted as archived (G10-03)."""

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.migration.models import ArchiveStore, IdMap, SourceItem
from scree.migration.pipeline import MigrationPipeline
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.service import TicketService
from scree.servicedesk.store import TicketStore


def _pipeline(store, idmap, *, doc_writer=None):
    svc = TicketService(store, TicketAuthority(FakeOpenFga(), agents=set()),
                        comment_store=CommentStore(), identity=IdentityDirectory())
    return MigrationPipeline(svc, idmap, ArchiveStore(), doc_writer=doc_writer,
                             identity=IdentityDirectory())


def _jira(old_id):
    return SourceItem(kind="jira", old_id=old_id, title="t", content="c",
                      marked=True, reporter="a@x.ac")


def test_rerun_with_fresh_idmap_does_not_duplicate():
    # Shared durable store across two pipeline instances (= a restart with a new
    # in-memory IdMap). The second run must not re-create the ticket.
    store = TicketStore()
    first = _pipeline(store, IdMap()).run([_jira("SUP-1")])
    assert first == {"migrated": 1, "archived": 0, "skipped": 0}

    second = _pipeline(store, IdMap()).run([_jira("SUP-1")])  # fresh IdMap (restart)
    assert second == {"migrated": 0, "archived": 0, "skipped": 1}
    assert len(store.all()) == 1  # no duplicate despite the lost map


def test_deterministic_id_is_stable_across_runs():
    store = TicketStore()
    _pipeline(store, IdMap()).run([_jira("SUP-9")])
    tid = store.all()[0].id
    _pipeline(store, IdMap()).run([_jira("SUP-9")])
    assert [t.id for t in store.all()] == [tid]  # same id, single ticket


def test_confluence_without_doc_writer_counts_as_archived():
    # G10-03: no doc_writer → archived, not counted as migrated.
    store = TicketStore()
    archive = ArchiveStore()
    svc = TicketService(store, TicketAuthority(FakeOpenFga(), agents=set()))
    pipe = MigrationPipeline(svc, IdMap(), archive, doc_writer=None)
    summary = pipe.run([SourceItem(kind="confluence", old_id="12345", title="t",
                                   content="c", marked=True)])
    assert summary == {"migrated": 0, "archived": 1, "skipped": 0}
    assert archive.get("12345") is not None
