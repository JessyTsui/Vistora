from __future__ import annotations

import os
import pathlib
from pathlib import Path

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
    input_file = tmp_path / "in.mp4"
    input_file.write_text("dummy")
    req = JobCreateRequest(
        input_path=str(input_file),
        output_path=None,
        user_id="u1",
        quality_tier="high",
        runner="dry-run",
        estimated_credits=None,
        options={"stage_sleep": 0},
    )
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        view = manager.create_job(req)
    finally:
        os.chdir(old_cwd)
    assert view.quality_tier == "high"
    assert view.detector_model
    assert view.restorer_model
    assert view.credits_reserved == 0
    assert view.output_path is not None
    output_path = Path(view.output_path)
    assert output_path.parent.name == "outputs"
    assert output_path.name.startswith("in_restored_")
