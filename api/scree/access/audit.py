from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuditEvent:
    principal: str | None
    action: str  # HTTP method
    resource: str  # request path
    result: int  # status code


@dataclass
class AuditSink:
    """Append-only audit of Gateway actions (INV-ID-3). Spike: in-memory; the
    real sink is hash-chained / WORM with retention (AR-10)."""

    _events: list[AuditEvent] = field(default_factory=list)

    def record(self, principal: str | None, action: str, resource: str, result: int) -> None:
        self._events.append(AuditEvent(principal, action, resource, result))

    def events(self) -> list[AuditEvent]:
        return list(self._events)
