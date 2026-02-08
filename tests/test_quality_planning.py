from __future__ import annotations

import pathlib

from vistora.core import JobCreateRequest
from vistora.services.job_manager import JobManager
from vistora.services.model_catalog import resolve_models
from vistora.services.pricing import estimate_credits
from vistora.services.credits import CreditLedger
from vistora.services.storage import JsonStore


def test_resolve_models_by_quality_tier():
    detector, restorer, refiner = resolve_models("high", None, None, None)
    assert detector
    assert restorer
    assert refiner is not None

    detector2, restorer2, refiner2 = resolve_models("balanced", "my-detector", None, None)
    assert detector2 == "my-detector"
    assert restorer2
    assert refiner2 is None


def test_estimate_credits_grows_with_quality():
    low = estimate_credits(duration_hint_seconds=180, quality_tier="balanced")
    high = estimate_credits(duration_hint_seconds=180, quality_tier="high")
    ultra = estimate_credits(duration_hint_seconds=180, quality_tier="ultra")
    assert low < high < ultra


def test_job_manager_autofills_models_and_credits(tmp_path: pathlib.Path):
    ledger = CreditLedger(JsonStore(tmp_path / "ledger.json"))
    manager = JobManager(ledger=ledger)
    req = JobCreateRequest(
        input_path="/tmp/in.mp4",
        output_path="/tmp/out.mp4",
        user_id="u1",
        quality_tier="high",
        estimated_credits=None,
    )
    view = manager.create_job(req)
    assert view.quality_tier == "high"
    assert view.detector_model
    assert view.restorer_model
    assert view.credits_reserved == 0
