import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Upload File for Insights", size="5"),
        rx.upload(
            rx.text("Drag and drop files here or click to select"),
            id="upload",
            accept={
                "text/csv": [".csv"],
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                "application/vnd.ms-excel": [".xls"],
                "application/pdf": [".pdf"],
                "text/plain": [".txt"],
            },
            max_files=1,
            on_drop=AppState.handle_upload,
        ),
        rx.cond(
            AppState.processing,
            rx.text("Processing..."),
            rx.cond(
                AppState.insights,
                rx.box(
                    rx.heading("Insights", size="4"),
                    rx.text(AppState.insights),
                ),
                rx.text("Upload a file to generate insights."),
            ),
        ),
        padding="1em",
    )