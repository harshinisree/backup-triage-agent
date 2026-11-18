import pandas as pd
import pytest

from triage.agent import TriageAgent
from triage.anomaly import detect
from triage.api import create_app
from triage.retriever import RunbookRetriever


def test_retriever_finds_right_runbook():
    name, score, _ = RunbookRetriever().search("storage_full no space left quota")[0]
    assert name == "storage_full" and score > 0


def test_anomaly_flags_injected_spike():
    df = pd.read_csv("data/sample_jobs.csv")
    assert "2026-09-30" in set(detect(df)["date"])


class DownLLM:
    def complete(self, *a):
        raise RuntimeError


@pytest.fixture
def client(tmp_path):
    return create_app(TriageAgent(llm=DownLLM(), audit_path=tmp_path / "a.jsonl")).test_client()


def test_api_flow(client):
    r = client.post("/triage", json={"id": "I-1", "message": "snapshot timeout exceeded window"})
    assert r.status_code == 201 and r.json["status"] == "pending_approval"
    assert client.post("/incidents/I-1/approve", json={}).status_code == 400
    ok = client.post("/incidents/I-1/approve", json={"approver": "harshini"})
    assert ok.json["status"] == "completed"
    assert client.post("/incidents/I-1/approve", json={"approver": "x"}).status_code == 409


def test_api_validation(client):
    assert client.post("/triage", json={"id": "x"}).status_code == 400
    assert client.get("/incidents/nope").status_code == 404


def test_api_reject_after_approval_returns_409(client):
    client.post("/triage", json={"id": "I-2", "message": "snapshot timeout exceeded window"})
    client.post("/incidents/I-2/approve", json={"approver": "harshini"})
    r = client.post("/incidents/I-2/reject", json={"approver": "x"})
    assert r.status_code == 409 and client.get("/incidents/I-2").json["status"] == "completed"
