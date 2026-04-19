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


class AppState(rx.State):
    transactions: list[dict] = []
    burn_rate: dict = {}
    verdict: str = ""
    merchant_habits: list[dict] = []
    interventions: list[dict] = []
    archetype: dict = {}
    budget: dict = {}
    flagged_txn: dict = {}
    show_flag_prompt: bool = False
    uploaded_file: dict = {}
    insights: str = ""
    processing: bool = False
    
    # Email import related
    available_banks: list[str] = []
    selected_banks: list[str] = []
    email_import_status: str = ""
    email_import_progress: int = 0
    extracted_emails: list[dict] = []

    @rx.var
    def budget_pct_progress(self) -> int:
        return int(self.burn_rate.get("budget_pct", 0) * 100)

    def load_dashboard(self):
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

    def handle_flag_context(self, context: str):
        with rx.session() as session:
            txn = session.get(Transaction, self.flagged_txn["id"])
            if txn:
                txn.user_context = context
                txn.is_flagged = False
                session.commit()
        self.show_flag_prompt = False

    def handle_upload(self, files):
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
        """Fetch list of potential banks from Gmail inbox (last 1 year)."""
        self.processing = True
        self.email_import_status = "Connecting to Gmail... Please complete authentication in the browser popup."
        yield  # Yield to prevent WebSocket timeout
        
        try:
            from spendlens.services.gmail_service import get_gmail_service, list_potential_banks
            
            service = get_gmail_service()
            self.email_import_status = "✓ Gmail authenticated! Scanning for bank emails (last 1 year)..."
            yield  # Yield during authentication
            
            self.email_import_status = "🤖 Analyzing senders with AI to find transaction alerts..."
            yield  # Yield before LLM processing
            banks = list_potential_banks(service)
            
            self.available_banks = banks
            self.email_import_status = f"✓ Found {len(banks)} verified transaction senders from last 1 year. Select banks to import."
            
        except FileNotFoundError as e:
            self.email_import_status = f"Error: {str(e)}"
        except Exception as e:
            self.email_import_status = f"Error fetching banks: {str(e)}"
        finally:
            self.processing = False
            yield

    def import_from_email(self, banks: list[str]):
        """Import transactions from selected email senders."""
        if not banks:
            self.email_import_status = "Please select at least one bank sender"
            return
        
        self.processing = True
        self.selected_banks = banks
        total_banks = len(banks)
        self.email_import_status = f"Starting import from {total_banks} bank(s)..."
        yield
        
        try:
            from spendlens.services.gmail_service import get_gmail_service, get_emails_from_sender
            from spendlens.services.email_extraction import batch_extract_transactions
            
            service = get_gmail_service()
            all_emails = []
            
            # Fetch emails from each selected bank (last 1 year by default)
            for i, bank in enumerate(banks, 1):
                self.email_import_status = f"📧 Fetching from bank {i}/{total_banks}: {bank} (last 1 year)..."
                yield  # Yield to prevent WebSocket timeout
                emails = get_emails_from_sender(service, bank, max_results=500, last_year_only=True)
                all_emails.extend(emails)
                self.email_import_status = f"✓ Fetched {len(emails)} emails from {bank}"
                yield
            
            if not all_emails:
                self.email_import_status = "No emails found from selected banks"
                self.processing = False
                return
            
            # Extract transactions
            self.email_import_status = f"🔍 Extracting transactions from {len(all_emails)} emails using AI..."
            yield  # Yield to prevent WebSocket timeout
            extracted = batch_extract_transactions(all_emails)
            
            successful_extractions = sum(1 for t in extracted if t.get("success"))
            self.email_import_status = f"✓ Extracted {successful_extractions} transactions from {len(all_emails)} emails"
            yield  # Yield to prevent WebSocket timeout
            
            # Save to database
            self.email_import_status = "Saving transactions to database..."
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
                            
                            # Yield every 10 transactions to prevent timeout
                            if saved_count % 10 == 0:
                                self.email_import_status = f"Saving transactions to database... ({saved_count}/{total_to_save})"
                                yield
                        except Exception as e:
                            print(f"Error saving transaction: {e}")
                            continue
                
                session.commit()
            
            self.extracted_emails = extracted
            self.email_import_status = f"✓ Successfully imported {saved_count} transactions from {len(all_emails)} emails (last 1 year)"
            
            # Reload dashboard
            self.load_dashboard()
            
        except FileNotFoundError as e:
            self.email_import_status = f"Error: {str(e)}"
        except Exception as e:
            self.email_import_status = f"Error importing emails: {str(e)}"
        finally:
            self.processing = False
            yield
