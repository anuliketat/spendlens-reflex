import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    return rx.box(
        rx.heading("Transaction Explorer", size="5"),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Date"),
                    rx.table.column_header_cell("Merchant"),
                    rx.table.column_header_cell("Amount"),
                    rx.table.column_header_cell("Category"),
                    rx.table.column_header_cell("Type"),
                    rx.table.column_header_cell("Source"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    AppState.transactions,
                    lambda txn: rx.table.row(
                        rx.table.cell(txn["datetime"]),
                        rx.table.cell(txn["merchant"]),
                        rx.table.cell(f"₹{txn['amount']}"),
                        rx.table.cell(txn["category"]),
                        rx.table.cell(txn["txn_type"]),
                        rx.table.cell(txn["source"]),
                    ),
                ),
            ),
        ),
        padding="1em",
    )
