from __future__ import annotations

from dataclasses import dataclass

from vistora.app.settings import Settings, load_settings
from vistora.services.credits import CreditLedger
from vistora.services.job_manager import JobManager
from vistora.services.profiles import ProfileStore
from vistora.services.storage import JsonStore
from vistora.services.telegram_ops import TelegramOpsService


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    ledger: CreditLedger
    profiles: ProfileStore
    jobs: JobManager
    tg_ops: TelegramOpsService


def build_container(settings: Settings | None = None) -> AppContainer:
    resolved = settings or load_settings()
    resolved.runtime_dir.mkdir(parents=True, exist_ok=True)

    ledger = CreditLedger(JsonStore(resolved.ledger_path))
    if resolved.bootstrap_credit_amount > 0:
        current = ledger.get_balance(resolved.bootstrap_credit_user).balance
        if current < resolved.bootstrap_credit_amount:
            ledger.topup(
                user_id=resolved.bootstrap_credit_user,
                amount=resolved.bootstrap_credit_amount - current,
                reason="bootstrap_credit",
            )
    profiles = ProfileStore(JsonStore(resolved.profiles_path))
    jobs = JobManager(ledger=ledger, enforce_credits=resolved.enforce_credits)
    tg_ops = TelegramOpsService(ledger=ledger)

    return AppContainer(
        settings=resolved,
        ledger=ledger,
        profiles=profiles,
        jobs=jobs,
        tg_ops=tg_ops,
    )
