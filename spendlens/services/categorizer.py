LARGE_SPEND_MULTIPLIER = 3.0

MERCHANT_CLUSTERS = {
    "food_convenience": ["swiggy", "zomato", "blinkit", "dunzo", "zepto"],
    "subscriptions": ["netflix", "spotify", "prime", "hotstar", "youtube"],
    "transport": ["uber", "ola", "rapido", "irctc"],
}


def classify_routine_vs_oneoff(amount: float, median_spend: float) -> bool:
    return amount < (median_spend * LARGE_SPEND_MULTIPLIER)


def get_merchant_cluster(merchant: str) -> str | None:
    merchant_lower = merchant.lower()
    for cluster, merchants in MERCHANT_CLUSTERS.items():
        if any(m in merchant_lower for m in merchants):
            return cluster
    return None
