import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Weekly Pulse", size="5"),
        rx.text("Budget used: "),
        rx.progress(
            value=AppState.budget_pct_progress,
            max=100,
            color_scheme=rx.cond(
                AppState.burn_rate["status"] == "on_track",
                "green",
                rx.cond(AppState.burn_rate["status"] == "at_risk", "orange", "red"),
            ),
        ),
        rx.hstack(
            rx.text(f"Budget: {AppState.burn_rate.get('budget_pct', 0):.0%}"),
            rx.text(f"Time: {AppState.burn_rate.get('time_pct', 0):.0%}"),
        ),
        padding="1em",
    )
