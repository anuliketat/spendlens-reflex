import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.heading("SpendLens", size="9"),
            rx.hstack(
                rx.link("Upload for Insights", href="/upload", color="blue"),
                rx.link("Import from Email", href="/email_import", color="blue"),
                spacing="3",
            ),
            justify="between",
            width="100%",
        ),
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
