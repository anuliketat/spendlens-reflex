import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    """Navigation sidebar for page navigation."""
    return rx.box(
        rx.vstack(
            rx.heading("SpendLens", size="4", color="white"),
            rx.divider(color="#374151"),
            
            # Dashboard button
            rx.button(
                rx.hstack(
                    rx.icon(tag="layout_dashboard", size=18, color=rx.cond(AppState.current_page == "dashboard", "#60a5fa", "#9ca3af")),
                    rx.text("Dashboard", color=rx.cond(AppState.current_page == "dashboard", "#60a5fa", "#9ca3af")),
                    spacing="2",
                    align="center",
                ),
                on_click=AppState.navigate_to("dashboard"),
                variant="ghost",
                size="2",
                width="100%",
                justify_content="start",
                background=rx.cond(AppState.current_page == "dashboard", "#1f2937", "transparent"),
                _hover={"background": "#374151"},
            ),
            
            # Upload button
            rx.button(
                rx.hstack(
                    rx.icon(tag="upload", size=18, color=rx.cond(AppState.current_page == "upload", "#60a5fa", "#9ca3af")),
                    rx.text("Upload CSV", color=rx.cond(AppState.current_page == "upload", "#60a5fa", "#9ca3af")),
                    spacing="2",
                    align="center",
                ),
                on_click=AppState.navigate_to("upload"),
                variant="ghost",
                size="2",
                width="100%",
                justify_content="start",
                background=rx.cond(AppState.current_page == "upload", "#1f2937", "transparent"),
                _hover={"background": "#374151"},
            ),
            
            # Email Import button
            rx.button(
                rx.hstack(
                    rx.icon(tag="mail", size=18, color=rx.cond(AppState.current_page == "email_import", "#60a5fa", "#9ca3af")),
                    rx.text("Import from Gmail", color=rx.cond(AppState.current_page == "email_import", "#60a5fa", "#9ca3af")),
                    spacing="2",
                    align="center",
                ),
                on_click=AppState.navigate_to("email_import"),
                variant="ghost",
                size="2",
                width="100%",
                justify_content="start",
                background=rx.cond(AppState.current_page == "email_import", "#1f2937", "transparent"),
                _hover={"background": "#374151"},
            ),
            
            spacing="3",
            width="100%",
            align="start",
        ),
        width="250px",
        height="100vh",
        background="#111827",
        border_right="1px solid #374151",
        padding="1.5rem",
        position="fixed",
        left="0",
        top="0",
        z_index="1000",
    )
