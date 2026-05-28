from .models import Doc


class DocStore:
    """In-memory doc store for the spike. Real impl reads Git-backed files."""

    def __init__(self, docs: list[Doc] | None = None) -> None:
        self._docs: dict[str, Doc] = {d.id: d for d in (docs or [])}

    def get(self, doc_id: str) -> Doc | None:
        return self._docs.get(doc_id)

    def all(self) -> list[Doc]:
        return list(self._docs.values())
