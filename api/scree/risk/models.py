from dataclasses import dataclass
from typing import Literal

RiskCategory = Literal["delivery", "security", "compliance", "operational", "strategic"]
RiskStatus = Literal["open", "closed"]
Strategy = Literal["resolve", "owned", "accepted", "mitigated"]  # ROAM


def severity_band(score: int) -> str:
    """Normative bands (frontmatter-schemas/risk): 1-4 low, 5-9 medium,
    10-15 high, 16-25 critical."""
    if score <= 4:
        return "low"
    if score <= 9:
        return "medium"
    if score <= 15:
        return "high"
    return "critical"


@dataclass(frozen=True)
class Risk:
    id: str
    title: str
    space: str
    category: RiskCategory
    likelihood: int  # 1-5
    impact: int  # 1-5
    strategy: Strategy
    status: RiskStatus = "open"
    escalated_from: str | None = None
    owner: str | None = None  # accountable principal (orphan detection, INV-ORPH-1)

    @property
    def score(self) -> int:  # derived, never authored (F-12)
        return self.likelihood * self.impact

    @property
    def severity(self) -> str:  # derived band (F-13)
        return severity_band(self.score)
