"""Check status map integrity"""

from grana.actions.base import ActionStatus


def test_status_names_and_values_match() -> None:
    """Validate names and values are the same"""
    assert all(status.name == status.value for status in ActionStatus)


def test_status_values_lengths() -> None:
    """Check status lengths as it's crucial for printer justification"""
    assert all(len(status.value) == 7 for status in ActionStatus)
