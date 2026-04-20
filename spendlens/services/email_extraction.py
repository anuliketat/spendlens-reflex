"""
Email Transaction Extraction using OpenRouter API with Gemini Flash.
Uses API-based inference for transaction data extraction from emails.
"""

import os
import json
import asyncio
import httpx
import warnings
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Load client once
_client = None

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
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
    OPENROUTER_API_KEY = None

# Model configuration - Use Gemini Flash for all email processing tasks
USE_LLM_FILTER = os.getenv("USE_LLM_FILTER", "true").lower() == "true"

FILTER_MODEL_NAME = "google/gemini-3-flash-preview"
MODEL_NAME = "google/gemini-3-flash-preview"

if OPENROUTER_API_KEY:
    print("[LLM] Using Gemini Flash (OpenRouter API) for all email processing")
else:
    FILTER_MODEL_NAME = None
    MODEL_NAME = None
    print("[!] Using rule-based methods only (OPENROUTER_API_KEY not set)")


def _get_client():
    """Get OpenAI client for OpenRouter API."""
    global _client
    
    if _client is not None:
        return _client
    
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "Cannot initialize client: OPENROUTER_API_KEY is not set.\n"
            "Please set OPENROUTER_API_KEY in your .env file.\n"
            "Get token from: https://openrouter.ai/keys"
        )
    
    _client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    return _client


def extract_transaction_details(email_body: str, sender: str = "") -> Dict[str, Any]:
    """
    Extract transaction details from email body using Gemini Flash via OpenRouter API.
    
    Returns:
    {
        "date": "YYYY-MM-DD",
        "time": "HH:MM:SS",
        "amount": float,
        "type": "debit|credit|investment",
        "merchant": str,
        "description": str,
        "success": bool
    }
    """
    prompt = f"""Extract transaction details from this email into JSON format:
Email from: {sender}
Email content: {email_body[:1000]}

Extract ONLY these fields (return valid JSON):
{{
  "date": "YYYY-MM-DD or empty string",
  "time": "HH:MM or empty string",
  "amount": "numeric value or 0",
  "type": "debit or credit or investment or other",
  "merchant": "store/bank name or empty",
  "description": "brief description or empty"
}}

JSON Response:"""
    
    try:
        client = _get_client()
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts transaction details from emails in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        json_obj = _parse_json_response(response_text)
        
        # Validate and normalize
        result = _validate_transaction(json_obj)
        result["success"] = True
        return result
        
    except RuntimeError as e:
        if "OPENROUTER_API_KEY" in str(e):
            print(f"⚠️  {str(e)}")
            return {
                "date": "",
                "time": "",
                "amount": 0,
                "type": "other",
                "merchant": sender,
                "description": "LLM unavailable: OPENROUTER_API_KEY not configured",
                "success": False
            }
        raise
    except Exception as e:
        return {
            "date": "",
            "time": "",
            "amount": 0,
            "type": "other",
            "merchant": sender,
            "description": f"Error: {str(e)[:50]}",
            "success": False
        }


def _parse_json_response(response: str) -> Dict[str, Any]:
    """Extract and parse JSON from model response."""
    try:
        # Try direct JSON parse
        return json.loads(response)
    except:
        pass
    
    try:
        # Try extracting JSON from text
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    # Return empty structure if parsing fails
    return {
        "date": "",
        "time": "",
        "amount": 0,
        "type": "other",
        "merchant": "",
        "description": ""
    }


def _validate_transaction(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize transaction data."""
    result = {
        "date": str(data.get("date", "")).strip() or "",
        "time": str(data.get("time", "")).strip() or "",
        "amount": 0,
        "type": str(data.get("type", "other")).lower(),
        "merchant": str(data.get("merchant", "")).strip() or "",
        "description": str(data.get("description", "")).strip() or ""
    }
    
    # Parse amount
    try:
        amount_str = str(data.get("amount", "0")).strip()
        amount_str = ''.join(c for c in amount_str if c.isdigit() or c == '.')
        result["amount"] = float(amount_str) if amount_str else 0
    except:
        result["amount"] = 0
    
    # Normalize type
    if result["type"] not in ["debit", "credit", "investment"]:
        result["type"] = "other"
    
    return result


async def extract_transactions_async(emails: list, max_concurrent: int = 3) -> list:
    """
    Async batch extraction of transactions from multiple emails.
    Limits concurrent requests to avoid memory issues.
    """
    results = []
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def extract_with_semaphore(email):
        async with semaphore:
            return extract_transaction_details(
                email.get('body', email.get('snippet', '')),
                email.get('sender', '')
            )
    
    tasks = [extract_with_semaphore(email) for email in emails]
    results = await asyncio.gather(*tasks)
    
    return results


def batch_extract_transactions(emails: list, progress_callback=None) -> list:
    """
    Synchronous batch extraction for use in Reflex state.
    Processes emails sequentially to avoid memory spikes.
    
    Args:
        emails: List of email dictionaries
        progress_callback: Optional callback function to report progress (current, total)
    """
    results = []
    total = len(emails)
    
    for i, email in enumerate(emails):
        result = extract_transaction_details(
            email.get('body', email.get('snippet', '')),
            email.get('sender', '')
        )
        result['email_id'] = email.get('id', '')
        result['sender'] = email.get('sender', '')
        results.append(result)
        
        # Call progress callback every 5 emails to keep WebSocket alive
        if progress_callback and (i + 1) % 5 == 0:
            progress_callback(i + 1, total)
    
    return results


def suggest_search_patterns(subject_samples: list[str]) -> list[str]:
    """
    Use LLM to analyze email subjects and suggest optimal search patterns for finding transaction emails.
    This helps narrow down the search to only relevant patterns.
    
    Args:
        subject_samples: List of email subject lines to analyze
    
    Returns:
        List of suggested search patterns (e.g., ['subject:debit', 'subject:credit'])
    """
    if not subject_samples:
        return ['subject:debit', 'subject:credit', 'subject:UPI', 'subject:payment']
    
    if not OPENROUTER_API_KEY:
        print("[LLM] API key not set, using default patterns")
        return ['subject:debit', 'subject:credit', 'subject:UPI', 'subject:payment']
    
    # Take a sample of subjects (max 20) to analyze
    sample_subjects = subject_samples[:20]
    subjects_str = "\n".join([f"- {s}" for s in sample_subjects])
    
    prompt = f"""Analyze these email subject lines and suggest which Gmail search patterns would be most effective to find bank transaction emails.

Email subjects:
{subjects_str}

Suggested patterns to search for (return as JSON array):
- subject:debit (for debits)
- subject:credit (for credits)
- subject:UPI (for UPI transactions)
- subject:payment (for payments)
- subject:transaction (for general transactions)
- subject:spent (for spending)
- subject:alert (for alerts)
- subject:statement (for statements)

Return ONLY a JSON array of the top 3-5 most relevant patterns for these emails:
["pattern1", "pattern2", "pattern3"]

Response:"""

    try:
        client = _get_client()
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes email subjects to suggest Gmail search patterns."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=100,
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            import json
            patterns = json.loads(response_text)
            if isinstance(patterns, list) and len(patterns) > 0:
                print(f"[LLM] Suggested patterns: {patterns}")
                return patterns
        except:
            pass
        
        # Fallback: extract pattern-like strings
        import re
        patterns = re.findall(r'subject:\w+', response_text)
        if patterns:
            print(f"[LLM] Extracted patterns: {patterns}")
            return patterns[:5]
        
    except Exception as e:
        print(f"[LLM] Error suggesting patterns: {e}")
    
    # Fallback to default patterns
    return ['subject:debit', 'subject:credit', 'subject:UPI', 'subject:payment']


def filter_senders_with_llm(senders_data: list[dict]) -> list[str]:
    """
    Use Gemini Flash to filter sender emails and identify true transaction alerts via OpenRouter API.
    
    Args:
        senders_data: List of dicts with 'email', 'name', 'subjects', 'count'
    
    Returns:
        List of verified sender email addresses that are transaction-related
    """
    if not senders_data:
        return []
    
    if not USE_LLM_FILTER:
        print("⏭️  LLM filtering disabled (USE_LLM_FILTER=false), using rule-based only")
        return [s['email'] for s in senders_data]
    
    # Build a concise prompt with sender info
    sender_summaries = []
    for s in senders_data[:15]:  # Limit to top 15 for speed
        subjects_sample = s.get('subjects', [])[:2]  # First 2 subjects only
        subjects_str = " | ".join(subjects_sample) if subjects_sample else "N/A"
        summary = f"- {s['email']} ({s.get('name', 'Unknown')}): {subjects_str}"
        sender_summaries.append(summary)
    
    prompt = f"""You are a financial email classifier. Analyze these sender emails and identify ONLY the ones sending REAL BANK TRANSACTION ALERTS (debit, credit, UPI, payment confirmations). Ignore marketing, offers, newsletters, OTPs, and login alerts.

Senders:
{chr(10).join(sender_summaries)}

Return ONLY a JSON array of transaction sender emails:
["email1@domain.com", "email2@domain.com"]

Response:"""

    try:
        client = _get_client()
        
        response = client.chat.completions.create(
            model=FILTER_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that filters financial emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=256,
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            import json
            filtered_emails = json.loads(response_text)
            return filtered_emails if isinstance(filtered_emails, list) else []
        except:
            # Fallback: extract email-like strings
            import re
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', response_text)
            return emails
    except RuntimeError as e:
        if "OPENROUTER_API_KEY" in str(e):
            print(f"⚠️  {str(e)}")
            print("⚠  Using rule-based filtering instead")
            return [s['email'] for s in senders_data]
        raise
    except Exception as e:
        print(f"⚠ LLM filtering failed: {e}. Using rule-based results.")
        return [s['email'] for s in senders_data]
