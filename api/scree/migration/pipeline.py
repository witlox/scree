import hashlib

from scree.knowledge.doc_service import Conflict, DuplicateId

from .models import ArchiveStore, IdMap, SourceItem


def _legacy_key(item: SourceItem) -> str:
    return item.old_id if item.kind == "jira" else f"confluence:{item.old_id}"


def _deterministic_ticket_id(key: str) -> str:
    # Deterministic id so a re-run (even after a restart, with an empty IdMap) maps
    # the same legacy id to the same ticket — idempotency derives from the durable
    # store, not the volatile map (G10-01/02, INV-ST-2).
    return "ticket-mig-" + hashlib.sha1(key.encode()).hexdigest()[:12]


class MigrationPipeline:
    """Atlassian → Scree big-bang migration (DD-014). Marked items migrate (Jira →
    ticket, Confluence → doc) and record a stable old→new mapping (INV-MIG-1);
    re-running is idempotent against the DURABLE store (INV-MIG-2); unmarked items
    are archived, not migrated (INV-MIG-3); imported customer identities enter the
    erasable directory under the opaque-id model (INV-MIG-4 / INV-DP-1)."""

    def __init__(self, ticket_service, idmap: IdMap, archive: ArchiveStore,
                 doc_writer=None, identity=None) -> None:
        self._tickets = ticket_service
        self._idmap = idmap
        self._archive = archive
        self._doc_writer = doc_writer
        self._identity = identity

    def run(self, items: list[SourceItem]) -> dict:
        counts = {"migrated": 0, "archived": 0, "skipped": 0}
        for item in items:
            if not item.marked:  # INV-MIG-3: default-archive, migration is opt-in
                self._archive.archive(item)
                outcome = "archived"
            elif item.kind == "jira":
                outcome = self._migrate_ticket(item, _legacy_key(item))
            else:
                outcome = self._migrate_doc(item, _legacy_key(item))
            counts[outcome] += 1
        return counts

    def _migrate_ticket(self, item: SourceItem, key: str) -> str:
        new_id = _deterministic_ticket_id(key)
        if self._tickets.exists(new_id):  # already migrated (idempotent, restart-safe)
            self._idmap.record(key, new_id)  # repair the (rebuildable) mapping
            return "skipped"
        requester = (
            self._identity.resolve(item.reporter)
            if (item.reporter and self._identity) else (item.reporter or "unknown")
        )
        self._tickets.create("api", requester, space=item.space, ticket_id=new_id)
        self._tickets.add_comment(new_id, requester, item.content, "api")  # preserve content
        self._idmap.record(key, new_id)
        return "migrated"

    def _migrate_doc(self, item: SourceItem, key: str) -> str:
        if self._doc_writer is None:
            self._archive.archive(item)  # nowhere to write → archive (and count as such)
            return "archived"
        doc_id = f"confluence-{item.old_id}"
        frontmatter = (
            f"---\nid: {doc_id}\nkind: doc\nschema_version: 1\n"
            f"title: {item.title}\nspace: {item.space}\n---\n{item.content}\n"
        )
        try:
            result = self._doc_writer.write(f"migrated/{item.old_id}.md", frontmatter,
                                            author="migrator", base_rev=None)
            self._idmap.record(key, result["id"])
            return "migrated"
        except (Conflict, DuplicateId):  # already migrated → idempotent
            self._idmap.record(key, doc_id)
            return "skipped"
