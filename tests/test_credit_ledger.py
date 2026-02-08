from __future__ import annotations

import pathlib

from vistora.services.credits import CreditLedger
from vistora.services.storage import JsonStore


def test_credit_lifecycle(tmp_path: pathlib.Path):
    ledger = CreditLedger(JsonStore(tmp_path / "ledger.json"))

    assert ledger.get_balance("u1").balance == 0
    ledger.topup("u1", 10, "seed")
    assert ledger.get_balance("u1").balance == 10

    reserve_txn = ledger.reserve("u1", 4, ref_id="j1")
    assert reserve_txn.amount == -4
    assert ledger.get_balance("u1").balance == 6

    refund_txn = ledger.refund("u1", 2, ref_id="j1")
    assert refund_txn.amount == 2
    assert ledger.get_balance("u1").balance == 8


def test_insufficient_credit(tmp_path: pathlib.Path):
    ledger = CreditLedger(JsonStore(tmp_path / "ledger.json"))
    ledger.topup("u1", 1, "seed")
    try:
        ledger.reserve("u1", 3, ref_id="j1")
        assert False, "reserve should fail"
    except ValueError as exc:
        assert "insufficient credits" in str(exc)
