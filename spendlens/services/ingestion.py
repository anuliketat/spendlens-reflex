import pandas as pd
from spendlens.models import Transaction
import reflex as rx


def ingest_csv(file_path: str):
    df = pd.read_csv(file_path)
    df["datetime"] = pd.to_datetime(df["datetime"])

    with rx.session() as session:
        for _, row in df.iterrows():
            txn = Transaction(
                datetime=row["datetime"],
                amount=row["amount"],
                merchant=row["merchant"],
                category=row["category"],
                txn_type=row["txn_type"],
                source="csv",
            )
            session.add(txn)
        session.commit()
