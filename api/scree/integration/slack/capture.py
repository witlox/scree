import time


class SlackDirectory:
    """Maps a Slack user id to a Keycloak/opaque principal (INV-ID-2). An unmapped
    Slack user resolves to None, and capture/link actions are refused — identity is
    never guessed or attributed. Spike: in-memory map."""

    def __init__(self, mapping: dict[str, str] | None = None) -> None:
        self._map = dict(mapping or {})

    def resolve(self, slack_user: str) -> str | None:
        return self._map.get(slack_user)


class CaptureRateLimiter:
    """Per-Slack-user sliding-window rate limit on captures (INV-SLACK-1: prevent
    emoji/slash spam/DoS). Spike: in-memory monotonic timestamps."""

    def __init__(self, limit: int = 5, window: float = 60.0) -> None:
        self._limit = limit
        self._window = window
        self._hits: dict[str, list[float]] = {}

    def allow(self, slack_user: str) -> bool:
        now = time.monotonic()
        recent = [t for t in self._hits.get(slack_user, []) if now - t < self._window]
        if len(recent) >= self._limit:
            self._hits[slack_user] = recent
            return False
        recent.append(now)
        self._hits[slack_user] = recent
        return True
