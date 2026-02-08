from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from vistora.app.dependencies import get_jobs, get_profiles
from vistora.core import JobCreateRequest, JobListView, JobView
from vistora.services.job_manager import JobManager
from vistora.services.profiles import ProfileStore

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _merge_request_with_profile(req: JobCreateRequest, profile_settings: dict) -> JobCreateRequest:
    req_payload = req.model_dump()
    merged_req = req_payload.copy()

    profile_options = profile_settings.get("options", {})
    if isinstance(profile_options, dict):
        merged_req["options"] = profile_options.copy()

    for key, value in profile_settings.items():
        if key == "options":
            continue
        if key in JobCreateRequest.model_fields:
            merged_req[key] = value

    # Explicit request values always win over profile defaults.
    for key in req.model_fields_set:
        merged_req[key] = req_payload[key]

    merged_req["options"] = {**(merged_req.get("options", {}) or {}), **req.options}
    return JobCreateRequest(**merged_req)


@router.post("", response_model=JobView)
def create_job(
    req: JobCreateRequest,
    jobs: JobManager = Depends(get_jobs),
    profiles: ProfileStore = Depends(get_profiles),
):
    if req.profile_name:
        profile = profiles.get_profile(req.profile_name)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"profile not found: {req.profile_name}")
        req = _merge_request_with_profile(req, profile.settings)
    return jobs.create_job(req)


@router.get("", response_model=JobListView)
def list_jobs(jobs: JobManager = Depends(get_jobs)):
    return jobs.list_jobs()


@router.get("/{job_id}", response_model=JobView)
def get_job(job_id: str, jobs: JobManager = Depends(get_jobs)):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/{job_id}/cancel", response_model=JobView)
def cancel_job(job_id: str, jobs: JobManager = Depends(get_jobs)):
    job = jobs.cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
