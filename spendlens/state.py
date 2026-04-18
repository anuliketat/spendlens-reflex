import reflex as rx
from spendlens.models import Transaction
from spendlens.services.analytics import compute_burn_rate, compute_merchant_habits
from spendlens.services.gemini import get_verdict


class AppState(rx.State):
    transactions: list = []
    burn_rate: dict = {}
    verdict: str = ""
    merchant_habits: list = []
    interventions: list = []
    archetype: dict = {}
    budget: dict = {}
    flagged_txn: dict = {}
    show_flag_prompt: bool = False

    def load_dashboard(self):
        with rx.session() as session:
            self.transactions = session.exec(
                rx.select(Transaction)
            ).all()

        total_spent = sum(t.amount for t in self.transactions)
        monthly_budget = self.budget.get("total", 50000)
        from datetime import datetime
        import calendar
        now = datetime.now()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        self.burn_rate = compute_burn_rate(
            total_spent, monthly_budget, now.day, days_in_month
        )

        top_txns = sorted(self.transactions, key=lambda t: t.amount, reverse=True)[:5]
        top_txns_display = [
            {"merchant": t.merchant, "amount": t.amount} for t in top_txns
        ]
        routine_total = sum(t.amount for t in self.transactions if t.is_routine)
        oneoff_total = sum(t.amount for t in self.transactions if not t.is_routine)

        try:
            self.verdict = get_verdict(
                self.burn_rate.get("budget_pct", 0),
                top_txns_display,
                routine_total,
                oneoff_total,
            )
        except Exception:
            self.verdict = "No Gemini API key configured."

        self.merchant_habits = compute_merchant_habits(self.transactions)

    def handle_flag_context(self, context: str):
        with rx.session() as session:
            txn = session.get(Transaction, self.flagged_txn["id"])
            if txn:
                txn.user_context = context
                txn.is_flagged = False
                session.commit()
        self.show_flag_prompt = False
