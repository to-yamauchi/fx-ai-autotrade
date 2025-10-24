#!/usr/bin/env python3
"""
GPT-5 models comparison test
gpt-5-miniとgpt-5-nanoの違いを調査
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def test_model(model_name):
    """指定されたモデルをテスト"""
    print(f"\n{'=' * 70}")
    print(f"Testing: {model_name}")
    print('=' * 70)

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key.startswith('your_'):
        print("❌ OPENAI_API_KEY not configured")
        return False

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=model_name,
            input=[
                {"type": "message", "role": "user", "content": "Say OK"}
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
        print(f"  Response ID: {response.id}")
        print(f"  Status: {response.status}")
        print(f"  Model: {response.model}")

        # output配列
        if hasattr(response, 'output'):
            print(f"\n  Output: {response.output}")
            print(f"  Output length: {len(response.output) if response.output else 0}")

            if response.output:
                for i, item in enumerate(response.output):
                    print(f"\n  Output[{i}]:")
                    print(f"    Type: {item.type if hasattr(item, 'type') else 'N/A'}")
                    print(f"    ID: {item.id if hasattr(item, 'id') else 'N/A'}")

                    if hasattr(item, 'role'):
                        print(f"    Role: {item.role}")

                    if hasattr(item, 'content'):
                        print(f"    Content: {item.content}")
                        print(f"    Content length: {len(item.content) if item.content else 0}")

                        if item.content:
                            for j, content in enumerate(item.content):
                                print(f"\n    Content[{j}]:")
                                print(f"      Type: {content.type if hasattr(content, 'type') else 'N/A'}")
                                if hasattr(content, 'text'):
                                    print(f"      Text: '{content.text}'")
                                    print(f"      Text length: {len(content.text)}")
        else:
            print(f"\n  ⚠️  No 'output' attribute")

        # output_textプロパティ
        if hasattr(response, 'output_text'):
            try:
                output_text = response.output_text
                print(f"\n  output_text: '{output_text}'")
                print(f"  output_text length: {len(output_text)}")
            except Exception as e:
                print(f"\n  ⚠️  Error accessing output_text: {e}")
        else:
            print(f"\n  ⚠️  No 'output_text' property")

        # usage
        if hasattr(response, 'usage') and response.usage:
            print(f"\n  Usage:")
            print(f"    Total tokens: {response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 'N/A'}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    models = ['gpt-5-mini', 'gpt-5-nano']
    results = {}

    for model in models:
        results[model] = test_model(model)

    print(f"\n{'=' * 70}")
    print("Summary:")
    print('=' * 70)
    for model, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {model}")
