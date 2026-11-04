# Backup Incident Triage Agent

Agentic workflow that triages backup-job failures: classify, retrieve the matching runbook (RAG),
draft a summary with an LLM, propose a remediation, and **require human approval** before any
mutating action. Every step is written to an audit log. Also includes anomaly detection on job history.

> Built from my experience in backup operations and incident management. All data and runbooks
> in this repo are **synthetic**; no employer or client data is used. The executor is a dry run.

## Workflow
```
incident -> classify (rules) -> retrieve runbook (TF-IDF) -> LLM summary + action (JSON, validated)
         -> approval gate (mutating actions) -> dry-run execute -> audit log (JSONL)
```
| Requirement | Where |
|---|---|
| Multi-step agent, state, approvals, fallback | `src/triage/agent.py` |
| LLM output validation + action allowlist | `src/triage/llm.py` |
| Retrieval over runbooks | `src/triage/retriever.py` |
| Anomaly detection (pandas, scikit-learn) | `src/triage/anomaly.py` |
| REST API (Flask) | `src/triage/api.py` |
| Audit logging | `src/triage/audit.py` |
| Tests, lint, CI, Docker | `tests/`, `pyproject.toml`, `.github/workflows/ci.yml`, `Dockerfile` |

## Safeguards
- LLM may only choose from an allowlist of actions; anything else is rejected.
- LLM down or invalid output: deterministic template fallback, triage never blocks.
- Mutating actions (`retry_job`, `escalate_to_team`) stay `pending_approval` until a named approver acts.
- Append-only audit trail of classification, retrieval, LLM use/fallback, approval and execution.

## Run
```bash
pip install -r requirements.txt
export PYTHONPATH=src
pytest -q && ruff check .
python -m triage.cli triage "Snapshot exceeded window, job timeout" --host srv-03
python -m triage.cli anomalies data/sample_jobs.csv
python -m triage.api            # http://localhost:5000
```
Optional LLM: `export ANTHROPIC_API_KEY=...` (works without it via fallback).

```bash
curl -X POST localhost:5000/triage -H 'Content-Type: application/json' \
  -d '{"id":"INC-1","message":"401 token expired","host":"srv-02"}'
curl -X POST localhost:5000/incidents/INC-1/approve -H 'Content-Type: application/json' \
  -d '{"approver":"your.name"}'
```
Docker: `docker build -t triage . && docker run -p 5000:5000 triage`

## Limitations / next steps
Rule-based classifier (LLM classifier is a next step); TF-IDF retrieval (embeddings next);
in-memory incident store (swap for MySQL); executor is a stub for real backup-platform APIs.
