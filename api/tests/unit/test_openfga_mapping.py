"""Unit — OpenFGA id mapping (domain id <-> typed id). Runs in CI."""

from scree.access.openfga import fga_object, fga_user, strip_type


def test_user_and_object_prefixing():
    assert fga_user("cust-okafor") == "user:cust-okafor"
    assert fga_object("ticket-1") == "ticket:ticket-1"


def test_strip_type_roundtrips_object():
    assert strip_type(fga_object("ticket-1")) == "ticket-1"
    assert strip_type("ticket:ticket-9") == "ticket-9"
