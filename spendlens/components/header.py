import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("SpendLens", size="9"),
        rx.text(AppState.verdict, color="gray"),
        rx.hstack(
            rx.badge(
                AppState.burn_rate.get("status", "—"),
                color_scheme=rx.cond(
                    AppState.burn_rate["status"] == "on_track",
                    "green",
                    rx.cond(
                        AppState.burn_rate["status"] == "at_risk",
                        "orange",
                        "red",
                    ),
                ),
            ),
        ),
        padding="1em",
        border_bottom="1px solid #eee",
    )
