import reflex as rx
from spendlens.state import AppState


def render() -> rx.Component:
    """Email import component for fetching and importing bank transactions."""
    return rx.box(
        rx.heading("Import Transactions from Email", size="5"),
        rx.divider(),
        
        # Step 1: Fetch Banks
        rx.section(
            rx.heading("Step 1: Fetch Bank Emails", size="4"),
            rx.text("Click below to scan your Gmail inbox for bank transaction emails."),
            rx.button(
                rx.hstack(
                    rx.cond(AppState.processing, rx.spinner(size="1")),
                    rx.text("Fetch Available Banks"),
                    spacing="2",
                ),
                on_click=AppState.fetch_email_banks,
                is_disabled=AppState.processing,
                color_scheme="blue",
                size="3",
                width="250px",
                _hover={
                    "box_shadow": "0 4px 12px rgba(0,0,0,0.15)",
                    "transform": "translateY(-1px)",
                },
                transition="all 0.2s ease",
                cursor="pointer",
            ),
            margin_bottom="2em",
        ),
        
        # Status messages
        rx.cond(
            AppState.email_import_status,
            rx.box(
                rx.hstack(
                    rx.cond(
                        AppState.processing,
                        rx.spinner(size="2"),
                        rx.icon(tag="info", color="blue"),
                    ),
                    rx.text(
                        AppState.email_import_status,
                        color=rx.cond(
                            AppState.email_import_status.contains("Error"),
                            "red",
                            rx.cond(
                                AppState.email_import_status.contains("Successfully"),
                                "green",
                                "black",
                            ),
                        ),
                        font_weight="medium",
                    ),
                    spacing="3",
                    align="center",
                ),
                padding="1em",
                background_color=rx.cond(
                    AppState.email_import_status.contains("Error"),
                    "#fee2e2",
                    rx.cond(
                        AppState.email_import_status.contains("Successfully"),
                        "#dcfce7",
                        "#f0f0f0",
                    ),
                ),
                border_radius="8px",
                margin_bottom="1em",
                border="1px solid",
                border_color=rx.cond(
                    AppState.email_import_status.contains("Error"),
                    "#ef4444",
                    rx.cond(
                        AppState.email_import_status.contains("Successfully"),
                        "#22c55e",
                        "#d1d5db",
                    ),
                ),
            ),
        ),
        
        # Step 2: Select Banks
        rx.cond(
            AppState.available_banks,
            rx.section(
                rx.heading("Step 2: Select Banks", size="4"),
                rx.text("Choose which banks' emails to import:"),
                rx.foreach(
                    AppState.available_banks,
                    lambda bank: rx.badge(
                        bank,
                        color_scheme="blue",
                        margin_right="0.5em",
                        margin_bottom="0.5em",
                    ),
                ),
                rx.divider(margin_y="1em"),
                rx.button(
                    rx.hstack(
                        rx.cond(AppState.processing, rx.spinner(size="1")),
                        rx.text("Import Selected Banks"),
                        spacing="2",
                    ),
                    on_click=lambda: AppState.import_from_email(AppState.available_banks),
                    color_scheme="green",
                    size="3",
                    is_disabled=AppState.processing | (AppState.available_banks.length() == 0),
                    _hover={
                        "box_shadow": "0 4px 12px rgba(0,0,0,0.15)",
                        "transform": "translateY(-1px)",
                    },
                    transition="all 0.2s ease",
                    cursor="pointer",
                ),
                margin_bottom="2em",
            ),
        ),
        
        # Step 3: Results
        rx.cond(
            AppState.extracted_emails,
            rx.section(
                rx.heading("Extract Results", size="4"),
                rx.hstack(
                    rx.text("Extracted "),
                    rx.text(AppState.extracted_emails.length()),
                    rx.text(" transactions"),
                    spacing="1",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Date"),
                            rx.table.column_header_cell("Merchant"),
                            rx.table.column_header_cell("Amount"),
                            rx.table.column_header_cell("Type"),
                            rx.table.column_header_cell("Status"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AppState.extracted_emails,
                            lambda txn: rx.cond(
                                txn["success"],
                                rx.table.row(
                                    rx.table.cell(txn.get("date", "—")),
                                    rx.table.cell(txn.get("merchant", "—")),
                                    rx.table.cell(f"₹{txn.get('amount', 0):.2f}"),
                                    rx.table.cell(txn.get("type", "—")),
                                    rx.table.cell("✓", color="green"),
                                ),
                                rx.table.row(
                                    rx.table.cell("—"),
                                    rx.table.cell(txn.get("description", "Error")),
                                    rx.table.cell("—"),
                                    rx.table.cell("—"),
                                    rx.table.cell("✗", color="red"),
                                ),
                            ),
                        ),
                    ),
                ),
                margin_bottom="2em",
            ),
        ),
        
        # Help section
        rx.section(
            rx.heading("Setup Instructions", size="4"),
            rx.unordered_list(
                rx.list_item("1. Go to Google Cloud Console and create a project"),
                rx.list_item("2. Enable the Gmail API"),
                rx.list_item("3. Create OAuth 2.0 credentials (Desktop application)"),
                rx.list_item("4. Download credentials.json and place in project root"),
                rx.list_item("5. First run will prompt for Gmail access authorization"),
            ),
            margin_bottom="2em",
        ),
        
        padding="1em",
        max_width="1000px",
    )
