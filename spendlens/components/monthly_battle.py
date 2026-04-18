import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Monthly Battlefield", size="5"),
        rx.text("Category breakdown coming soon — wire up Budget model to populate."),
        padding="1em",
    )
