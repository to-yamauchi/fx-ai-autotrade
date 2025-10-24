#!/usr/bin/env python3
"""
GPT-5 Detailed Debug Script
GPT-5レスポンス構造を詳細に調査
"""

import os
import sys
import logging
from dotenv import load_dotenv

# ログレベルをDEBUGに設定して詳細情報を表示
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

# OpenAI SDKを直接使用してテスト
from openai import OpenAI

def test_gpt5_direct():
    """GPT-5 APIを直接テスト"""
    print("=" * 70)
    print("GPT-5 Direct API Test")
    print("=" * 70)

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key.startswith('your_'):
        print("❌ OPENAI_API_KEY not configured")
        return

    client = OpenAI(api_key=api_key)

    print("\n📞 Calling GPT-5 Responses API...")
    try:
        response = client.responses.create(
            model="gpt-5-nano",
            input=[
                {"type": "message", "role": "user", "content": "Say 'Hello World'"}
            ],
            text={
                "format": {"type": "text"},
                "verbosity": "medium"
            },
            reasoning={
                "effort": "medium",
                "summary": "auto"
            },
            max_output_tokens=100
        )

        print(f"\n✅ Response received!")
        print(f"Response type: {type(response)}")
        print(f"Response ID: {response.id}")
        print(f"Response status: {response.status}")
        print(f"Response model: {response.model}")

        # output配列の内容を表示
        print(f"\nOutput array length: {len(response.output)}")
        for i, output_item in enumerate(response.output):
            print(f"\n--- Output[{i}] ---")
            print(f"  Type: {output_item.type}")
            if hasattr(output_item, 'role'):
                print(f"  Role: {output_item.role}")
            if hasattr(output_item, 'content'):
                print(f"  Content length: {len(output_item.content)}")
                for j, content_item in enumerate(output_item.content):
                    print(f"\n  --- Content[{j}] ---")
                    print(f"    Type: {content_item.type}")
                    if hasattr(content_item, 'text'):
                        print(f"    Text: {content_item.text}")
                    # すべての属性を表示
                    attrs = [attr for attr in dir(content_item) if not attr.startswith('_')]
                    print(f"    Attributes: {attrs}")

        # output_textプロパティを確認
        print(f"\n--- output_text property ---")
        if hasattr(response, 'output_text'):
            output_text = response.output_text
            print(f"output_text: '{output_text}'")
            print(f"output_text length: {len(output_text)}")
        else:
            print("No output_text property")

        # usageを表示
        if hasattr(response, 'usage'):
            print(f"\n--- Usage ---")
            print(f"Total tokens: {response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 'N/A'}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_gpt5_direct()
