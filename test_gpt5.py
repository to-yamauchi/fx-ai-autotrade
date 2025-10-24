#!/usr/bin/env python3
"""
GPT-5 API Integration Test
Tests the OpenAI Responses API support for GPT-5 models
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the Python path
sys.path.insert(0, '/home/user/fx-ai-autotrade')

from src.ai_analysis.openai_client import OpenAIClient

def test_gpt5_connection():
    """Test GPT-5 Responses API connection"""
    print("=" * 60)
    print("GPT-5 Responses API Integration Test")
    print("=" * 60)

    # Get OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return False

    # Test models
    test_models = [
        ('gpt-5-nano', 'GPT-5 Nano (Responses API)'),
        ('gpt-5-mini', 'GPT-5 Mini (Responses API)'),
        ('gpt-4o', 'GPT-4o (Chat Completions API)'),
    ]

    client = OpenAIClient(api_key=api_key)

    results = {}
    for model_name, description in test_models:
        print(f"\n🔌 Testing {description}...")
        print(f"   Model: {model_name}")

        try:
            # Test with a simple prompt
            response = client.generate_response(
                prompt="Hello, this is a connection test. Please respond with 'OK'.",
                model=model_name,
                max_tokens=50,
                phase="GPT-5 Test"
            )

            if response and len(response) > 0:
                print(f"   ✅ SUCCESS - Response: {response[:100]}...")
                results[model_name] = True
            else:
                print(f"   ❌ FAILED - Empty response")
                results[model_name] = False

        except Exception as e:
            print(f"   ❌ FAILED - Error: {e}")
            results[model_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    for model_name, description in test_models:
        status = "✅ PASS" if results.get(model_name, False) else "❌ FAIL"
        print(f"{status} - {description}")

    all_passed = all(results.values())
    print("\n" + ("=" * 60))
    if all_passed:
        print("🎉 All tests PASSED!")
    else:
        print("⚠️  Some tests FAILED")
    print("=" * 60)

    return all_passed

if __name__ == '__main__':
    try:
        success = test_gpt5_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
