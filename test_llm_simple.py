#!/usr/bin/env python
"""
Simple LLM Test - Check model loading without actually loading full models
"""

import os
import sys
from dotenv import load_dotenv

print("=" * 80)
print("LLM DIAGNOSTICS")
print("=" * 80)

# Load environment variables
load_dotenv()

print("\n1. ENVIRONMENT VARIABLE CHECK")
print("-" * 80)

hf_token = os.getenv("HF_TOKEN")
fast_mode = os.getenv("FAST_LLM_MODE", "false").lower() == "true"
use_llm_filter = os.getenv("USE_LLM_FILTER", "true").lower() == "true"

if hf_token:
    print(f"✓ HF_TOKEN is set")
    print(f"  Token (preview): {hf_token[:20]}...{hf_token[-10:]}")
else:
    print(f"❌ HF_TOKEN is NOT set")
    print(f"\n  This is required for LLM models to work!")
    print(f"\n  To fix:")
    print(f"    1. Get a token from https://huggingface.co/settings/tokens")
    print(f"    2. Copy .env.example to .env")
    print(f"    3. Replace 'your_huggingface_token_here' with your token")
    print(f"    4. Restart your application")

print(f"\nOther settings:")
print(f"  FAST_LLM_MODE: {fast_mode} (use lightweight Phi-3 instead of Fin-R1)")
print(f"  USE_LLM_FILTER: {use_llm_filter} (whether to use LLM for bank filtering)")

# Check if transformers library is available
print("\n2. DEPENDENCIES CHECK")
print("-" * 80)

deps = {
    "transformers": False,
    "torch": False,
    "bitsandbytes": False,
    "google-auth": False,
    "dotenv": False,
}

for dep in deps:
    try:
        if dep == "google-auth":
            import google.auth
        elif dep == "dotenv":
            import dotenv
        else:
            __import__(dep.replace("-", "_"))
        print(f"✓ {dep}")
        deps[dep] = True
    except ImportError:
        print(f"❌ {dep} - NOT installed")

missing = [k for k, v in deps.items() if not v]
if missing:
    print(f"\n  Missing dependencies: {', '.join(missing)}")
    print(f"  Install with: pip install {' '.join(missing)}")

# Check which LLM functions would fail
print("\n3. LLM FUNCTION AVAILABILITY CHECK")
print("-" * 80)

functions_status = {}

# Check intel module
print("\nIntel module (get_verdict, interventions):")
try:
    from spendlens.services.intel import get_verdict, get_intervention_cards
    print("  ✓ Functions are importable")
    functions_status["intel"] = "OK"
    if not hf_token:
        print("  ⚠ But will FAIL at runtime without HF_TOKEN")
        functions_status["intel"] = "NEEDS_TOKEN"
except Exception as e:
    print(f"  ❌ Import failed: {str(e)}")
    functions_status["intel"] = "FAILED"

# Check email extraction
print("\nEmail extraction module (extract_transaction_details):")
try:
    from spendlens.services.email_extraction import extract_transaction_details, batch_extract_transactions
    print("  ✓ Functions are importable")
    functions_status["email_extraction"] = "OK"
    if not hf_token:
        print("  ⚠ But will FAIL at runtime without HF_TOKEN")
        functions_status["email_extraction"] = "NEEDS_TOKEN"
except Exception as e:
    print(f"  ❌ Import failed: {str(e)}")
    functions_status["email_extraction"] = "FAILED"

# Check gmail filter
print("\nGmail filter (filter_senders_with_llm):")
try:
    from spendlens.services.email_extraction import filter_senders_with_llm
    print("  ✓ Function is importable")
    functions_status["gmail_filter"] = "OK"
    if not hf_token:
        print("  ⚠ But will FAIL at runtime without HF_TOKEN")
        functions_status["gmail_filter"] = "NEEDS_TOKEN"
except Exception as e:
    print(f"  ❌ Import failed: {str(e)}")
    functions_status["gmail_filter"] = "FAILED"

# Summary
print("\n" + "=" * 80)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 80)

if hf_token:
    print("\n✓ HF_TOKEN is configured. LLMs should be ready to use.")
    print("\nTo test actual inference, run:")
    print("  python test_llm.py")
else:
    print("\n❌ HF_TOKEN is NOT set. LLM functions will fail at runtime.")
    print("\nTo enable LLMs:")
    print("  1. Create .env file (copy from .env.example)")
    print("  2. Get HF_TOKEN from https://huggingface.co/settings/tokens")
    print("  3. Update HF_TOKEN in .env file")
    print("  4. Restart your application")

print("\nOptional configuration:")
print("  - Set FAST_LLM_MODE=true to use Phi-3 (lighter, faster, less accurate)")
print("  - Set USE_LLM_FILTER=false to skip LLM-based bank filtering")
print("  - Set USE_LLM_FILTER=true to use LLM for better bank detection")

print("\n" + "=" * 80)
