from __future__ import annotations

from fastapi import Depends
from fastapi import Request

from vistora.app.container import AppContainer
from vistora.services.credits import CreditLedger
from vistora.services.job_manager import JobManager
from vistora.services.profiles import ProfileStore
from vistora.services.telegram_ops import TelegramOpsService


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_ledger(container: AppContainer = Depends(get_container)) -> CreditLedger:
    return container.ledger


def get_jobs(container: AppContainer = Depends(get_container)) -> JobManager:
    return container.jobs


def get_profiles(container: AppContainer = Depends(get_container)) -> ProfileStore:
    return container.profiles


def get_tg_ops(container: AppContainer = Depends(get_container)) -> TelegramOpsService:
    return container.tg_ops
