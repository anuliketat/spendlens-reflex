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
                "Fetch Available Banks",
                on_click=AppState.fetch_email_banks,
                is_disabled=AppState.processing,
            ),
            margin_bottom="2em",
        ),
        
        # Status messages
        rx.cond(
            AppState.email_import_status,
            rx.box(
                rx.cond(
                    AppState.processing,
                    rx.spinner(),
                    rx.text(AppState.email_import_status),
                ),
                padding="1em",
                background_color="#f0f0f0",
                border_radius="6px",
                margin_bottom="1em",
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
                    "Import Selected Banks",
                    on_click=lambda: AppState.import_from_email(AppState.available_banks),
                    color_scheme="green",
                    is_disabled=AppState.processing | (AppState.available_banks == []),
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
