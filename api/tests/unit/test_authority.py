"""TDD — validates the architected authority component (enforcement of INV-ACC):
a principal may read a doc only if its Space is in their readable set."""

from scree.access.authority import Authority
from scree.knowledge.models import Doc


def _doc(space: str) -> Doc:
    return Doc(id="doc-x", title="t", space=space, body="b")


def test_can_read_only_in_readable_space():
    auth = Authority({"rivera": {"platform/handbook"}})
    assert auth.can_read("rivera", _doc("platform/handbook")) is True
    assert auth.can_read("rivera", _doc("org/risk-portfolio")) is False


def test_unknown_principal_reads_nothing():
    auth = Authority({})
    assert auth.can_read("ghost", _doc("platform/handbook")) is False
