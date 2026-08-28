from __future__ import annotations

import pytest

from pathlib import Path

from fastapi.testclient import TestClient

from little_meals.api.app import create_app
from little_meals.config import Settings


@pytest.mark.requirement("REQ-000000037")
def test_enable_scheduler_false_by_default(client: TestClient):
    assert client.app.state.scheduler is None


@pytest.mark.requirement("REQ-000000037")
def test_enable_scheduler_starts_and_stops_a_background_scheduler(tmp_path: Path):
    settings = Settings(data_dir=tmp_path)
    app = create_app(settings=settings, enable_scheduler=True)

    assert app.state.scheduler is not None
    assert app.state.scheduler.running is False  # not started until lifespan startup

    with TestClient(app):
        assert app.state.scheduler.running is True

    assert app.state.scheduler.running is False
