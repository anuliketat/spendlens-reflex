#!/usr/bin/env python
"""
Comprehensive LLM Testing Script
Tests both Fin-R1 and email extraction LLMs
"""

import os
import sys
from dotenv import load_dotenv
import torch
import traceback

# Load environment variables
load_dotenv()

print("=" * 80)
print("LLM CONFIGURATION & TESTING")
print("=" * 80)

# Check environment variables
print("\n1. CHECKING ENVIRONMENT VARIABLES")
print("-" * 80)

hf_token = os.getenv("HF_TOKEN")
fast_mode = os.getenv("FAST_LLM_MODE", "false").lower() == "true"
use_llm_filter = os.getenv("USE_LLM_FILTER", "true").lower() == "true"
model_name = os.getenv("MODEL_NAME", "mlabonne/Fin-R1")

print(f"✓ HF_TOKEN set: {'YES' if hf_token else 'NO'}")
print(f"  Token preview: {hf_token[:20]}...{hf_token[-10:] if hf_token and len(hf_token) > 30 else 'N/A'}")
print(f"✓ FAST_LLM_MODE: {fast_mode}")
print(f"✓ USE_LLM_FILTER: {use_llm_filter}")
print(f"✓ MODEL_NAME: {model_name}")

# Check GPU/CUDA availability
print("\n2. CHECKING GPU/COMPUTE RESOURCES")
print("-" * 80)
print(f"✓ CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✓ CUDA Version: {torch.version.cuda}")
    print(f"✓ GPU Count: {torch.cuda.device_count()}")
    print(f"✓ GPU Name: {torch.cuda.get_device_name(0)}")
    print(f"✓ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

print(f"✓ PyTorch Version: {torch.__version__}")

# Test Fin-R1 model loading
print("\n3. TESTING MODEL LOADING")
print("-" * 80)

if not hf_token:
    print("❌ ERROR: HF_TOKEN not set!")
    print("   Set HF_TOKEN in your .env file to use the models")
    sys.exit(1)

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    print("✓ Transformers library imported successfully")

    # Try loading the configured model
    print(f"\n  Attempting to load {model_name}...")

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )
    print("  ✓ BitsAndBytes quantization config created")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        token=hf_token,
        trust_remote_code=True,
    )
    print("  ✓ Tokenizer loaded successfully")

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quantization_config,
        device_map="auto",
        token=hf_token,
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
    model.eval()
    print(f"  ✓ Model loaded successfully (device: {next(model.parameters()).device})")

    # Test inference
    print("\n  Testing inference...")
    test_prompt = "What is 2+2? Answer briefly:"

    inputs = tokenizer(test_prompt, return_tensors="pt").to(model.device)
    print(f"    ✓ Input tokenized (length: {inputs['input_ids'].shape[1]})")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=20,
            temperature=0.3,
            top_p=0.9,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    print(f"    ✓ Inference successful!")
    print(f"    Response: {response.strip()}")
    print(f"\n✓ {model_name.upper()} MODEL TEST PASSED")

except Exception as e:
    print(f"❌ FAILED TO LOAD {model_name.upper()}: {str(e)}")
    traceback.print_exc()

# Test email extraction module
print("\n4. TESTING EMAIL EXTRACTION MODULE")
print("-" * 80)

try:
    from spendlens.services.email_extraction import extract_transaction_details
    print("✓ email_extraction module imported successfully")
    
    # Test email extraction
    test_email = """
    Dear Customer,
    
    Your account has been debited with ₹5,000 on 2024-04-20 at 14:30:45
    towards online shopping purchase from Amazon.
    
    Transaction details:
    Amount: ₹5,000
    Merchant: Amazon.in
    Reference: TXN123456
    
    Thank you,
    Your Bank
    """
    
    print("\n  Testing extract_transaction_details()...")
    result = extract_transaction_details(test_email, sender="alerts@bank.com")
    print(f"  ✓ Extraction successful!")
    print(f"    Result: {result}")
    
    if result.get("success"):
        print("\n✓ EMAIL EXTRACTION TEST PASSED")
    else:
        print("\n⚠ Email extraction returned success=False")
        
except Exception as e:
    print(f"❌ FAILED: {str(e)}")
    import traceback
    traceback.print_exc()

# Test intel module (get_verdict)
print("\n5. TESTING INTEL MODULE (VERDICT GENERATION)")
print("-" * 80)

try:
    from spendlens.services.intel import get_verdict
    print("✓ intel module imported successfully")
    
    print("\n  Testing get_verdict()...")
    verdict = get_verdict(
        burn_rate=0.75,
        top_txns=[{"merchant": "Starbucks", "amount": 200}],
        routine_total=15000,
        oneoff_total=5000
    )
    print(f"  ✓ Verdict generation successful!")
    print(f"    Verdict: {verdict}")
    print("\n✓ INTEL MODULE TEST PASSED")
    
except Exception as e:
    print(f"❌ FAILED: {str(e)}")
    import traceback
    traceback.print_exc()

# Test gmail filter
print("\n6. TESTING GMAIL FILTER (LLM-based)")
print("-" * 80)

try:
    from spendlens.services.email_extraction import filter_senders_with_llm
    print("✓ filter_senders_with_llm imported successfully")
    
    # Test with sample data
    test_senders = [
        {
            "email": "alerts@hdfc.co.in",
            "name": "HDFC Bank",
            "subjects": ["Debit alert", "Payment received"]
        },
        {
            "email": "info@example.com",
            "name": "Example",
            "subjects": ["Newsletter", "Update"]
        }
    ]
    
    print("\n  Testing filter_senders_with_llm()...")
    filtered = filter_senders_with_llm(test_senders)
    print(f"  ✓ Filtering successful!")
    print(f"    Filtered senders: {filtered}")
    print("\n✓ GMAIL FILTER TEST PASSED")
    
except Exception as e:
    print(f"⚠ FAILED (this may be optional): {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\n✓ All critical tests completed!")
print("\nNOTE: If any tests failed:")
print("  1. Ensure HF_TOKEN is set in your .env file")
print("  2. Check internet connection (for model downloads)")
print("  3. Ensure sufficient VRAM is available (Phi-3: ~8GB, Fin-R1: ~24GB)")
print("  4. Set FAST_LLM_MODE=true in .env for lighter models")
print("  5. Check MODEL_NAME in .env for correct model identifier")
print("\n" + "=" * 80)
