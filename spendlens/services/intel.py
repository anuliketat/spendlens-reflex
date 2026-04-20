import os
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch
import warnings

# Load environment variables from .env file
load_dotenv()

# HuggingFace token for model access (from environment)
hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    warnings.warn(
        "⚠️  HF_TOKEN environment variable is NOT set!\n"
        "   LLM-based features will not work.\n"
        "   To enable:\n"
        "   1. Copy .env.example to .env\n"
        "   2. Get token from https://huggingface.co/settings/tokens\n"
        "   3. Set HF_TOKEN in your .env file\n"
        "   4. Restart your application",
        UserWarning
    )
    hf_token = None
model_name = os.getenv("MODEL_NAME", "microsoft/Phi-3-medium-128k-instruct")

# Configure 4-bit quantization for memory efficiency
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

# Global model and tokenizer
_model = None
_tokenizer = None


def _load_model():
    """Lazy load model with 4-bit quantization and FlashAttention-2."""
    global _model, _tokenizer
    
    if _model is not None:
        return _model, _tokenizer
    
    if not hf_token:
        raise RuntimeError(
            "Cannot load model: HF_TOKEN is not set.\n"
            "Please set HF_TOKEN in your .env file.\n"
            "Get token from: https://huggingface.co/settings/tokens"
        )
    
    try:
        # Load tokenizer
        _tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            token=hf_token,
            trust_remote_code=True,
        )
        
        # Load model with optimizations
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            token=hf_token,
            trust_remote_code=True,
            attn_implementation="flash_attention_2",  # FlashAttention-2 for speed
            torch_dtype=torch.float16,
        )
        _model.eval()
        print(f"✓ Loaded {model_name} with 4-bit quantization and FlashAttention-2")
        return _model, _tokenizer
    except RuntimeError as e:
        if "flash_attention_2" in str(e).lower():
            print("⚠ FlashAttention-2 not available, loading without it...")
            _tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                token=hf_token,
                trust_remote_code=True,
            )
            _model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                device_map="auto",
                token=hf_token,
                trust_remote_code=True,
                torch_dtype=torch.float16,
            )
            _model.eval()
            return _model, _tokenizer
        raise
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            raise RuntimeError(f"Token authentication failed: HuggingFace token is expired or invalid. Please update HF_TOKEN in .env file.")
        elif "404" in error_msg or "Not Found" in error_msg:
            raise RuntimeError(f"Model '{model_name}' not found. Please check MODEL_NAME in .env file.")
        else:
            raise RuntimeError(f"Failed to load model '{model_name}': {error_msg}")


def get_verdict(
    burn_rate: float,
    top_txns: list,
    routine_total: float,
    oneoff_total: float,
) -> str:
    """Generate spending verdict using Fin-R1 with 4-bit quantization."""
    prompt = f"""Analyze the following spending data and provide a ONE sentence verdict (max 20 words):
- Monthly budget burn rate: {burn_rate:.0%}
- Routine spend: ₹{routine_total}
- One-off spend: ₹{oneoff_total}
- Top transactions: {top_txns}

Verdict:"""
    
    try:
        model, tokenizer = _load_model()
        
        # Tokenize with optimizations
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(model.device)
        
        # Generate with optimized settings
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.7,
                top_p=0.9,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        return response.strip().split('\n')[0]  # First line only
    except RuntimeError as e:
        error_msg = str(e)
        if "HF_TOKEN" in error_msg or "token" in error_msg.lower():
            return "🤖 LLM unavailable: HuggingFace token expired or invalid. Please update HF_TOKEN in .env file."
        elif "not a valid model identifier" in error_msg:
            return f"🤖 Model '{model_name}' not found. Please check MODEL_NAME in .env file."
        else:
            return f"🤖 LLM error: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        if "expired" in error_msg.lower():
            return "🤖 Token expired: Please refresh your HuggingFace token in .env file."
        else:
            return f"🤖 Error generating verdict: {error_msg}"


def get_intervention_cards(merchant_habits: list, budget_gaps: list) -> list[dict]:
    """Generate intervention cards using Fin-R1."""
    prompt = f"""Based on these financial habits, suggest 3 spending interventions:
Merchant habits: {merchant_habits}
Budget gaps: {budget_gaps}

Return a JSON array with cards containing: merchant_or_habit, pattern, monthly_saving_inr, action"""
    
    try:
        model, tokenizer = _load_model()
        
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
                temperature=0.7,
                top_p=0.9,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        
        # Try to parse JSON
        import json
        return json.loads(response)
    except Exception as e:
        return [{"merchant_or_habit": "Error", "pattern": str(e), "monthly_saving_inr": 0, "action": "Check logs"}]
