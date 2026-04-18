import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Two-Tier Spend Map", size="5"),
        rx.vstack(
            rx.text("Routine Spend", weight="bold"),
            rx.foreach(
                AppState.transactions,
                lambda txn: rx.cond(
                    txn["is_routine"],
                    rx.hstack(
                        rx.text(txn["merchant"]),
                        rx.spacer(),
                        rx.text(f"₹{txn['amount']}"),
                        width="100%",
                    ),
                    rx.fragment(),
                ),
            ),
            rx.text("One-Off Spend", weight="bold", margin_top="1em"),
            rx.foreach(
                AppState.transactions,
                lambda txn: rx.cond(
                    ~txn["is_routine"],
                    rx.hstack(
                        rx.text(txn["merchant"]),
                        rx.spacer(),
                        rx.text(f"₹{txn['amount']}"),
                        width="100%",
                    ),
                    rx.fragment(),
                ),
            ),
        ),
        padding="1em",
    )
