"""@api — the audit sink is hash-chained (#79 / INV-ID-3, AR-10): an intact log
verifies, and any tampering (altered field, reorder, or deletion) is detectable."""

from dataclasses import replace

from scree.access.audit import AuditSink


def _populated() -> AuditSink:
    sink = AuditSink()
    sink.record("rivera", "GET", "/docs", 200)
    sink.record("okafor", "POST", "/tickets", 200)
    sink.record(None, "GET", "/docs", 401)
    return sink


def test_intact_chain_verifies():
    assert _populated().verify() is True


def test_altered_entry_is_detected():
    sink = _populated()
    evts = sink.events()
    evts[1] = replace(evts[1], result=500)  # tamper a field, keep the (now-wrong) hashes
    tampered = AuditSink(_events=evts)
    assert tampered.verify() is False


def test_reorder_is_detected():
    sink = _populated()
    evts = sink.events()
    evts[0], evts[1] = evts[1], evts[0]
    assert AuditSink(_events=evts).verify() is False


def test_deletion_is_detected():
    sink = _populated()
    evts = sink.events()
    del evts[1]  # removing an entry breaks the prev_hash linkage of the next
    assert AuditSink(_events=evts).verify() is False
