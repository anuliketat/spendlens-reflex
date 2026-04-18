import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Live Feed", size="5"),
        rx.foreach(
            AppState.transactions,
            lambda txn: rx.hstack(
                rx.text(txn["merchant"]),
                rx.spacer(),
                rx.text(f"₹{txn['amount']}"),
                rx.badge(
                    rx.cond(txn["is_flagged"], "Flagged", txn["category"]),
                    color_scheme=rx.cond(txn["is_flagged"], "red", "blue"),
                ),
                width="100%",
                padding_y="0.25em",
            ),
        ),
        padding="1em",
    )
