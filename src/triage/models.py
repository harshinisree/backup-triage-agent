from dataclasses import asdict, dataclass, field


@dataclass
class Incident:
    id: str
    message: str
    host: str = "unknown"


@dataclass
class TriageResult:
    incident_id: str
    category: str
    confidence: float
    runbook: str
    summary: str
    proposed_action: str
    requires_approval: bool
    status: str
    used_llm: bool = False
    trace: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
