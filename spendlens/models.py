import reflex as rx
from datetime import datetime


class Transaction(rx.Model, table=True):
    id: int | None = None
    datetime: datetime
    amount: float
    merchant: str
    category: str
    txn_type: str
    is_routine: bool = True
    is_flagged: bool = False
    user_context: str = ""
    source: str = "csv"


class Budget(rx.Model, table=True):
    id: int | None = None
    category: str
    user_set: float
    app_inferred: float
    month: str


class Archetype(rx.Model, table=True):
    id: int | None = None
    label: str
    summary: str
    computed_at: datetime


class Insight(rx.Model, table=True):
    id: int | None = None
    section: str
    content: str
    computed_at: datetime
