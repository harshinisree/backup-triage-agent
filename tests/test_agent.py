import json

import pytest

from triage.agent import TriageAgent
from triage.llm import LLMUnavailable, validate
from triage.models import Incident


class GoodLLM:
    def complete(self, message, category, runbook):
        return {"summary": "Snapshot slow; retry off-peak.", "action": "retry_job"}


class DownLLM:
    def complete(self, *a):
        raise LLMUnavailable("no key")


@pytest.fixture
def audit_path(tmp_path):
    return tmp_path / "audit.jsonl"


def test_mutating_action_requires_approval(audit_path):
    agent = TriageAgent(llm=GoodLLM(), audit_path=audit_path)
    r = agent.triage(Incident("INC-1", "snapshot timeout exceeded window"))
    assert r.status == "pending_approval" and r.requires_approval and r.used_llm


def test_approval_executes_dry_run_and_audits(audit_path):
    agent = TriageAgent(llm=GoodLLM(), audit_path=audit_path)
    r = agent.triage(Incident("INC-1", "snapshot timeout exceeded window"))
    agent.approve(r, "harshini")
    assert r.status == "completed" and "executed_dry_run" in r.trace
    steps = [json.loads(line)["step"] for line in audit_path.read_text().splitlines()]
    assert steps[-2:] == ["approved", "executed_dry_run"]


def test_cannot_approve_twice(audit_path):
    agent = TriageAgent(llm=GoodLLM(), audit_path=audit_path)
    r = agent.triage(Incident("INC-1", "snapshot timeout"))
    agent.approve(r, "a")
    with pytest.raises(ValueError):
        agent.approve(r, "a")


def test_llm_failure_falls_back_safely(audit_path):
    agent = TriageAgent(llm=DownLLM(), audit_path=audit_path)
    r = agent.triage(Incident("INC-2", "401 token expired"))
    assert not r.used_llm and "llm_fallback" in r.trace
    assert r.proposed_action == "escalate_to_team" and r.summary


def test_unknown_is_ticket_only(audit_path):
    agent = TriageAgent(llm=DownLLM(), audit_path=audit_path)
    r = agent.triage(Incident("INC-3", "odd glitch"))
    assert r.status == "completed" and not r.requires_approval


def test_llm_output_validation_rejects_unsafe_action():
    with pytest.raises(ValueError):
        validate('{"summary": "x", "action": "delete_all_backups"}')
    with pytest.raises(ValueError):
        validate('{"summary": "", "action": "retry_job"}')


def test_cannot_reject_after_completion(audit_path):
    agent = TriageAgent(llm=GoodLLM(), audit_path=audit_path)
    r = agent.triage(Incident("INC-4", "snapshot timeout"))
    agent.approve(r, "a")
    with pytest.raises(ValueError):
        agent.reject(r, "b")
    assert r.status == "completed"


def test_llm_reply_without_text_falls_back(monkeypatch, audit_path):
    """A reply holding only non-text blocks must not crash triage."""
    import sys
    from types import SimpleNamespace

    from triage.llm import LLMClient

    reply = SimpleNamespace(content=[SimpleNamespace(type="thinking")])
    fake = SimpleNamespace(
        Anthropic=lambda: SimpleNamespace(messages=SimpleNamespace(create=lambda **k: reply))
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setitem(sys.modules, "anthropic", fake)

    with pytest.raises(ValueError):
        LLMClient().complete("snapshot timeout", "snapshot_timeout", "runbook")
    agent = TriageAgent(llm=LLMClient(), audit_path=audit_path)
    r = agent.triage(Incident("I", "snapshot timeout"))
    assert "llm_fallback" in r.trace
