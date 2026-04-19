import os
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

# Load environment variables from .env file
load_dotenv()

# HuggingFace token for model access (from environment)
hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    raise ValueError("HF_TOKEN environment variable is required. Set it in your .env file.")
model_name = "mlabonne/Fin-R1"

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
    except Exception as e:
        return f"Error generating verdict: {str(e)}"


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
