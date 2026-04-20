from fastapi import APIRouter
from spendlens.models import Transaction
from fastapi.responses import StreamingResponse
import reflex as rx
import csv
import io
from datetime import datetime

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


@router.get("/api/export/transactions/csv")
async def export_transactions_csv():
    """Export all transactions to CSV format."""
    with rx.session() as session:
        transactions = session.query(Transaction).all()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=['Date', 'Time', 'Merchant', 'Amount', 'Category', 'Type', 'Source', 'Is Routine', 'Is Flagged', 'Notes']
    )
    writer.writeheader()
    
    for txn in transactions:
        writer.writerow({
            'Date': txn.datetime.strftime('%Y-%m-%d'),
            'Time': txn.datetime.strftime('%H:%M:%S'),
            'Merchant': txn.merchant,
            'Amount': f"₹{txn.amount:.2f}",
            'Category': txn.category,
            'Type': txn.txn_type,
            'Source': txn.source,
            'Is Routine': 'Yes' if txn.is_routine else 'No',
            'Is Flagged': 'Yes' if txn.is_flagged else 'No',
            'Notes': txn.user_context
        })
    
    # Return as downloadable file
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"}
    )

