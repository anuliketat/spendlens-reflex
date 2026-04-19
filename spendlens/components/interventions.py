import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Intervention Feed", size="5"),
        rx.foreach(
            AppState.interventions,
            lambda card: rx.card(
                rx.text(card["merchant_or_habit"], weight="bold"),
                rx.text(card["pattern"]),
                rx.text(f"Potential saving: ₹{card['monthly_saving_inr']}/mo"),
                rx.text(card["action"], color="green"),
                margin_bottom="0.5em",
            ),
        ),
        rx.cond(
            ~AppState.interventions,
            rx.text("No intervention cards yet. Fin-R1 will generate them from your habits."),
            rx.fragment(),
        ),
        padding="1em",
    )
