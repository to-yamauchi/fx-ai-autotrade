#!/usr/bin/env python3
"""
GPT-5 Response Structure Debug Script
実際のGPT-5レスポンス構造を確認するためのデバッグスクリプト
"""

import os
import sys
import logging

# ログレベルをDEBUGに設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from dotenv import load_dotenv
load_dotenv()

# Direct import
import importlib.util
spec_base = importlib.util.spec_from_file_location(
    "base_llm_client",
    "/home/user/fx-ai-autotrade/src/ai_analysis/base_llm_client.py"
)
base_module = importlib.util.module_from_spec(spec_base)
sys.modules['src.ai_analysis.base_llm_client'] = base_module
spec_base.loader.exec_module(base_module)

spec = importlib.util.spec_from_file_location(
    "openai_client",
    "/home/user/fx-ai-autotrade/src/ai_analysis/openai_client.py"
)
openai_module = importlib.util.module_from_spec(spec)
sys.modules['src.ai_analysis.openai_client'] = openai_module
spec.loader.exec_module(openai_module)

OpenAIClient = openai_module.OpenAIClient

def debug_gpt5():
    """GPT-5のレスポンス構造をデバッグ"""
    print("=" * 70)
    print("GPT-5 Response Structure Debug")
    print("=" * 70)

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key.startswith('your_'):
        print("❌ OPENAI_API_KEY not configured")
        return

    client = OpenAIClient(api_key=api_key)

    print("\nTesting with gpt-5-nano...")
    try:
        response = client.generate_response(
            prompt="Say OK",
            model="gpt-5-nano",
            max_tokens=50,
            phase="Debug Test"
        )
        print(f"\n✅ Success! Response: {response}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_gpt5()
