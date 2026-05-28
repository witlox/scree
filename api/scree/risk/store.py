from .models import Risk


class RiskStore:
    """In-memory risk store for the spike (real impl persists to Git repos:
    project `risks/` and dedicated org spaces, DD-004)."""

    def __init__(self, risks: list[Risk] | None = None) -> None:
        self._risks: dict[str, Risk] = {r.id: r for r in (risks or [])}

    def get(self, risk_id: str) -> Risk | None:
        return self._risks.get(risk_id)

    def all(self) -> list[Risk]:
        return list(self._risks.values())

    def put(self, risk: Risk) -> None:
        self._risks[risk.id] = risk
