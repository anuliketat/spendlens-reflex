import os
from dotenv import load_dotenv
from openai import OpenAI
import warnings

# Load environment variables from .env file
load_dotenv()

# OpenRouter API key for model access (from environment)
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_api_key:
    warnings.warn(
        "⚠️  OPENROUTER_API_KEY environment variable is NOT set!\n"
        "   LLM-based features will not work.\n"
        "   To enable:\n"
        "   1. Copy .env.example to .env\n"
        "   2. Get token from https://openrouter.ai/keys\n"
        "   3. Set OPENROUTER_API_KEY in your .env file\n"
        "   4. Restart your application",
        UserWarning
    )
    openrouter_api_key = None

# DeepSeek V3.2 is used for analytics and insights
model_name = os.getenv("ANALYTICS_MODEL", "deepseek/deepseek-v3.2")

# Global OpenAI client
_client = None


def _get_client():
    """Get OpenAI client for OpenRouter API."""
    global _client
    
    if _client is not None:
        return _client
    
    if not openrouter_api_key:
        raise RuntimeError(
            "Cannot initialize client: OPENROUTER_API_KEY is not set.\n"
            "Please set OPENROUTER_API_KEY in your .env file.\n"
            "Get token from: https://openrouter.ai/keys"
        )
    
    _client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_api_key,
    )
    return _client


def get_verdict(
    burn_rate: float,
    top_txns: list,
    routine_total: float,
    oneoff_total: float,
) -> str:
    """Generate spending verdict using DeepSeek V3.2 via OpenRouter API."""
    prompt = f"""Analyze the following spending data and provide a ONE sentence verdict (max 20 words):
- Monthly budget burn rate: {burn_rate:.0%}
- Routine spend: ₹{routine_total}
- One-off spend: ₹{oneoff_total}
- Top transactions: {top_txns}

Verdict:"""
    
    try:
        client = _get_client()
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful financial assistant that provides brief spending verdicts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=50,
        )
        
        return response.choices[0].message.content.strip()
    except RuntimeError as e:
        error_msg = str(e)
        if "OPENROUTER_API_KEY" in error_msg or "token" in error_msg.lower():
            return "[LLM] LLM unavailable: OpenRouter API key is not set. Please update OPENROUTER_API_KEY in .env file."
        else:
            return f"[LLM] LLM error: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        return f"[LLM] Error generating verdict: {error_msg}"


def get_intervention_cards(merchant_habits: list, budget_gaps: list) -> list[dict]:
    """Generate intervention cards using DeepSeek V3.2 via OpenRouter API."""
    prompt = f"""Based on these financial habits, suggest 3 spending interventions:
Merchant habits: {merchant_habits}
Budget gaps: {budget_gaps}

Return a JSON array with cards containing: merchant_or_habit, pattern, monthly_saving_inr, action"""
    
    try:
        client = _get_client()
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful financial assistant that provides spending intervention suggestions in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200,
        )
        
        # Try to parse JSON
        import json
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return [{"merchant_or_habit": "Error", "pattern": str(e), "monthly_saving_inr": 0, "action": "Check logs"}]
