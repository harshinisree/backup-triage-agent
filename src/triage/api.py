from flask import Flask, Response, jsonify, request

from .agent import TriageAgent
from .models import Incident, TriageResult

Reply = Response | tuple[Response, int] | dict[str, str]


def create_app(agent: TriageAgent | None = None) -> Flask:
    app = Flask(__name__)
    ag = agent or TriageAgent()
    store: dict[str, TriageResult] = {}

    @app.get("/healthz")
    def health() -> Reply:
        return {"status": "ok"}

    @app.post("/triage")
    def triage() -> Reply:
        body = request.get_json(silent=True) or {}
        if not body.get("id") or not body.get("message"):
            return jsonify(error="id and message are required"), 400
        result = ag.triage(Incident(body["id"], body["message"], body.get("host", "unknown")))
        store[result.incident_id] = result
        return jsonify(result.to_dict()), 201

    @app.get("/incidents/<iid>")
    def get_incident(iid: str) -> Reply:
        if iid not in store:
            return jsonify(error="not found"), 404
        return jsonify(store[iid].to_dict())

    @app.post("/incidents/<iid>/<decision>")
    def decide(iid: str, decision: str) -> Reply:
        if iid not in store:
            return jsonify(error="not found"), 404
        approver = (request.get_json(silent=True) or {}).get("approver")
        if not approver:
            return jsonify(error="approver is required"), 400
        try:
            if decision == "approve":
                ag.approve(store[iid], approver)
            elif decision == "reject":
                ag.reject(store[iid], approver)
            else:
                return jsonify(error="decision must be approve or reject"), 400
        except ValueError as e:
            return jsonify(error=str(e)), 409
        return jsonify(store[iid].to_dict())

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
