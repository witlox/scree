"""TDD — critical-webhook trigger (INV-IX-1, category-driven) and escalation
(INV-LC-4 / DD-004)."""

from scree.risk.escalation import escalate
from scree.risk.models import Risk
from scree.risk.triggers import fires_critical_webhook


def _risk(category, likelihood=1, impact=1, space="platform/handbook") -> Risk:
    return Risk(id="risk-1", title="t", space=space, category=category,
                likelihood=likelihood, impact=impact, strategy="mitigated")


def test_security_category_fires_webhook():
    assert fires_critical_webhook(_risk("security")) is True


def test_compliance_category_fires_webhook():
    assert fires_critical_webhook(_risk("compliance")) is True


def test_high_score_delivery_risk_does_not_fire():
    # INV-IX-1: critical is category-driven, NOT severity. A delivery risk with
    # the maximum score (severity "critical") must NOT fire the webhook.
    risk = _risk("delivery", likelihood=5, impact=4)
    assert risk.severity == "critical"
    assert fires_critical_webhook(risk) is False


def test_escalation_creates_org_duplicate_with_crossref():
    original = _risk("strategic", space="platform/handbook")
    org = escalate(original, "org/risk-portfolio", "risk-org-7")
    assert org.space == "org/risk-portfolio"
    assert org.escalated_from == original.id
    assert org.id == "risk-org-7"
    # original is untouched
    assert original.space == "platform/handbook"
    assert original.escalated_from is None
