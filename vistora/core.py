from __future__ import annotations

from datetime import datetime, UTC
from typing import Literal

from pydantic import BaseModel, Field, model_validator

JobStatus = Literal["queued", "running", "done", "failed", "canceled"]
QualityTier = Literal["balanced", "high", "ultra"]


class JobCreateRequest(BaseModel):
    input_path: str
    output_path: str | None = None
    user_id: str = "anonymous"
    profile_name: str | None = None
    estimated_credits: int | None = None
    duration_hint_seconds: int | None = None
    runner: Literal["auto", "dry-run", "lada-cli"] = "auto"
    quality_tier: QualityTier = "ultra"
    detector_model: str | None = None
    restorer_model: str | None = None
    refiner_model: str | None = None
    options: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_values(self):
        if self.estimated_credits is not None and self.estimated_credits < 1:
            raise ValueError("estimated_credits must be >= 1")
        if self.duration_hint_seconds is not None and self.duration_hint_seconds < 1:
            raise ValueError("duration_hint_seconds must be >= 1")
        return self


class JobView(BaseModel):
    id: str
    user_id: str
    status: JobStatus
    stage: str
    progress: float
    credits_reserved: int
    quality_tier: QualityTier
    detector_model: str
    restorer_model: str
    refiner_model: str | None = None
    input_path: str
    output_path: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class JobListView(BaseModel):
    jobs: list[JobView]


class CreditTopupRequest(BaseModel):
    amount: int
    reason: str = "manual_topup"

    @model_validator(mode="after")
    def validate_values(self):
        if self.amount < 1:
            raise ValueError("amount must be >= 1")
        return self


class CreditBalanceView(BaseModel):
    user_id: str
    balance: int


class CreditTxnView(BaseModel):
    id: str
    user_id: str
    amount: int
    kind: Literal["topup", "reserve", "refund"]
    reason: str
    ref_id: str | None = None
    created_at: datetime


class ProfileUpdateRequest(BaseModel):
    settings: dict[str, str | int | float | bool | None]


class ProfileView(BaseModel):
    name: str
    settings: dict[str, str | int | float | bool | None]


class ProfileListView(BaseModel):
    profiles: list[ProfileView]


class SystemCapabilityView(BaseModel):
    devices: list[str]
    runners: list[str]
    quality_tiers: list[QualityTier]
    defaults: dict[str, str | int | float | bool]


class ModelCardView(BaseModel):
    id: str
    role: Literal["detector", "restorer", "refiner"]
    family: str
    objective: Literal["quality-first", "speed-first", "balanced"]
    maturity: Literal["baseline", "candidate"]
    notes: str


class QualityPresetView(BaseModel):
    tier: QualityTier
    detector_model: str
    restorer_model: str
    refiner_model: str | None = None
    notes: str


class ModelCatalogView(BaseModel):
    cards: list[ModelCardView]
    quality_presets: list[QualityPresetView]


class TgWebhookRequest(BaseModel):
    event: str
    user_id: str
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


def utc_now() -> datetime:
    return datetime.now(UTC)
