from dataclasses import replace

from .models import Risk


def escalate(risk: Risk, org_space: str, new_id: str) -> Risk:
    """Escalation = explicit duplication into an org Space with a cross-reference
    back; the original is left in place (DD-004 / INV-LC-4)."""
    return replace(risk, id=new_id, space=org_space, escalated_from=risk.id)
