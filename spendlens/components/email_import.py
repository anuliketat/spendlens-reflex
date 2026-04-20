import reflex as rx
from spendlens.state import AppState
import csv
import io
from datetime import datetime
from typing import List, Dict


def render() -> rx.Component:
    """Enhanced email import component with progress tracking, bank selection, and time period choice."""
    
    return rx.box(
        # Header
        rx.vstack(
            rx.heading("Import Bank Transactions from Gmail", size="5"),
            rx.text(
                "Seamlessly extract transaction data from your bank emails. Select your banks and time period to get started.",
                font_size="14px",
                color="gray"
            ),
            spacing="1",
            margin_bottom="2em",
        ),
        
        # Step 1: Fetch Available Banks
        rx.vstack(
            rx.badge(
                "Step 1",
                variant="solid",
                color_scheme="blue",
                font_size="12px"
            ),
            rx.heading("Discover Your Banks", size="4"),
            rx.text(
                "Scan your Gmail inbox to automatically detect bank transaction senders.",
                color="gray",
                font_size="14px"
            ),
            
            # Fetch Banks Button with enhanced styling
            rx.button(
                rx.hstack(
                    rx.cond(
                        AppState.processing & (AppState.available_banks.length() == 0),
                        rx.spinner(size="1"),
                        rx.icon(tag="mail", size=18)
                    ),
                    rx.text(
                        rx.cond(
                            AppState.available_banks.length() > 0,
                            f"✓ Found Banks • Scan Again",
                            "Scan Gmail for Banks"
                        ),
                        font_weight="600",
                        font_size="15px"
                    ),
                    spacing="3",
                    align="center",
                ),
                on_click=AppState.fetch_email_banks,
                is_disabled=AppState.processing,
                size="3",
                padding="12px 24px",
                background=rx.cond(
                    AppState.available_banks.length() > 0,
                    "#10b981",
                    "#3b82f6"
                ),
                color="white",
                border="none",
                border_radius="8px",
                _hover={
                    "box_shadow": "0 6px 20px rgba(0,0,0,0.15)",
                    "transform": "translateY(-2px)",
                    "background": rx.cond(
                        AppState.available_banks.length() > 0,
                        "#059669",
                        "#2563eb"
                    ),
                },
                transition="all 0.3s ease",
                cursor="pointer",
                width="fit-content",
            ),
            
            # Progress bar and status
            rx.cond(
                AppState.processing | (AppState.email_import_status != ""),
                rx.vstack(
                    rx.cond(
                        AppState.processing & (AppState.available_banks.length() == 0),
                        rx.progress(
                            value=AppState.email_import_progress / 100,
                            size="3",
                            color_scheme="blue",
                            width="100%"
                        ),
                    ),
                    rx.box(
                        rx.hstack(
                            rx.icon(
                                tag=rx.cond(
                                    AppState.email_import_status.contains("Error"),
                                    "alert_circle",
                                    rx.cond(
                                        AppState.email_import_status.contains("✓"),
                                        "check_circle",
                                        "info"
                                    )
                                ),
                                size=18,
                                color=rx.cond(
                                    AppState.email_import_status.contains("Error"),
                                    "#ef4444",
                                    rx.cond(
                                        AppState.email_import_status.contains("✓"),
                                        "#10b981",
                                        "#3b82f6"
                                    )
                                )
                            ),
                            rx.text(
                                AppState.email_import_status,
                                font_size="14px",
                                flex="1"
                            ),
                            spacing="3",
                            align="center",
                            width="100%"
                        ),
                        padding="12px 16px",
                        background=rx.cond(
                            AppState.email_import_status.contains("Error"),
                            "#fef2f2",
                            rx.cond(
                                AppState.email_import_status.contains("✓"),
                                "#f0fdf4",
                                "#f0f9ff"
                            )
                        ),
                        border_radius="8px",
                        border="1px solid",
                        border_color=rx.cond(
                            AppState.email_import_status.contains("Error"),
                            "#fecaca",
                            rx.cond(
                                AppState.email_import_status.contains("✓"),
                                "#86efac",
                                "#bfdbfe"
                            )
                        ),
                        width="100%"
                    ),
                    spacing="2",
                    width="100%"
                )
            ),
            
            spacing="3",
            padding="20px",
            background="#f9fafb",
            border_radius="12px",
            border="1px solid #e5e7eb",
            margin_bottom="2em",
        ),
        
        # Step 2: Select Banks and Time Period
        rx.cond(
            AppState.available_banks.length() > 0,
            rx.vstack(
                rx.badge(
                    "Step 2",
                    variant="solid",
                    color_scheme="blue",
                    font_size="12px"
                ),
                rx.heading("Select Banks & Time Period", size="4"),
                
                # Bank Selection
                rx.vstack(
                    rx.heading("Choose Banks to Import", size="5", margin_bottom="1"),
                    rx.box(
                        rx.vstack(
                            rx.foreach(
                                AppState.available_banks.to(List[Dict[str, str]]),
                                lambda bank: rx.hstack(
                                    rx.checkbox(
                                        is_checked=AppState.selected_banks.contains(bank["email"]),
                                        on_change=lambda _: AppState.toggle_bank_selection(bank["email"])
                                    ),
                                    rx.vstack(
                                        rx.text(
                                            rx.cond(
                                                bank["name"],
                                                bank["name"],
                                                bank["email"]
                                            ),
                                            font_weight="600",
                                            font_size="14px"
                                        ),
                                        rx.text(
                                            bank["email"],
                                            font_size="12px",
                                            color="gray"
                                        ),
                                        spacing="0",
                                    ),
                                    rx.spacer(),
                                    rx.badge(
                                        rx.text(f"{bank.get('count', 0)} emails"),
                                        color_scheme="gray",
                                        font_size="12px"
                                    ),
                                    spacing="3",
                                    align="center",
                                    padding="12px",
                                    width="100%",
                                    _hover={"background": "#f3f4f6"},
                                    border_radius="8px",
                                ),
                            ),
                            spacing="2",
                            width="100%"
                        ),
                        padding="12px",
                        background="white",
                        border="1px solid #e5e7eb",
                        border_radius="8px",
                    ),
                    spacing="2",
                ),
                
                # Time Period Selection
                rx.vstack(
                    rx.heading("Select Time Period", size="5", margin_bottom="1"),
                    rx.hstack(
                        rx.button(
                            "Last 1 Year",
                            on_click=lambda: AppState.set_time_period("1y"),
                            size="2",
                            variant=rx.cond(
                                AppState.time_period == "1y",
                                "solid",
                                "outline"
                            ),
                            color_scheme="blue",
                            cursor="pointer"
                        ),
                        rx.button(
                            "Last 6 Months",
                            on_click=lambda: AppState.set_time_period("6m"),
                            size="2",
                            variant=rx.cond(
                                AppState.time_period == "6m",
                                "solid",
                                "outline"
                            ),
                            color_scheme="blue",
                            cursor="pointer"
                        ),
                        rx.button(
                            "Last 3 Months",
                            on_click=lambda: AppState.set_time_period("3m"),
                            size="2",
                            variant=rx.cond(
                                AppState.time_period == "3m",
                                "solid",
                                "outline"
                            ),
                            color_scheme="blue",
                            cursor="pointer"
                        ),
                        rx.button(
                            "Custom Range",
                            on_click=lambda: AppState.set_time_period("custom"),
                            size="2",
                            variant=rx.cond(
                                AppState.time_period == "custom",
                                "solid",
                                "outline"
                            ),
                            color_scheme="blue",
                            cursor="pointer"
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    
                    # Custom date inputs
                    rx.cond(
                        AppState.time_period == "custom",
                        rx.hstack(
                            rx.input(
                                type_="date",
                                on_change=lambda v: AppState.set_custom_dates(v, AppState.custom_end_date),
                                value=AppState.custom_start_date,
                                size="2"
                            ),
                            rx.text("to", color="gray"),
                            rx.input(
                                type_="date",
                                on_change=lambda v: AppState.set_custom_dates(AppState.custom_start_date, v),
                                value=AppState.custom_end_date,
                                size="2"
                            ),
                            spacing="2",
                        )
                    ),
                    spacing="2",
                ),
                
                # Import Button
                rx.button(
                    rx.hstack(
                        rx.cond(
                            AppState.processing & (AppState.available_banks.length() > 0),
                            rx.spinner(size="1"),
                            rx.icon(tag="download", size=18)
                        ),
                        rx.text(
                            "Import Selected Transactions",
                            font_weight="600",
                            font_size="15px"
                        ),
                        spacing="3",
                        align="center",
                    ),
                    on_click=lambda: AppState.import_from_email(AppState.selected_banks),
                    is_disabled=AppState.processing | (AppState.selected_banks.length() == 0),
                    size="3",
                    padding="12px 24px",
                    background="#10b981",
                    color="white",
                    border="none",
                    border_radius="8px",
                    _hover={
                        "box_shadow": "0 6px 20px rgba(0,0,0,0.15)",
                        "transform": "translateY(-2px)",
                        "background": "#059669",
                    },
                    transition="all 0.3s ease",
                    cursor="pointer",
                    width="fit-content",
                ),
                
                spacing="4",
                padding="20px",
                background="#f9fafb",
                border_radius="12px",
                border="1px solid #e5e7eb",
                margin_bottom="2em",
            )
        ),
        
        # Step 3: Import Progress
        rx.cond(
            AppState.processing & (AppState.available_banks.length() > 0),
            rx.vstack(
                rx.badge(
                    "Step 3",
                    variant="solid",
                    color_scheme="blue",
                    font_size="12px"
                ),
                rx.heading("Importing Transactions", size="4"),
                
                rx.progress(
                    value=AppState.email_import_progress / AppState.email_import_progress_max,
                    size="3",
                    color_scheme="green",
                    width="100%"
                ),
                
                rx.box(
                    rx.hstack(
                        rx.spinner(size="2", color="#10b981"),
                        rx.vstack(
                            rx.text(
                                AppState.email_import_status,
                                font_size="14px",
                                font_weight="500"
                            ),
                            rx.text(
                                f"Progress: {AppState.email_import_progress}/{AppState.email_import_progress_max}",
                                font_size="12px",
                                color="gray"
                            ),
                            spacing="1",
                            flex="1"
                        ),
                        spacing="3",
                        align="center",
                        width="100%"
                    ),
                    padding="16px",
                    background="white",
                    border_radius="8px",
                    border="1px solid #e5e7eb",
                ),
                
                spacing="3",
                padding="20px",
                background="#f9fafb",
                border_radius="12px",
                border="1px solid #e5e7eb",
                margin_bottom="2em",
            )
        ),
        
        # Step 4: Results and CSV Download
        rx.cond(
            AppState.import_completed,
            rx.vstack(
                rx.badge(
                    "Step 4",
                    variant="solid",
                    color_scheme="blue",
                    font_size="12px"
                ),
                rx.heading("Import Complete!", size="4"),
                
                rx.box(
                    rx.hstack(
                        rx.icon(tag="check_check", size=24, color="#10b981"),
                        rx.vstack(
                            rx.text(
                                f"✓ Successfully imported {AppState.total_transactions_imported} transactions",
                                font_weight="600",
                                font_size="14px"
                            ),
                            rx.text(
                                "Your data is now synced and insights are being updated on the main dashboard.",
                                font_size="12px",
                                color="gray"
                            ),
                            spacing="1",
                            flex="1"
                        ),
                        spacing="3",
                        align="center",
                        width="100%"
                    ),
                    padding="16px",
                    background="#f0fdf4",
                    border="1px solid #86efac",
                    border_radius="8px",
                ),
                
                # Download CSV Button
                rx.link(
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="download", size=18),
                            rx.text("Download as CSV", font_weight="600"),
                            spacing="2",
                            align="center",
                        ),
                        size="3",
                        padding="10px 20px",
                        background="#6366f1",
                        color="white",
                        border="none",
                        border_radius="8px",
                        _hover={
                            "box_shadow": "0 4px 12px rgba(0,0,0,0.15)",
                            "background": "#4f46e5",
                        },
                        cursor="pointer",
                        width="fit-content",
                    ),
                    href="/api/export/transactions/csv",
                    is_external=True,
                    download="transactions.csv"
                ),
                
                # Transaction Details Table
                rx.cond(
                    AppState.extracted_emails.length() > 0,
                    rx.vstack(
                        rx.heading("Imported Transactions", size="5", margin_bottom="1"),
                        rx.box(
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("Date"),
                                        rx.table.column_header_cell("Time"),
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
                                                rx.table.cell(txn.get("time", "—")),
                                                rx.table.cell(txn.get("merchant", "—")),
                                                rx.table.cell(f"₹{txn.get('amount', 0):.2f}"),
                                                rx.table.cell(txn.get("type", "—")),
                                                rx.table.cell("✓", color="green"),
                                            ),
                                            rx.table.row(
                                                rx.table.cell("—"),
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
                            overflow="auto",
                            width="100%",
                        ),
                        spacing="2",
                    )
                ),
                
                spacing="4",
                padding="20px",
                background="#f9fafb",
                border_radius="12px",
                border="1px solid #e5e7eb",
                margin_bottom="2em",
            )
        ),
        
        # Help section
        rx.vstack(
            rx.heading("Setup Instructions", size="5"),
            rx.unordered_list(
                rx.list_item("1. Go to Google Cloud Console and create a project"),
                rx.list_item("2. Enable the Gmail API"),
                rx.list_item("3. Create OAuth 2.0 credentials (Desktop application)"),
                rx.list_item("4. Download credentials.json and place in project root"),
                rx.list_item("5. First run will prompt for Gmail access authorization"),
            ),
            color="gray",
            font_size="13px",
            padding="16px",
            background="#f3f4f6",
            border_radius="8px",
            margin_bottom="2em",
        ),
        
        padding="2em",
        max_width="1000px",
    )
