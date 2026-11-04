import pytest

from triage.classifier import classify


@pytest.mark.parametrize("msg,expected", [
    ("Snapshot exceeded window, job timeout", "snapshot_timeout"),
    ("401 token expired for service account", "auth_failure"),
    ("No space left on archival target, quota exceeded", "storage_full"),
    ("Agent unreachable: connection refused", "agent_unreachable"),
    ("something weird happened", "unknown"),
])
def test_classify(msg, expected):
    assert classify(msg)[0] == expected
