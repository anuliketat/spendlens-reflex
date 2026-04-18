import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Merchant Lens", size="5"),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Merchant"),
                    rx.table.column_header_cell("Visits"),
                    rx.table.column_header_cell("Total Spend"),
                    rx.table.column_header_cell("Annual Projection"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    AppState.merchant_habits,
                    lambda row: rx.table.row(
                        rx.table.cell(row["merchant"]),
                        rx.table.cell(row["count"]),
                        rx.table.cell(f"₹{row['total']:.0f}"),
                        rx.table.cell(f"₹{row['annual_projection']:.0f}"),
                    ),
                ),
            ),
        ),
        padding="1em",
    )
