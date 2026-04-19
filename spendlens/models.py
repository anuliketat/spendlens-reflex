import reflex as rx
from datetime import datetime
from sqlmodel import Field
from typing import Optional


class Transaction(rx.Model, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
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
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str
    user_set: float
    app_inferred: float
    month: str


class Archetype(rx.Model, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str
    summary: str
    computed_at: datetime


class Insight(rx.Model, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    section: str
    content: str
    computed_at: datetime
