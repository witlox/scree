from dataclasses import dataclass


@dataclass
class Availability:
    """Liveness of the upstream dependencies the Gateway degrades around (DD-003/
    DD-019). When GitLab is down, reads from the local clone still serve but writes
    are refused with a clear error (never silently dropped, INV-DEG-1); when O365 is
    down, inbound email-driven creation fails visibly (INV-DEG-2).

    G12-03: these flags are set externally. A production deployment must wire a
    health probe / circuit-breaker (on GitLab & Graph call failures) to update them
    — otherwise degradation never engages. The spike flips them in tests; the probe
    is a deploy concern."""

    gitlab_up: bool = True
    email_up: bool = True
