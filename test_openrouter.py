#!/usr/bin/env python
"""
Test OpenRouter API with DeepSeek and Gemini models
Uses OpenAI-compatible API format
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

print("=" * 80)
print("OPENROUTER API TESTING")
print("=" * 80)

# Get API key
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

if not openrouter_api_key:
    print("\n[X] ERROR: OPENROUTER_API_KEY not set!")
    print("   Set OPENROUTER_API_KEY in your .env file")
    print("   Get your key from: https://openrouter.ai/keys")
    exit(1)

print(f"\n[OK] OPENROUTER_API_KEY is set")
print(f"  Key (preview): {openrouter_api_key[:20]}...{openrouter_api_key[-10:]}")

# Initialize OpenAI client with OpenRouter base URL
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key,
)

# Test 1: DeepSeek Reasoning model
print("\n" + "=" * 80)
print("TEST 1: DEEPSEEK-REASONING MODEL")
print("=" * 80)

try:
    print("\n  Testing deepseek-r1 model (reasoning) with chain-of-thought...")
    response = client.chat.completions.create(
        model="deepseek/deepseek-r1",
        messages=[
            {"role": "system", "content": "You are a helpful financial assistant."},
            {"role": "user", "content": "What is 2+2? Answer briefly."}
        ],
        temperature=0.3,
        max_tokens=100,
        extra_body={
            "include_reasoning": True
        }
    )
    
    print(f"  [OK] DeepSeek R1 (reasoning) model invoked successfully!")
    print(f"    Response: {response.choices[0].message.content}")
    if hasattr(response.choices[0].message, 'reasoning') and response.choices[0].message.reasoning:
        print(f"    Reasoning (Chain of Thought): {response.choices[0].message.reasoning[:200]}...")
    else:
        print(f"    [!] No reasoning field in response")
    print("\n[OK] DEEPSEEK-R1 TEST PASSED")
    
except Exception as e:
    print(f"  [X] FAILED: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 2: DeepSeek V3.2 model
print("\n" + "=" * 80)
print("TEST 2: DEEPSEEK-V3.2 MODEL (STABLE)")
print("=" * 80)

try:
    print("\n  Testing deepseek-v3.2 model...")
    response = client.chat.completions.create(
        model="deepseek/deepseek-v3.2",
        messages=[
            {"role": "system", "content": "You are a helpful financial assistant."},
            {"role": "user", "content": "What is 2+2? Answer briefly."}
        ],
        temperature=0.3,
        max_tokens=100
    )
    
    print(f"  [OK] DeepSeek V3.2 model invoked successfully!")
    print(f"    Response: {response.choices[0].message.content}")
    print("\n[OK] DEEPSEEK-V3.2 TEST PASSED")
    
except Exception as e:
    print(f"  [X] FAILED: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 3: Gemini Flash model
print("\n" + "=" * 80)
print("TEST 3: GEMINI-FLASH MODEL")
print("=" * 80)

try:
    print("\n  Testing gemini-3-flash-preview model...")
    response = client.chat.completions.create(
        model="google/gemini-3-flash-preview",
        messages=[
            {"role": "system", "content": "You are a helpful financial assistant."},
            {"role": "user", "content": "What is 2+2? Answer briefly."}
        ],
        temperature=0.3,
        max_tokens=100
    )
    
    print(f"  [OK] Gemini Flash model invoked successfully!")
    print(f"    Response: {response.choices[0].message.content}")
    print("\n[OK] GEMINI-FLASH TEST PASSED")
    
except Exception as e:
    print(f"  [X] FAILED: {str(e)}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\n[OK] OpenRouter API testing completed!")
print("\nModel IDs used:")
print("  - DeepSeek R1 (reasoning): deepseek/deepseek-r1")
print("  - DeepSeek V3.2 (stable): deepseek/deepseek-v3.2")
print("  - Gemini Flash: google/gemini-3-flash-preview")
print("\n" + "=" * 80)
