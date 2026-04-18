import pandas as pd


def compute_burn_rate(
    spent: float,
    budget: float,
    day_of_month: int,
    days_in_month: int,
) -> dict:
    budget_pct = spent / budget if budget else 0
    time_pct = day_of_month / days_in_month
    if budget_pct <= time_pct:
        status = "on_track"
    elif budget_pct < time_pct + 0.1:
        status = "at_risk"
    else:
        status = "overshooting"
    return {
        "budget_pct": budget_pct,
        "time_pct": time_pct,
        "status": status,
    }


def compute_merchant_habits(transactions: list) -> list:
    if not transactions:
        return []
    df = pd.DataFrame([t.__dict__ for t in transactions])
    grouped = (
        df.groupby("merchant")
        .agg(count=("amount", "count"), total=("amount", "sum"))
        .reset_index()
    )
    grouped["annual_projection"] = grouped["total"] * 12
    return (
        grouped.sort_values("total", ascending=False)
        .head(10)
        .to_dict("records")
    )


def compute_category_drift(transactions: list, months: int = 3) -> list:
    if not transactions:
        return []
    df = pd.DataFrame([t.__dict__ for t in transactions])
    df["month"] = pd.to_datetime(df["datetime"]).dt.to_period("M")
    pivot = df.groupby(["month", "category"])["amount"].sum().unstack(fill_value=0)
    return pivot.pct_change().tail(months).to_dict()
