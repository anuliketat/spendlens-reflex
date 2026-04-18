import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Quarterly Drift", size="5"),
        rx.text(
            "Category drift analysis will display month-over-month changes "
            "once 3+ months of transaction data is available."
        ),
        padding="1em",
    )
