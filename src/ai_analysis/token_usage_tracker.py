"""
トークン使用量追跡モジュール

AI APIの使用トークン数を記録・集計します。
"""
from typing import Dict, List
from collections import defaultdict
from datetime import datetime
import logging


class TokenUsageTracker:
    """
    トークン使用量を追跡するシングルトンクラス

    全てのLLM API呼び出しのトークン使用量を記録し、
    Phase別・プロバイダー別の統計を提供します。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.logger = logging.getLogger(__name__)
        self.usage_records: List[Dict] = []
        self._initialized = True

    def record_usage(
        self,
        phase: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        timestamp: datetime = None
    ):
        """
        トークン使用量を記録

        Args:
            phase: フェーズ名（例: "Phase 1", "Phase 2"など）
            provider: プロバイダー名（例: "gemini", "openai", "anthropic"）
            model: 使用したモデル名
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            timestamp: 記録時刻（省略時は現在時刻）
        """
        record = {
            'phase': phase,
            'provider': provider,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'timestamp': timestamp or datetime.now()
        }

        self.usage_records.append(record)

        self.logger.debug(
            f"Token usage recorded: {phase} - {provider} "
            f"(in: {input_tokens}, out: {output_tokens})"
        )

    def get_summary(self) -> Dict:
        """
        トークン使用量のサマリーを取得

        Returns:
            Dict: Phase別、プロバイダー別の統計情報
        """
        if not self.usage_records:
            return {
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_tokens': 0,
                'by_phase': {},
                'by_provider': {},
                'by_model': {},
                'call_count': 0
            }

        # Phase別集計
        by_phase = defaultdict(lambda: {'input': 0, 'output': 0, 'total': 0, 'calls': 0})
        for record in self.usage_records:
            phase = record['phase']
            by_phase[phase]['input'] += record['input_tokens']
            by_phase[phase]['output'] += record['output_tokens']
            by_phase[phase]['total'] += record['total_tokens']
            by_phase[phase]['calls'] += 1

        # プロバイダー別集計
        by_provider = defaultdict(lambda: {'input': 0, 'output': 0, 'total': 0, 'calls': 0})
        for record in self.usage_records:
            provider = record['provider']
            by_provider[provider]['input'] += record['input_tokens']
            by_provider[provider]['output'] += record['output_tokens']
            by_provider[provider]['total'] += record['total_tokens']
            by_provider[provider]['calls'] += 1

        # モデル別集計
        by_model = defaultdict(lambda: {'input': 0, 'output': 0, 'total': 0, 'calls': 0})
        for record in self.usage_records:
            model = record['model']
            by_model[model]['input'] += record['input_tokens']
            by_model[model]['output'] += record['output_tokens']
            by_model[model]['total'] += record['total_tokens']
            by_model[model]['calls'] += 1

        # 総計
        total_input = sum(r['input_tokens'] for r in self.usage_records)
        total_output = sum(r['output_tokens'] for r in self.usage_records)

        return {
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'total_tokens': total_input + total_output,
            'by_phase': dict(by_phase),
            'by_provider': dict(by_provider),
            'by_model': dict(by_model),
            'call_count': len(self.usage_records)
        }

    def print_summary(self):
        """トークン使用量サマリーを標準出力に表示"""
        summary = self.get_summary()

        print("=" * 80)
        print("トークン使用量レポート")
        print("=" * 80)
        print()

        # 総計
        print(f"総API呼び出し回数: {summary['call_count']:,}回")
        print(f"総入力トークン数:   {summary['total_input_tokens']:,} tokens")
        print(f"総出力トークン数:   {summary['total_output_tokens']:,} tokens")
        print(f"総トークン数:       {summary['total_tokens']:,} tokens")
        print()

        # Phase別
        if summary['by_phase']:
            print("-" * 80)
            print("Phase別使用量:")
            print("-" * 80)
            for phase, stats in sorted(summary['by_phase'].items()):
                print(f"{phase:20s}: {stats['calls']:3d}回 | "
                      f"入力: {stats['input']:8,} | "
                      f"出力: {stats['output']:8,} | "
                      f"合計: {stats['total']:8,} tokens")
            print()

        # プロバイダー別
        if summary['by_provider']:
            print("-" * 80)
            print("プロバイダー別使用量:")
            print("-" * 80)
            for provider, stats in sorted(summary['by_provider'].items()):
                print(f"{provider.upper():20s}: {stats['calls']:3d}回 | "
                      f"入力: {stats['input']:8,} | "
                      f"出力: {stats['output']:8,} | "
                      f"合計: {stats['total']:8,} tokens")
            print()

        # モデル別
        if summary['by_model']:
            print("-" * 80)
            print("モデル別使用量:")
            print("-" * 80)
            for model, stats in sorted(summary['by_model'].items()):
                print(f"{model:40s}: {stats['calls']:3d}回 | "
                      f"入力: {stats['input']:8,} | "
                      f"出力: {stats['output']:8,} | "
                      f"合計: {stats['total']:8,} tokens")
            print()

        print("=" * 80)

    def reset(self):
        """記録をリセット"""
        self.usage_records = []
        self.logger.info("Token usage records reset")


# グローバルインスタンス
_tracker = TokenUsageTracker()

def get_token_tracker() -> TokenUsageTracker:
    """トークン追跡インスタンスを取得"""
    return _tracker
