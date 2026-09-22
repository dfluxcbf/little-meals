"""little_meals/incident_reporter.py is a vendored copy of little-workshop's
own reporter (tools/incident_reporter.py there) — an unhandled exception from
any route is reported to little-workshop's Agentic Development pillar as an
incident awaiting the user's confirmation, never dispatched on its own."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from little_meals import incident_reporter as ir


def test_report_incident_is_silent_when_the_socket_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("LITTLE_WORKSHOP_AGENT_SOCKET", str(tmp_path / "nope.sock"))
    ir.report_incident(project_id="little-meals", context="ctx", exc=ValueError("boom"))  # must not raise


def test_no_auto_incident_suppresses_reporting(tmp_path, monkeypatch):
    socket_path = tmp_path / "agent.sock"
    socket_path.touch()
    monkeypatch.setenv("LITTLE_WORKSHOP_AGENT_SOCKET", str(socket_path))
    calls = []
    monkeypatch.setattr(ir.httpx, "Client", lambda **kw: calls.append(1))
    with ir.no_auto_incident():
        ir.report_incident(project_id="little-meals", context="ctx", exc=ValueError("boom"))
    assert calls == []


def test_middleware_reports_and_still_lets_the_exception_propagate(monkeypatch):
    reported = []
    monkeypatch.setattr(ir, "report_incident", lambda **kw: reported.append(kw))
    app = FastAPI()
    ir.install_incident_reporting(app, project_id="little-meals")

    @app.get("/boom")
    def boom():
        raise ValueError("kaboom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    assert reported[0]["project_id"] == "little-meals" and reported[0]["context"] == "GET /boom"


def test_the_real_app_installs_incident_reporting():
    from little_meals.api.app import create_app
    from little_meals.config import Settings
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(settings=Settings(data_dir=Path(tmp)))
        assert any("IncidentReportingMiddleware" in str(m.cls) for m in app.user_middleware)
