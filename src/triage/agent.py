"""Multi-step triage workflow with approval gate, fallback, and audit trail.

ingest -> classify -> retrieve runbook -> summarize (LLM, validated) ->
propose action -> approval gate -> execute (dry-run) -> audit
"""
from pathlib import Path

from . import audit
from .classifier import classify
from .llm import LLMClient
from .models import Incident, TriageResult
from .retriever import RunbookRetriever

# Default action per category when the LLM is unavailable or returns bad output.
DEFAULT_ACTION = {
    "auth_failure": "escalate_to_team",
    "storage_full": "escalate_to_team",
    "agent_unreachable": "escalate_to_team",
    "snapshot_timeout": "retry_job",
    "unknown": "open_ticket",
}
# Only low-risk, non-mutating actions run without human approval.
AUTO_APPROVED = {"open_ticket", "none"}


class TriageAgent:
    def __init__(self, retriever=None, llm=None, audit_path: Path | None = None):
        self.retriever = retriever or RunbookRetriever()
        self.llm = llm or LLMClient()
        self.audit_path = audit_path

    def _log(self, result: TriageResult, step: str, detail: dict) -> None:
        result.trace.append(step)
        audit.log(result.incident_id, step, detail, self.audit_path)

    def triage(self, incident: Incident) -> TriageResult:
        category, conf = classify(incident.message)
        name, score, text = self.retriever.search(f"{category} {incident.message}")[0]
        result = TriageResult(
            incident_id=incident.id, category=category, confidence=conf, runbook=name,
            summary="", proposed_action=DEFAULT_ACTION[category],
            requires_approval=False, status="new",
        )
        self._log(result, "classified", {"category": category, "confidence": conf})
        self._log(result, "retrieved", {"runbook": name, "score": round(score, 3)})

        try:
            out = self.llm.complete(incident.message, category, text)
            result.summary = out["summary"]
            result.proposed_action = out["action"]
            result.used_llm = True
            self._log(result, "llm_summary", {"action": out["action"]})
        except Exception as e:  # safe failure: never block triage on the LLM
            result.summary = (
                f"[{category}] on {incident.host}: {incident.message[:120]}. "
                f"See runbook '{name}'."
            )
            self._log(result, "llm_fallback", {"reason": type(e).__name__})

        result.requires_approval = result.proposed_action not in AUTO_APPROVED
        if result.requires_approval:
            result.status = "pending_approval"
        else:
            result.status = "completed"
        self._log(result, "proposed", {"action": result.proposed_action,
                                        "requires_approval": result.requires_approval})
        return result

    def approve(self, result: TriageResult, approver: str) -> TriageResult:
        if result.status != "pending_approval":
            raise ValueError(f"cannot approve incident in status {result.status}")
        self._log(result, "approved", {"by": approver})
        # Dry-run executor: no real backup-system calls are made in this demo.
        self._log(result, "executed_dry_run", {"action": result.proposed_action})
        result.status = "completed"
        return result

    def reject(self, result: TriageResult, approver: str) -> TriageResult:
        self._log(result, "rejected", {"by": approver})
        result.status = "rejected"
        return result
