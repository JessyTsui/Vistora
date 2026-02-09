from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field

from vistora.core import JobCreateRequest, JobListView, JobStatus, JobView, utc_now
from vistora.services.credits import CreditLedger
from vistora.services.model_catalog import resolve_models
from vistora.services.pathing import default_output_path
from vistora.services.pricing import estimate_credits
from vistora.services.runners import build_runner


@dataclass
class ManagedJob:
    id: str
    request: JobCreateRequest
    status: JobStatus = "queued"
    stage: str = "queued"
    progress: float = 0.0
    credits_reserved: int = 0
    error: str | None = None
    created_at: object = field(default_factory=utc_now)
    updated_at: object = field(default_factory=utc_now)

    def to_view(self) -> JobView:
        detector_model = self.request.detector_model or "unknown-detector"
        restorer_model = self.request.restorer_model or "unknown-restorer"
        return JobView(
            id=self.id,
            user_id=self.request.user_id,
            status=self.status,
            stage=self.stage,
            progress=self.progress,
            credits_reserved=self.credits_reserved,
            quality_tier=self.request.quality_tier,
            detector_model=detector_model,
            restorer_model=restorer_model,
            refiner_model=self.request.refiner_model,
            input_path=self.request.input_path,
            output_path=self.request.output_path,
            error=self.error,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class JobManager:
    def __init__(self, ledger: CreditLedger, enforce_credits: bool = False):
        self._ledger = ledger
        self._enforce_credits = enforce_credits
        self._jobs: dict[str, ManagedJob] = {}
        self._lock = threading.Lock()

    def start(self):
        # Serial manager has no background worker.
        return

    def stop(self):
        # Serial manager has no background worker.
        return

    def create_job(self, req: JobCreateRequest) -> JobView:
        detector_model, restorer_model, refiner_model = resolve_models(
            req.quality_tier,
            req.detector_model,
            req.restorer_model,
            req.refiner_model,
        )
        estimated_credits = req.estimated_credits or estimate_credits(req.duration_hint_seconds, req.quality_tier)
        output_path = req.output_path or default_output_path(req.input_path)
        resolved_req = req.model_copy(
            update={
                "detector_model": detector_model,
                "restorer_model": restorer_model,
                "refiner_model": refiner_model,
                "estimated_credits": estimated_credits,
                "output_path": output_path,
            }
        )
        job_id = uuid.uuid4().hex
        job = ManagedJob(
            id=job_id,
            request=resolved_req,
            status="running",
            stage="starting",
            progress=0.01,
        )
        with self._lock:
            self._jobs[job_id] = job
        self._execute_job(job_id)
        with self._lock:
            return self._jobs[job_id].to_view()

    def get_job(self, job_id: str) -> JobView | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_view() if job else None

    def list_jobs(self) -> JobListView:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return JobListView(jobs=[job.to_view() for job in jobs])

    def cancel_job(self, job_id: str) -> JobView | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.status in {"queued", "running"}:
                job.status = "canceled"
                job.stage = "canceled"
                job.updated_at = utc_now()
            return job.to_view()

    def _execute_job(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status == "canceled":
                return
            req = job.request

        try:
            if self._enforce_credits:
                reserve_txn = self._ledger.reserve(req.user_id, req.estimated_credits, ref_id=job_id)
                self._set_reserved(job_id, abs(reserve_txn.amount))
            runner = build_runner(req.runner)
            runner.run(req, on_stage=lambda stage, progress: self._set_stage(job_id, stage, progress))
        except Exception as exc:
            self._on_failure(job_id, str(exc))
        else:
            self._on_done(job_id)

    def _set_reserved(self, job_id: str, reserved: int):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.credits_reserved = reserved
            job.updated_at = utc_now()

    def _set_stage(self, job_id: str, stage: str, progress: float):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.stage = stage
            job.progress = max(0.0, min(1.0, progress))
            job.updated_at = utc_now()

    def _on_done(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "done"
            job.stage = "done"
            job.progress = 1.0
            job.updated_at = utc_now()

    def _on_failure(self, job_id: str, error: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.stage = "failed"
            job.error = error
            job.updated_at = utc_now()
            credits_reserved = job.credits_reserved
            user_id = job.request.user_id
        if credits_reserved > 0:
            # Refund outside lock.
            self._ledger.refund(user_id, credits_reserved, ref_id=job_id)
