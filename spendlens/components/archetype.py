import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Spending Archetype", size="5"),
        rx.cond(
            AppState.archetype,
            rx.vstack(
                rx.badge(AppState.archetype["label"], size="3"),
                rx.text(AppState.archetype["summary"]),
            ),
            rx.text("Archetype not yet computed. Load more transactions."),
        ),
        padding="1em",
    )
