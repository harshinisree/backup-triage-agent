# Backup Incident Triage Agent

![CI](https://github.com/harshinisree/backup-triage-agent/actions/workflows/ci.yml/badge.svg)

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
| Tests, lint, type checks, CI, Docker | `tests/`, `pyproject.toml`, `.github/workflows/ci.yml`, `Dockerfile` |

## Safeguards
- LLM may only choose from an allowlist of actions; anything else is rejected.
- LLM down or invalid output: deterministic template fallback, triage never blocks.
- Mutating actions (`retry_job`, `escalate_to_team`) stay `pending_approval` until a named approver acts.
- Append-only audit trail of classification, retrieval, LLM use/fallback, approval and execution.

## Run
```bash
pip install -r requirements-dev.txt
export PYTHONPATH=src
ruff check . && mypy src && pytest -q
python -m triage.cli triage "Snapshot exceeded window, job timeout" --host srv-03
python -m triage.cli anomalies data/sample_jobs.csv
python -m triage.api            # development server at http://localhost:5000
```
Optional LLM: `export ANTHROPIC_API_KEY=...` (works without it via fallback).

```bash
curl -X POST localhost:5000/triage -H 'Content-Type: application/json' \
  -d '{"id":"INC-1","message":"401 token expired","host":"srv-02"}'
curl -X POST localhost:5000/incidents/INC-1/approve -H 'Content-Type: application/json' \
  -d '{"approver":"your.name"}'
```
Docker (served by gunicorn, as a non-root user): `docker build -t triage . && docker run -p 5000:5000 triage`

## Example output
Real output with no API key, so the summary comes from the safe fallback. A retry changes the backup
system, so it waits for approval:

```json
{"incident_id": "INC-1", "category": "snapshot_timeout", "confidence": 1.0,
 "runbook": "snapshot_timeout", "proposed_action": "retry_job",
 "requires_approval": true, "status": "pending_approval", "used_llm": false,
 "summary": "[snapshot_timeout] on srv-03: Snapshot exceeded window, job timeout. See runbook 'snapshot_timeout'.",
 "trace": ["classified", "retrieved", "llm_fallback", "proposed"]}
```

After `POST /incidents/INC-1/approve` the status becomes `completed` and the trace ends with
`"approved", "executed_dry_run"`. Approving or rejecting it again returns `409`.

Anomaly detection on the sample history flags the injected failure spike:

```
      date  total  failed  fail_rate  anomaly
2026-09-30      8       5      0.625     True
```

## Quality checks
CI runs on every push: ruff (lint and type-hint rules), mypy, 18 pytest tests, and a Docker build
that must answer `/healthz`. Dependencies are pinned in `requirements.txt` (runtime) and
`requirements-dev.txt` (tests and checks).

## Limitations / next steps
Rule-based classifier (LLM classifier is a next step); TF-IDF retrieval (embeddings next);
in-memory incident store (swap for MySQL); executor is a stub for real backup-platform APIs.
