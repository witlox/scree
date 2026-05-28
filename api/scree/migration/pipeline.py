from .models import ArchiveStore, IdMap, SourceItem


def _legacy_key(item: SourceItem) -> str:
    return item.old_id if item.kind == "jira" else f"confluence:{item.old_id}"


class MigrationPipeline:
    """Atlassian → Scree big-bang migration (DD-014). Marked items migrate (Jira →
    ticket, Confluence → doc) and record a stable old→new mapping (INV-MIG-1);
    re-running is idempotent (INV-MIG-2); unmarked items are archived, not migrated
    (INV-MIG-3); imported customer identities enter the erasable directory under the
    opaque-id model (INV-MIG-4 / INV-DP-1)."""

    def __init__(self, ticket_service, idmap: IdMap, archive: ArchiveStore,
                 doc_writer=None, identity=None) -> None:
        self._tickets = ticket_service
        self._idmap = idmap
        self._archive = archive
        self._doc_writer = doc_writer
        self._identity = identity

    def run(self, items: list[SourceItem]) -> dict:
        migrated, archived, skipped = 0, 0, 0
        for item in items:
            if not item.marked:  # INV-MIG-3: default-archive, migration is opt-in
                self._archive.archive(item)
                archived += 1
                continue
            key = _legacy_key(item)
            if self._idmap.has(key):  # INV-MIG-2: idempotent — no duplicates
                skipped += 1
                continue
            if item.kind == "jira":
                self._migrate_ticket(item, key)
            else:
                self._migrate_doc(item, key)
            migrated += 1
        return {"migrated": migrated, "archived": archived, "skipped": skipped}

    def _migrate_ticket(self, item: SourceItem, key: str) -> None:
        # Opaque requester via the erasable identity directory (INV-MIG-4 / INV-DP-1).
        requester = (
            self._identity.resolve(item.reporter)
            if (item.reporter and self._identity) else (item.reporter or "unknown")
        )
        ticket = self._tickets.create("api", requester, space=item.space)  # grants OpenFGA tuple
        self._tickets.add_comment(ticket.id, requester, item.content, "api")  # preserve content
        self._idmap.record(key, ticket.id)

    def _migrate_doc(self, item: SourceItem, key: str) -> None:
        if self._doc_writer is None:
            self._archive.archive(item)  # nowhere to write → archive rather than lose
            return
        doc_id = f"confluence-{item.old_id}"
        frontmatter = (
            f"---\nid: {doc_id}\nkind: doc\nschema_version: 1\n"
            f"title: {item.title}\nspace: {item.space}\n---\n{item.content}\n"
        )
        result = self._doc_writer.write(f"migrated/{item.old_id}.md", frontmatter,
                                        author="migrator", base_rev=None)
        self._idmap.record(key, result["id"])
