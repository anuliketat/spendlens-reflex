import os
import json
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
model = genai.GenerativeModel("gemini-1.5-flash")


def get_verdict(
    burn_rate: float,
    top_txns: list,
    routine_total: float,
    oneoff_total: float,
) -> str:
    prompt = f"""
    User's monthly budget burn rate: {burn_rate:.0%}
    Routine spend this month: ₹{routine_total}
    One-off/unplanned spend: ₹{oneoff_total}
    Top transactions: {top_txns}
    Write ONE sentence (max 20 words) summarising the user's spending posture today.
    Be direct. No filler words.
    """
    return model.generate_content(prompt).text.strip()


def get_intervention_cards(merchant_habits: list, budget_gaps: list) -> list[dict]:
    prompt = f"""
    Merchant habits: {merchant_habits}
    Budget overruns: {budget_gaps}
    Return a JSON array of 5 intervention cards. Each card has:
    - merchant_or_habit (str)
    - pattern (str, 1 sentence)
    - monthly_saving_inr (int)
    - action (str, 1 sentence, specific)
    Only JSON. No markdown.
    """
    raw = model.generate_content(prompt).text.strip()
    return json.loads(raw)


def get_archetype(
    top_categories: list,
    top_merchants: list,
    spend_pattern: str,
) -> dict:
    prompt = f"""
    Top categories: {top_categories}
    Top merchants: {top_merchants}
    Spend pattern: {spend_pattern}
    Return JSON with:
    - label (str, 2-3 word archetype name)
    - summary (str, 2 sentences explaining the archetype)
    Only JSON. No markdown.
    """
    raw = model.generate_content(prompt).text.strip()
    return json.loads(raw)
