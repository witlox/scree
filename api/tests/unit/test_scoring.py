"""TDD — risk scoring: derived score and normative severity bands (F-12/F-13)."""

import pytest

from scree.risk.models import Risk, severity_band


@pytest.mark.parametrize(
    "score,band",
    [(1, "low"), (4, "low"), (5, "medium"), (9, "medium"),
     (10, "high"), (15, "high"), (16, "critical"), (25, "critical")],
)
def test_severity_bands(score, band):
    assert severity_band(score) == band


def test_score_and_severity_are_derived():
    r = Risk(id="r1", title="t", space="s", category="delivery",
             likelihood=5, impact=4, strategy="mitigated")
    assert r.score == 20
    assert r.severity == "critical"
