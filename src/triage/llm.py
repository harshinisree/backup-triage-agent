"""LLM wrapper. Returns validated JSON or raises; the agent falls back safely."""
import json
import os

ALLOWED_ACTIONS = {"retry_job", "escalate_to_team", "open_ticket", "none"}
MODEL = os.getenv("TRIAGE_MODEL", "claude-sonnet-5-5")

PROMPT = """You are an incident triage assistant. Using ONLY the runbook excerpt, respond with
JSON: {{"summary": "<2 sentences>", "action": "<one of {actions}>"}}.
Incident: {message}
Category: {category}
Runbook:
{runbook}"""


class LLMUnavailable(Exception):
    pass


def validate(raw: str) -> dict:
    data = json.loads(raw)
    if not isinstance(data.get("summary"), str) or not data["summary"].strip():
        raise ValueError("missing summary")
    if data.get("action") not in ALLOWED_ACTIONS:
        raise ValueError(f"action not allowed: {data.get('action')}")
    return {"summary": data["summary"].strip(), "action": data["action"]}


class LLMClient:
    def complete(self, message: str, category: str, runbook: str) -> dict:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise LLMUnavailable("ANTHROPIC_API_KEY not set")
        try:
            import anthropic
        except ImportError as e:
            raise LLMUnavailable("anthropic package not installed") from e
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": PROMPT.format(
                    actions=sorted(ALLOWED_ACTIONS), message=message,
                    category=category, runbook=runbook[:2000],
                ),
            }],
        )
        return validate(resp.content[0].text)
