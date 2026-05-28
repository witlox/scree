from .models import Risk


def fires_critical_webhook(risk: Risk) -> bool:
    """INV-IX-1 / OQ-A-013: a risk fires the near-real-time indexing webhook when
    its *category* is security or compliance — NOT based on the severity band."""
    return risk.category in {"security", "compliance"}
