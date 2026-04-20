import reflex as rx
from sqlmodel import select
from spendlens.models import Transaction
from spendlens.services.analytics import compute_burn_rate, compute_merchant_habits
from spendlens.services.intel import get_verdict
import pandas as pd
import pdfplumber
import base64
import io
import os
from typing import Any


class AppState(rx.State):
    transactions: list[dict[str, Any]] = []
    burn_rate: dict[str, Any] = {}
    verdict: str = ""
    merchant_habits: list[dict[str, Any]] = []
    interventions: list[dict[str, Any]] = []
    archetype: dict[str, Any] = {}
    budget: dict[str, Any] = {}
    flagged_txn: dict[str, Any] = {}
    show_flag_prompt: bool = False
    uploaded_file: dict[str, Any] = {}
    insights: str = ""
    processing: bool = False
    current_page: str = "dashboard"
    
    # Email import related
    available_banks: list[dict[str, Any]] = []  # List of {email, name, count}
    selected_banks: list[str] = []
    email_import_status: str = ""
    email_import_progress: int = 0
    email_import_progress_max: int = 100
    extracted_emails: list[dict[str, Any]] = []
    
    # Time period selection
    time_period: str = "1y"  # Options: 1y, 6m, 3m, custom
    custom_start_date: str = ""
    custom_end_date: str = ""
    
    # Import completion tracking
    import_completed: bool = False
    total_transactions_imported: int = 0

    @rx.var
    def budget_pct_progress(self) -> int:
        return int(self.burn_rate.get("budget_pct", 0) * 100)

    def load_dashboard(self) -> None:
        with rx.session() as session:
            txns = session.exec(
                select(Transaction)
            ).all()
            self.transactions = [
                {
                    "id": t.id,
                    "datetime": t.datetime.isoformat(),
                    "amount": t.amount,
                    "merchant": t.merchant,
                    "category": t.category,
                    "txn_type": t.txn_type,
                    "is_routine": t.is_routine,
                    "is_flagged": t.is_flagged,
                    "user_context": t.user_context,
                    "source": t.source,
                }
                for t in txns
            ]

        total_spent = sum(t["amount"] for t in self.transactions)
        monthly_budget = self.budget.get("total", 50000)
        from datetime import datetime
        import calendar
        now = datetime.now()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        self.burn_rate = compute_burn_rate(
            total_spent, monthly_budget, now.day, days_in_month
        )

        top_txns = sorted(self.transactions, key=lambda t: t["amount"], reverse=True)[:5]
        top_txns_display = [
            {"merchant": t["merchant"], "amount": t["amount"]} for t in top_txns
        ]
        routine_total = sum(t["amount"] for t in self.transactions if t["is_routine"])
        oneoff_total = sum(t["amount"] for t in self.transactions if not t["is_routine"])

        try:
            self.verdict = get_verdict(
                self.burn_rate.get("budget_pct", 0),
                top_txns_display,
                routine_total,
                oneoff_total,
            )
        except Exception:
            self.verdict = "Error generating verdict. Check HF token."

        self.merchant_habits = compute_merchant_habits(self.transactions)

    def handle_flag_context(self, context: str) -> None:
        with rx.session() as session:
            txn = session.get(Transaction, self.flagged_txn["id"])
            if txn:
                txn.user_context = context
                txn.is_flagged = False
                session.commit()
        self.show_flag_prompt = False

    def handle_upload(self, files: list[dict]) -> None:
        if files:
            self.processing = True
            file = files[0]
            self.uploaded_file = file
            content = base64.b64decode(file["content"])
            filename = file["name"]
            ext = filename.split('.')[-1].lower()
            text = ""
            if ext == 'csv':
                df = pd.read_csv(io.StringIO(content.decode('utf-8')))
                text = df.to_string()
            elif ext in ['xlsx', 'xls']:
                df = pd.read_excel(io.BytesIO(content))
                text = df.to_string()
            elif ext == 'pdf':
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
            elif ext == 'txt':
                text = content.decode('utf-8')
            else:
                text = "Unsupported file type"
            
            # Generate insights using Fin-R1 with optimizations
            try:
                from spendlens.services.intel import _load_model
                import torch
                model, tokenizer = _load_model()
                
                # Prepare prompt and limit text length
                text_truncated = text[:2000]  # Limit to 2000 chars
                prompt = f"Analyze and provide financial insights:\n{text_truncated}\n\nInsights:"
                
                inputs = tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                ).to(model.device)
                
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=512,
                        temperature=0.7,
                        top_p=0.9,
                        do_sample=False,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                
                self.insights = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()
            except Exception as e:
                self.insights = f"Error generating insights: {str(e)}"
            
            self.processing = False

    def fetch_email_banks(self):
        """Fetch list of potential banks from Gmail inbox."""
        self.processing = True
        self.email_import_progress = 0
        self.email_import_status = "🔐 Connecting to Gmail... Authentication popup will open in a new tab."
        print("[Gmail Import] Starting fetch_email_banks...")
        yield  # Yield to prevent WebSocket timeout
        
        try:
            from spendlens.services.gmail_service import get_gmail_service, list_potential_banks
            
            self.email_import_status = "🔐 Authenticating with Gmail..."
            self.email_import_progress = 5
            print("[Gmail Import] Authenticating with Gmail...")
            yield  # Yield before authentication
            
            service = get_gmail_service()
            self.email_import_progress = 10
            self.email_import_status = "✓ Gmail authenticated! Scanning for bank emails..."
            print("[Gmail Import] Gmail authenticated successfully")
            yield  # Yield during authentication
            
            self.email_import_status = "🔍 Starting Gmail scan..."
            self.email_import_progress = 15
            print("[Gmail Import] Starting Gmail scan...")
            yield
            
            # Consume the generator and update progress based on yielded updates
            banks_generator = list_potential_banks(service)
            banks = None
            
            for progress_update in banks_generator:
                update_type = progress_update.get('type', '')
                message = progress_update.get('message', '')
                
                print(f"[Gmail Import] {message}")
                self.email_import_status = message
                
                # Calculate progress based on update type
                if update_type == 'pattern_start':
                    pattern = progress_update.get('pattern', 1)
                    total_patterns = progress_update.get('total_patterns', 7)
                    # 15-70% for pattern scanning
                    progress = 15 + ((pattern - 1) / total_patterns) * 55
                    self.email_import_progress = int(progress)
                elif update_type == 'page_fetch':
                    # Keep progress moving during page fetches
                    current_progress = self.email_import_progress
                    self.email_import_progress = min(current_progress + 1, 70)
                elif update_type == 'message_process':
                    # Keep progress moving during message processing
                    current_progress = self.email_import_progress
                    self.email_import_progress = min(current_progress + 1, 70)
                elif update_type == 'pattern_complete':
                    pattern = progress_update.get('pattern', 1)
                    total_patterns = progress_update.get('total_patterns', 7)
                    # 15-70% for pattern scanning
                    progress = 15 + (pattern / total_patterns) * 55
                    self.email_import_progress = int(progress)
                elif update_type == 'filtering':
                    self.email_import_progress = 75
                elif update_type == 'complete':
                    banks = progress_update.get('banks', [])
                    self.email_import_progress = 85
                
                yield  # Yield after each progress update
            
            if banks is None:
                banks = []
            
            self.email_import_progress = 90
            self.email_import_status = f"✓ Analysis complete! Found {len(banks)} verified transaction senders."
            print(f"[Gmail Import] Complete! Found {len(banks)} verified transaction senders")
            yield  # Yield after filtering
            
            self.available_banks = banks
            self.email_import_progress = 100
            self.email_import_status = f"✓ Found {len(banks)} verified transaction senders. Select banks and time period to import."
            print("[Gmail Import] Finished successfully")
            yield  # Final yield
            
        except ConnectionError as e:
            error_msg = f"❌ Connection Error: {str(e)}. Please check your internet connection and try again."
            self.email_import_status = error_msg
            print(f"[Gmail Import ERROR] Connection Error: {e}")
        except TimeoutError as e:
            error_msg = f"❌ Timeout Error: {str(e)}. The operation took too long. Please try again."
            self.email_import_status = error_msg
            print(f"[Gmail Import ERROR] Timeout Error: {e}")
        except FileNotFoundError as e:
            error_msg = f"❌ Gmail Setup Required: {str(e)}"
            self.email_import_status = error_msg
            print(f"[Gmail Import ERROR] FileNotFoundError: {e}")
        except RuntimeError as e:
            if "authentication required" in str(e).lower():
                error_msg = f"🔐 Gmail Authentication Needed: Please complete OAuth setup first. {str(e)}"
                self.email_import_status = error_msg
                print(f"[Gmail Import ERROR] Authentication Required: {e}")
            else:
                error_msg = f"❌ Authentication Error: {str(e)}"
                self.email_import_status = error_msg
                print(f"[Gmail Import ERROR] RuntimeError: {e}")
        except Exception as e:
            error_msg = str(e)
            if "mismatching_state" in error_msg:
                error_msg = "❌ CSRF Error: Please refresh the page and try Gmail authentication again."
                self.email_import_status = error_msg
                print(f"[Gmail Import ERROR] CSRF Error: {e}")
            else:
                error_msg = f"❌ Error fetching banks: {error_msg}"
                self.email_import_status = error_msg
                print(f"[Gmail Import ERROR] Exception: {e}")
        finally:
            self.processing = False
            print("[Gmail Import] Processing flag set to False")
            yield
    
    def toggle_bank_selection(self, bank_email: str) -> None:
        """Toggle selection of a bank."""
        if bank_email in self.selected_banks:
            self.selected_banks.remove(bank_email)
        else:
            self.selected_banks.append(bank_email)
    
    def set_time_period(self, period: str) -> None:
        """Set the time period for data import."""
        self.time_period = period
    
    def set_custom_dates(self, start_date: str, end_date: str) -> None:
        """Set custom date range."""
        self.custom_start_date = start_date
        self.custom_end_date = end_date
    
    @rx.event
    def navigate_to(self, page: str) -> None:
        """Navigate to a different page."""
        self.current_page = page

    def import_from_email(self, banks: list[str]):
        """Import transactions from selected email senders with selected time period."""
        if not banks:
            self.email_import_status = "Please select at least one bank sender"
            return
        
        self.processing = True
        self.import_completed = False
        self.total_transactions_imported = 0
        self.selected_banks = banks
        total_banks = len(banks)
        self.email_import_status = f"Starting import from {total_banks} bank(s) for {self.time_period}..."
        self.email_import_progress = 0
        self.email_import_progress_max = 100  # Use percentage instead of raw numbers
        yield
        
        try:
            from spendlens.services.gmail_service import get_gmail_service, get_emails_from_sender
            from spendlens.services.email_extraction import batch_extract_transactions
            
            self.email_import_status = "🔐 Connecting to Gmail..."
            self.email_import_progress = 5
            print("[Email Import] Connecting to Gmail...")
            yield
            
            service = get_gmail_service()
            self.email_import_progress = 10
            self.email_import_status = "✓ Gmail connected successfully"
            print("[Email Import] Gmail connected successfully")
            yield
            
            all_emails = []
            
            # Get date range based on selected time period
            from datetime import datetime, timedelta
            self.email_import_status = "📅 Calculating date range..."
            self.email_import_progress = 15
            print("[Email Import] Calculating date range...")
            yield
            
            end_date = datetime.now()
            if self.time_period == "1y":
                start_date = end_date - timedelta(days=365)
            elif self.time_period == "6m":
                start_date = end_date - timedelta(days=180)
            elif self.time_period == "3m":
                start_date = end_date - timedelta(days=90)
            elif self.time_period == "custom":
                start_date = datetime.strptime(self.custom_start_date, "%Y-%m-%d")
                end_date = datetime.strptime(self.custom_end_date, "%Y-%m-%d")
            else:
                start_date = end_date - timedelta(days=365)
            
            self.email_import_progress = 20
            self.email_import_status = f"✓ Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            print(f"[Email Import] Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            yield
            
            # Fetch emails from each selected bank
            base_progress = 20
            progress_per_bank = 50 / total_banks  # 50% for fetching emails across all banks
            
            for i, bank in enumerate(banks, 1):
                bank_progress_start = base_progress + ((i - 1) * progress_per_bank)
                
                self.email_import_status = f"📧 Fetching emails from {i}/{total_banks}: {bank}..."
                self.email_import_progress = int(bank_progress_start)
                print(f"[Email Import] Fetching from {i}/{total_banks}: {bank}")
                yield
                
                # Consume the generator and update progress
                email_generator = get_emails_from_sender(
                    service, 
                    bank, 
                    max_results=500,
                    start_date=start_date,
                    end_date=end_date
                )
                
                bank_emails = []
                for progress_update in email_generator:
                    update_type = progress_update.get('type', '')
                    message = progress_update.get('message', '')
                    
                    print(f"[Email Import] {message}")
                    self.email_import_status = message
                    
                    # Update progress based on update type
                    if update_type == 'fetch_start':
                        pass  # Already set before loop
                    elif update_type == 'page_fetch':
                        # Increment progress slightly during page fetches
                        current_progress = self.email_import_progress
                        self.email_import_progress = min(current_progress + 1, int(bank_progress_start + progress_per_bank * 0.8))
                    elif update_type == 'message_process':
                        # Increment progress during message processing
                        current_progress = self.email_import_progress
                        self.email_import_progress = min(current_progress + 1, int(bank_progress_start + progress_per_bank * 0.9))
                    elif update_type == 'complete':
                        bank_emails = progress_update.get('emails', [])
                        self.email_import_progress = int(bank_progress_start + progress_per_bank)
                    elif update_type == 'error':
                        print(f"[Email Import ERROR] {message}")
                    
                    yield
                
                all_emails.extend(bank_emails)
                print(f"[Email Import] Fetched {len(bank_emails)} emails from {bank}")
                yield
            
            if not all_emails:
                self.email_import_status = "No emails found from selected banks in the selected period"
                print("[Email Import] No emails found")
                self.processing = False
                return
            
            # Extract transactions in smaller batches to prevent WebSocket timeout
            self.email_import_progress = 70
            self.email_import_status = f"🤖 Extracting transactions from {len(all_emails)} emails with AI..."
            print(f"[Email Import] Extracting transactions from {len(all_emails)} emails...")
            yield  # Yield to prevent WebSocket timeout
            
            from spendlens.services.email_extraction import extract_transaction_details
            extracted = []
            batch_size = 5  # Process 5 emails at a time with yields in between
            
            for batch_start in range(0, len(all_emails), batch_size):
                batch_end = min(batch_start + batch_size, len(all_emails))
                batch = all_emails[batch_start:batch_end]
                
                # Process this batch
                for email in batch:
                    result = extract_transaction_details(
                        email.get('body', email.get('snippet', '')),
                        email.get('sender', '')
                    )
                    result['email_id'] = email.get('id', '')
                    result['sender'] = email.get('sender', '')
                    extracted.append(result)
                
                # Update progress and yield after each batch
                processed = len(extracted)
                progress_pct = 70 + (processed / len(all_emails)) * 15  # 70-85% for extraction
                self.email_import_progress = int(progress_pct)
                self.email_import_status = f"🤖 AI processing... ({processed}/{len(all_emails)} emails)"
                print(f"[Email Import] AI processing {processed}/{len(all_emails)} emails...")
                yield  # Yield to keep WebSocket alive
            
            successful_extractions = sum(1 for t in extracted if t.get("success"))
            self.email_import_progress = 85
            self.email_import_status = f"✓ Extracted {successful_extractions} transactions from {len(all_emails)} emails"
            print(f"[Email Import] Extracted {successful_extractions} transactions")
            yield  # Yield to prevent WebSocket timeout
            
            # Save to database
            self.email_import_progress = 90
            self.email_import_status = "💾 Saving transactions to database..."
            print("[Email Import] Saving transactions to database...")
            saved_count = 0
            
            with rx.session() as session:
                total_to_save = sum(1 for t in extracted if t.get("success") and t.get("amount", 0) > 0)
                for i, txn_data in enumerate(extracted):
                    if txn_data.get("success") and txn_data.get("amount", 0) > 0:
                        try:
                            # Parse date
                            from datetime import datetime
                            try:
                                txn_date = datetime.strptime(txn_data.get("date", ""), "%Y-%m-%d")
                            except:
                                txn_date = datetime.now()
                            
                            transaction = Transaction(
                                datetime=txn_date,
                                amount=txn_data.get("amount", 0),
                                merchant=txn_data.get("merchant", "Unknown"),
                                category="banking",
                                txn_type=txn_data.get("type", "other"),
                                is_routine=True,
                                source="email",
                                user_context=f"{txn_data.get('description', '')} (from {txn_data.get('sender', '')})"
                            )
                            session.add(transaction)
                            saved_count += 1
                            
                            # Yield every 5 transactions to prevent timeout (more frequent)
                            if saved_count % 5 == 0:
                                progress_pct = 90 + int((saved_count / total_to_save) * 10) if total_to_save > 0 else 90
                                self.email_import_progress = min(progress_pct, 99)
                                self.email_import_status = f"💾 Saving transactions... ({saved_count}/{total_to_save})"
                                print(f"[Email Import] Saving transactions {saved_count}/{total_to_save}...")
                                yield
                        except Exception as e:
                            print(f"[Email Import ERROR] Error saving transaction: {e}")
                            continue
                
                session.commit()
            
            self.extracted_emails = extracted
            self.total_transactions_imported = saved_count
            self.email_import_progress = 100
            self.email_import_status = f"✓ Successfully imported {saved_count} transactions from {len(all_emails)} emails"
            print(f"[Email Import] Successfully imported {saved_count} transactions")
            self.import_completed = True
            yield
            
            # Reload dashboard to sync data
            self.load_dashboard()
            
        except ConnectionError as e:
            self.email_import_status = f"❌ Connection Error: {str(e)}. Please check your internet connection and try again."
            self.processing = False
            yield
        except TimeoutError as e:
            self.email_import_status = f"❌ Timeout Error: {str(e)}. The operation took too long. Please try again."
            self.processing = False
            yield
        except FileNotFoundError as e:
            self.email_import_status = f"❌ Gmail Setup Required: {str(e)}"
            self.processing = False
            yield
        except Exception as e:
            error_msg = str(e)
            self.email_import_status = f"❌ Error: {error_msg}. Please check the error and try again."
            self.processing = False
            yield
        finally:
            self.processing = False
            yield
