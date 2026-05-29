"""Binds canonical degradation.feature for traceability. Every scenario is @contract
(graceful degradation needs a real GitLab clone / outage), so all are skipped here and
run in the testcontainers tier; INV-DEG-1/2 are exercised in test_degradation*.py."""

from pytest_bdd import scenarios

scenarios("degradation.feature")
