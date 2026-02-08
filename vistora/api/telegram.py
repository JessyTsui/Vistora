from __future__ import annotations

from fastapi import APIRouter, Depends

from vistora.app.dependencies import get_tg_ops
from vistora.core import TgWebhookRequest
from vistora.services.telegram_ops import TelegramOpsService

router = APIRouter(prefix="/api/v1/tg", tags=["telegram"])


@router.post("/webhook")
def tg_webhook(req: TgWebhookRequest, tg_ops: TelegramOpsService = Depends(get_tg_ops)):
    return tg_ops.handle_webhook_event(req)
