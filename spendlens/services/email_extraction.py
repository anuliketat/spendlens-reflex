"""
Email Transaction Extraction using Fin-R1 model.
Uses local model inference for fast transaction data extraction from emails.
"""

import json
import asyncio
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# Load model once
_model = None
_tokenizer = None

HF_TOKEN = "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"
MODEL_NAME = "mlabonne/Fin-R1"


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
