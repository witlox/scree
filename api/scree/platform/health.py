from dataclasses import dataclass


@dataclass
class Availability:
    """Liveness of the upstream dependencies the Gateway degrades around (DD-003/
    DD-019). When GitLab is down, reads from the local clone still serve but writes
    are refused with a clear error (never silently dropped, INV-DEG-1); when O365 is
    down, inbound email-driven creation fails visibly (INV-DEG-2). A real probe
    updates these; the spike flips them in tests."""

    gitlab_up: bool = True
    email_up: bool = True
