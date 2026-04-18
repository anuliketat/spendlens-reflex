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
)


def index() -> rx.Component:
    return rx.box(
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
        max_width="1200px",
        margin="0 auto",
        padding="1em",
    )


app = rx.App()
app.add_page(index, route="/")
