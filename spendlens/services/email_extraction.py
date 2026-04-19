"""
Email Transaction Extraction using Fin-R1 model.
Uses local model inference for fast transaction data extraction from emails.
"""

import os
import json
import asyncio
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
import torch
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# Load environment variables from .env file
load_dotenv()

# Load model once
_model = None
_tokenizer = None

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is required. Set it in your .env file.")

# Model configuration
FAST_LLM_MODE = os.getenv("FAST_LLM_MODE", "false").lower() == "true"
USE_LLM_FILTER = os.getenv("USE_LLM_FILTER", "true").lower() == "true"

if FAST_LLM_MODE:
    # Fast 3.8B model for quick classification (loads ~5x faster)
    FILTER_MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"
    print("⚡ Using FAST mode: Phi-3-mini (3.8B parameters)")
else:
    # Accurate 32B model for best transaction extraction
    FILTER_MODEL_NAME = os.getenv("MODEL_NAME", "mlabonne/Fin-R1")
    print("🎯 Using ACCURATE mode: Fin-R1 (32B parameters)")

# For transaction extraction, always use Fin-R1 (more accurate)
MODEL_NAME = os.getenv("MODEL_NAME", "mlabonne/Fin-R1")


def _load_extraction_model():
    """Load Fin-R1 model with 4-bit quantization for extraction tasks."""
    global _model, _tokenizer
    
    if _model is not None:
        return _model, _tokenizer
    
    try:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        
        _tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            token=HF_TOKEN,
            trust_remote_code=True,
        )
        
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            quantization_config=quantization_config,
            device_map="auto",
            token=HF_TOKEN,
            trust_remote_code=True,
            torch_dtype=torch.float16,
        )
        _model.eval()
        print("✓ Loaded Fin-R1 for email extraction")
        return _model, _tokenizer
    except RuntimeError as e:
        if "flash_attention_2" in str(e).lower():
            print("⚠ Loading without FlashAttention-2...")
            _tokenizer = AutoTokenizer.from_pretrained(
                MODEL_NAME,
                token=HF_TOKEN,
                trust_remote_code=True,
            )
            _model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                quantization_config=quantization_config,
                device_map="auto",
                token=HF_TOKEN,
                trust_remote_code=True,
                torch_dtype=torch.float16,
            )
            _model.eval()
            return _model, _tokenizer
        raise


def extract_transaction_details(email_body: str, sender: str = "") -> Dict[str, Any]:
    """
    Extract transaction details from email body using Fin-R1.
    
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
        model, tokenizer = _load_extraction_model()
        
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.3,
                top_p=0.9,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()
        
        # Parse JSON response
        json_obj = _parse_json_response(response)
        
        # Validate and normalize
        result = _validate_transaction(json_obj)
        result["success"] = True
        return result
        
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


def batch_extract_transactions(emails: list) -> list:
    """
    Synchronous batch extraction for use in Reflex state.
    Processes emails sequentially to avoid memory spikes.
    """
    results = []
    for email in emails:
        result = extract_transaction_details(
            email.get('body', email.get('snippet', '')),
            email.get('sender', '')
        )
        result['email_id'] = email.get('id', '')
        result['sender'] = email.get('sender', '')
        results.append(result)
    
    return results


# Separate model instances for filtering (can be faster model)
_filter_model = None
_filter_tokenizer = None


def _load_filter_model():
    """Load model for sender filtering (can be smaller/faster than extraction model)."""
    global _filter_model, _filter_tokenizer
    
    if _filter_model is not None:
        return _filter_model, _filter_tokenizer
    
    if not USE_LLM_FILTER:
        raise RuntimeError("LLM filtering is disabled")
    
    try:
        # Use 4-bit quantization for faster loading
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        
        print(f"🤖 Loading filter model: {FILTER_MODEL_NAME}...")
        _filter_tokenizer = AutoTokenizer.from_pretrained(
            FILTER_MODEL_NAME,
            token=HF_TOKEN,
            trust_remote_code=True,
        )
        
        _filter_model = AutoModelForCausalLM.from_pretrained(
            FILTER_MODEL_NAME,
            quantization_config=quantization_config,
            device_map="auto",
            token=HF_TOKEN,
            trust_remote_code=True,
            torch_dtype=torch.float16,
        )
        _filter_model.eval()
        print(f"✓ Loaded filter model")
        return _filter_model, _filter_tokenizer
    except Exception as e:
        print(f"⚠ Failed to load filter model: {e}")
        raise


def filter_senders_with_llm(senders_data: list[dict]) -> list[str]:
    """
    Use LLM to filter sender emails and identify true transaction alerts.
    Uses FAST_LLM_MODE model (Phi-3-mini for speed, or Fin-R1 for accuracy).
    
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
        model, tokenizer = _load_filter_model()
        
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,  # Shorter for speed
                temperature=0.1,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()
        
        # Parse JSON array response
        try:
            # Try to extract JSON array from the response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                transaction_senders = json.loads(json_str)
                if isinstance(transaction_senders, list):
                    print(f"✓ LLM filtered {len(senders_data)} → {len(transaction_senders)} transaction senders")
                    return transaction_senders
        except json.JSONDecodeError:
            pass
        
        # Fallback: extract emails with regex
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_emails = re.findall(email_pattern, response)
        # Only return emails that were in the original list
        valid_emails = [e for e in found_emails if any(s['email'] == e for s in senders_data)]
        if valid_emails:
            print(f"✓ LLM found {len(valid_emails)} transaction senders (regex fallback)")
            return list(set(valid_emails))
        
        print("⚠ LLM returned no valid senders, using rule-based results")
        return [s['email'] for s in senders_data]
        
    except Exception as e:
        print(f"⚠ LLM filtering failed: {e}. Using rule-based results.")
        return [s['email'] for s in senders_data]
