from __future__ import annotations

from fastapi import APIRouter, Depends

from vistora.app.dependencies import get_ledger
from vistora.core import CreditBalanceView, CreditTopupRequest
from vistora.services.credits import CreditLedger

router = APIRouter(prefix="/api/v1/credits", tags=["credits"])


@router.get("/{user_id}", response_model=CreditBalanceView)
def get_balance(user_id: str, ledger: CreditLedger = Depends(get_ledger)):
    return ledger.get_balance(user_id)


@router.post("/{user_id}/topup")
def topup(user_id: str, req: CreditTopupRequest, ledger: CreditLedger = Depends(get_ledger)):
    txn = ledger.topup(user_id=user_id, amount=req.amount, reason=req.reason)
    return {"ok": True, "transaction": txn, "balance": ledger.get_balance(user_id)}


@router.get("/{user_id}/transactions")
def list_transactions(user_id: str, ledger: CreditLedger = Depends(get_ledger)):
    return {"transactions": ledger.list_transactions(user_id=user_id)}
