"""TDD — ticket transition legality (INV-LC-1)."""

import pytest

from scree.servicedesk.lifecycle import IllegalTransition, transition


@pytest.mark.parametrize(
    "current,target",
    [("open", "resolved"), ("resolved", "closed"), ("resolved", "open"), ("closed", "open")],
)
def test_legal_transitions(current, target):
    assert transition(current, target) == target


@pytest.mark.parametrize("current,target", [("open", "closed"), ("closed", "resolved")])
def test_illegal_transitions_rejected(current, target):
    with pytest.raises(IllegalTransition):
        transition(current, target)
