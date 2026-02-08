from __future__ import annotations

from vistora.core import TgWebhookRequest
from vistora.services.credits import CreditLedger


class TelegramOpsService:
    """
    Lightweight webhook handler to support early Telegram growth loops:
    - topup credits
    - query balance
    - request job creation (handled by caller)
    """

    def __init__(self, ledger: CreditLedger):
        self._ledger = ledger

    def handle_webhook_event(self, req: TgWebhookRequest) -> dict:
        if req.event == "topup":
            amount = int(req.payload.get("amount", 0))
            reason = str(req.payload.get("reason", "tg_topup"))
            txn = self._ledger.topup(req.user_id, amount, reason)
            return {"ok": True, "event": req.event, "transaction_id": txn.id}

        if req.event == "balance":
            balance = self._ledger.get_balance(req.user_id)
            return {"ok": True, "event": req.event, "balance": balance.balance}

        if req.event == "ping":
            return {"ok": True, "event": req.event, "message": "pong"}

        return {"ok": False, "event": req.event, "error": "unsupported_event"}
