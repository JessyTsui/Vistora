from __future__ import annotations

import threading
import uuid

from vistora.core import CreditBalanceView, CreditTxnView, utc_now
from vistora.services.storage import JsonStore


class CreditLedger:
    def __init__(self, store: JsonStore):
        self._store = store
        self._lock = threading.Lock()
        payload = self._store.load_dict()
        self._balances: dict[str, int] = payload.get("balances", {}) if isinstance(payload.get("balances"), dict) else {}
        self._txns: list[dict] = payload.get("transactions", []) if isinstance(payload.get("transactions"), list) else []

    def get_balance(self, user_id: str) -> CreditBalanceView:
        with self._lock:
            return CreditBalanceView(user_id=user_id, balance=int(self._balances.get(user_id, 0)))

    def topup(self, user_id: str, amount: int, reason: str) -> CreditTxnView:
        if amount < 1:
            raise ValueError("topup amount must be >= 1")
        with self._lock:
            self._balances[user_id] = int(self._balances.get(user_id, 0)) + amount
            txn = self._append_txn(user_id=user_id, amount=amount, kind="topup", reason=reason, ref_id=None)
            self._persist()
            return txn

    def reserve(self, user_id: str, amount: int, ref_id: str) -> CreditTxnView:
        if amount < 1:
            raise ValueError("reserve amount must be >= 1")
        with self._lock:
            balance = int(self._balances.get(user_id, 0))
            if balance < amount:
                raise ValueError(f"insufficient credits: balance={balance}, required={amount}")
            self._balances[user_id] = balance - amount
            txn = self._append_txn(user_id=user_id, amount=-amount, kind="reserve", reason="job_reserve", ref_id=ref_id)
            self._persist()
            return txn

    def refund(self, user_id: str, amount: int, ref_id: str) -> CreditTxnView:
        if amount < 1:
            raise ValueError("refund amount must be >= 1")
        with self._lock:
            self._balances[user_id] = int(self._balances.get(user_id, 0)) + amount
            txn = self._append_txn(user_id=user_id, amount=amount, kind="refund", reason="job_refund", ref_id=ref_id)
            self._persist()
            return txn

    def list_transactions(self, user_id: str | None = None) -> list[CreditTxnView]:
        with self._lock:
            result = []
            for raw in self._txns:
                if user_id and raw.get("user_id") != user_id:
                    continue
                result.append(CreditTxnView(**raw))
            return result

    def _append_txn(self, user_id: str, amount: int, kind: str, reason: str, ref_id: str | None) -> CreditTxnView:
        raw = {
            "id": uuid.uuid4().hex,
            "user_id": user_id,
            "amount": amount,
            "kind": kind,
            "reason": reason,
            "ref_id": ref_id,
            "created_at": utc_now(),
        }
        txn = CreditTxnView(**raw)
        self._txns.append(txn.model_dump(mode="json"))
        return txn

    def _persist(self):
        self._store.save_dict({"balances": self._balances, "transactions": self._txns})
