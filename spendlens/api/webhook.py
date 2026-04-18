from fastapi import APIRouter
from spendlens.models import Transaction
import reflex as rx

router = APIRouter()


@router.post("/api/transaction")
async def receive_transaction(data: dict):
    with rx.session() as session:
        txn = Transaction(
            datetime=data["datetime"],
            amount=data["amount"],
            merchant=data["merchant"],
            category=data.get("category", "uncategorized"),
            txn_type=data.get("txn_type", ""),
            source="live",
            is_flagged=data["amount"] > 5000,
        )
        session.add(txn)
        session.commit()
    return {"status": "ok", "flagged": txn.is_flagged}
