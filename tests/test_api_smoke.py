from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

from vistora.app.main import create_app
from vistora.app.settings import Settings


def _build_test_app(tmp_path: pathlib.Path):
    runtime_dir = tmp_path / "runtime"
    settings = Settings(
        host="127.0.0.1",
        port=8585,
        runtime_dir=runtime_dir,
        ledger_path=runtime_dir / "credits_ledger.json",
        profiles_path=runtime_dir / "profiles.json",
    )
    return create_app(settings=settings)


def test_api_smoke_endpoints(tmp_path: pathlib.Path):
    app = _build_test_app(tmp_path)
    with TestClient(app) as client:
        index = client.get("/")
        assert index.status_code == 200

        web_asset = client.get("/web/app.js")
        assert web_asset.status_code == 200

        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["ok"] is True

        caps = client.get("/api/v1/system/capabilities")
        assert caps.status_code == 200
        assert "runners" in caps.json()

        models = client.get("/api/v1/models/catalog")
        assert models.status_code == 200
        assert len(models.json().get("cards", [])) > 0

        put_profile = client.put(
            "/api/v1/profiles/hq-fast",
            json={"settings": {"runner": "dry-run", "quality_tier": "high"}},
        )
        assert put_profile.status_code == 200

        create = client.post(
            "/api/v1/jobs",
            json={
                "input_path": "/tmp/in.mp4",
                "output_path": "/tmp/out.mp4",
                "user_id": "demo",
                "runner": "dry-run",
                "quality_tier": "high",
            },
        )
        assert create.status_code == 200
        job_id = create.json()["id"]

        listed = client.get("/api/v1/jobs")
        assert listed.status_code == 200
        assert any(job["id"] == job_id for job in listed.json()["jobs"])

        topup = client.post("/api/v1/credits/demo/topup", json={"amount": 10, "reason": "seed"})
        assert topup.status_code == 200
        assert topup.json()["ok"] is True

        tg_ping = client.post("/api/v1/tg/webhook", json={"event": "ping", "user_id": "demo", "payload": {}})
        assert tg_ping.status_code == 200
        assert tg_ping.json()["ok"] is True
