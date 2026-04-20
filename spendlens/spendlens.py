import reflex as rx
from spendlens.state import AppState
from spendlens.components import (
    header,
    live_feed,
    weekly_pulse,
    monthly_battle,
    merchant_lens,
    two_tier_map,
    archetype,
    drift,
    interventions,
    explorer,
    upload,
    email_import,
    navigation,
)


def index() -> rx.Component:
    return rx.box(
        navigation.render(),
        rx.box(
            rx.cond(
                AppState.current_page == "dashboard",
                rx.box(
                    header.render(),
                    live_feed.render(),
                    weekly_pulse.render(),
                    monthly_battle.render(),
                    merchant_lens.render(),
                    two_tier_map.render(),
                    archetype.render(),
                    drift.render(),
                    interventions.render(),
                    explorer.render(),
                    on_mount=AppState.load_dashboard,
                ),
                rx.cond(
                    AppState.current_page == "upload",
                    upload.render(),
                    rx.cond(
                        AppState.current_page == "email_import",
                        email_import.render(),
                    ),
                ),
            ),
            margin_left="250px",
            padding="1em",
            background="#111827",
            min_height="100vh",
        ),
    )


app = rx.App()
app.add_page(index, route="/")
