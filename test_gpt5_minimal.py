#!/usr/bin/env python3
"""
Minimal GPT-5 API Integration Test
Tests the OpenAI Responses API support for GPT-5 models
"""

import os
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, '/home/user/fx-ai-autotrade')

# Load environment variables manually
from dotenv import load_dotenv
load_dotenv()

# Direct import to avoid __init__.py dependency issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "openai_client",
    "/home/user/fx-ai-autotrade/src/ai_analysis/openai_client.py"
)
openai_module = importlib.util.module_from_spec(spec)

# Load base_llm_client first
spec_base = importlib.util.spec_from_file_location(
    "base_llm_client",
    "/home/user/fx-ai-autotrade/src/ai_analysis/base_llm_client.py"
)
base_module = importlib.util.module_from_spec(spec_base)
sys.modules['src.ai_analysis.base_llm_client'] = base_module
spec_base.loader.exec_module(base_module)

# Now load openai_client
sys.modules['src.ai_analysis.openai_client'] = openai_module
spec.loader.exec_module(openai_module)

OpenAIClient = openai_module.OpenAIClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_gpt5_connection():
    """Test GPT-5 Responses API connection"""
    print("=" * 60)
    print("GPT-5 Responses API Integration Test")
    print("=" * 60)

    # Get OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key.startswith('your_'):
        print("❌ OPENAI_API_KEY not configured in .env file")
        print("   Please set a valid OpenAI API key to test GPT-5")
        return None

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
                print(f"   ✅ SUCCESS")
                print(f"   Response: {response[:200]}...")
                results[model_name] = True
            else:
                print(f"   ❌ FAILED - Empty response")
                results[model_name] = False

        except Exception as e:
            print(f"   ❌ FAILED - Error: {str(e)[:200]}")
            results[model_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    for model_name, description in test_models:
        status = "✅ PASS" if results.get(model_name, False) else "❌ FAIL"
        print(f"{status} - {description}")

    all_passed = all(results.values()) if results else False
    print("\n" + ("=" * 60))
    if all_passed:
        print("🎉 All tests PASSED!")
    elif results:
        print("⚠️  Some tests FAILED")
    print("=" * 60)

    return all_passed

if __name__ == '__main__':
    try:
        success = test_gpt5_connection()
        if success is None:
            print("\n⚠️  Test skipped (API key not configured)")
            sys.exit(0)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
