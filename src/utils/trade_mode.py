"""
========================================
トレードモード管理モジュール
========================================

ファイル名: trade_mode.py
パス: src/utils/trade_mode.py

【概要】
トレードモード（backtest/demo/live）の管理と設定を提供します。
各モードに応じた適切なデータソース、テーブル名、MT5接続情報を返します。

【モード】
- backtest: 過去データでのシミュレーション（data/tick_data使用）
- demo: リアルタイムデータでDEMO口座取引（MT5リアルタイム取得）
- live: リアルタイムデータで本番口座取引（MT5リアルタイム取得）

【作成日】2025-10-23
"""

import os
from enum import Enum
from typing import Dict, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()


class TradeMode(Enum):
    """トレードモード列挙型"""
    BACKTEST = "backtest"
    DEMO = "demo"
    LIVE = "live"


class TradeModeConfig:
    """
    トレードモード設定クラス

    環境変数からモード設定を読み取り、各モードに応じた設定を提供します。
    """

    def __init__(self):
        """初期化"""
        # 環境変数からモードを取得
        mode_str = os.getenv('TRADE_MODE', 'demo')

        # 値をクリーンアップ（前後の空白除去、コメント除去、小文字変換）
        if mode_str:
            # コメント（#）以降を削除
            if '#' in mode_str:
                mode_str = mode_str.split('#')[0]
            # 前後の空白を除去して小文字に変換
            mode_str = mode_str.strip().lower()
        else:
            mode_str = 'demo'

        # モードの検証
        if mode_str not in ['backtest', 'demo', 'live']:
            raise ValueError(
                f"Invalid TRADE_MODE: '{mode_str}'. "
                f"Must be one of: backtest, demo, live"
            )

        self.mode = TradeMode(mode_str)

    def get_mode(self) -> TradeMode:
        """
        現在のトレードモードを取得

        Returns:
            TradeMode: 現在のモード
        """
        return self.mode

    def is_backtest(self) -> bool:
        """バックテストモードか判定"""
        return self.mode == TradeMode.BACKTEST

    def is_demo(self) -> bool:
        """DEMOモードか判定"""
        return self.mode == TradeMode.DEMO

    def is_live(self) -> bool:
        """本番モードか判定"""
        return self.mode == TradeMode.LIVE

    def get_table_names(self) -> Dict[str, str]:
        """
        モードに応じたテーブル名を取得

        Returns:
            Dict[str, str]: テーブル名のマッピング
                {
                    'ai_judgments': テーブル名,
                    'positions': テーブル名,
                    'reviews': テーブル名,
                    'strategies': テーブル名,
                    'periodic_updates': テーブル名,
                    'layer3a_monitoring': テーブル名,
                    'layer3b_emergency': テーブル名
                }
        """
        table_mapping = {
            TradeMode.BACKTEST: {
                'ai_judgments': 'backtest_ai_judgments',
                'positions': 'backtest_positions',
                'reviews': 'backtest_daily_reviews',
                'strategies': 'backtest_daily_strategies',
                'periodic_updates': 'backtest_periodic_updates',
                'layer3a_monitoring': 'backtest_layer3a_monitoring',
                'layer3b_emergency': 'backtest_layer3b_emergency'
            },
            TradeMode.DEMO: {
                'ai_judgments': 'demo_ai_judgments',
                'positions': 'demo_positions',
                'reviews': 'demo_daily_reviews',
                'strategies': 'demo_daily_strategies',
                'periodic_updates': 'demo_periodic_updates',
                'layer3a_monitoring': 'demo_layer3a_monitoring',
                'layer3b_emergency': 'demo_layer3b_emergency'
            },
            TradeMode.LIVE: {
                'ai_judgments': 'ai_judgments',
                'positions': 'positions',
                'reviews': 'daily_reviews',
                'strategies': 'daily_strategies',
                'periodic_updates': 'periodic_updates',
                'layer3a_monitoring': 'layer3a_monitoring',
                'layer3b_emergency': 'layer3b_emergency'
            }
        }

        return table_mapping[self.mode]

    def get_backtest_period(self) -> Tuple[datetime, datetime]:
        """
        バックテスト期間を取得

        Returns:
            Tuple[datetime, datetime]: (開始日, 終了日)

        Raises:
            ValueError: バックテストモード以外で呼ばれた場合
            ValueError: 環境変数が設定されていない場合
        """
        if not self.is_backtest():
            raise ValueError("get_backtest_period() can only be called in BACKTEST mode")

        start_date_str = os.getenv('BACKTEST_START_DATE')
        end_date_str = os.getenv('BACKTEST_END_DATE')

        if not start_date_str or not end_date_str:
            raise ValueError(
                "BACKTEST_START_DATE and BACKTEST_END_DATE must be set in .env "
                "for backtest mode"
            )

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError as e:
            raise ValueError(
                f"Invalid date format. Use YYYY-MM-DD format. Error: {e}"
            )

        if start_date >= end_date:
            raise ValueError("BACKTEST_START_DATE must be before BACKTEST_END_DATE")

        return start_date, end_date

    def get_backtest_symbol(self) -> str:
        """
        バックテスト対象シンボルを取得

        Returns:
            str: シンボル名（例: USDJPY）
        """
        if not self.is_backtest():
            raise ValueError("get_backtest_symbol() can only be called in BACKTEST mode")

        symbol = os.getenv('BACKTEST_SYMBOL', 'USDJPY')
        return symbol

    def get_mt5_credentials(self) -> Dict[str, str]:
        """
        MT5接続情報を取得

        Returns:
            Dict[str, str]: MT5接続情報
                {
                    'login': ログイン番号,
                    'password': パスワード,
                    'server': サーバー名
                }

        Raises:
            ValueError: バックテストモードで呼ばれた場合
            ValueError: 必要な環境変数が設定されていない場合
        """
        if self.is_backtest():
            raise ValueError(
                "get_mt5_credentials() cannot be called in BACKTEST mode. "
                "Backtest does not use MT5 connection."
            )

        # 本番モードの場合は専用の環境変数を使用
        if self.is_live():
            login = os.getenv('MT5_LIVE_LOGIN')
            password = os.getenv('MT5_LIVE_PASSWORD')
            server = os.getenv('MT5_LIVE_SERVER')

            if not all([login, password, server]):
                raise ValueError(
                    "MT5_LIVE_LOGIN, MT5_LIVE_PASSWORD, MT5_LIVE_SERVER "
                    "must be set in .env for live mode"
                )
        else:
            # DEMOモードの場合は通常の環境変数を使用
            login = os.getenv('MT5_LOGIN')
            password = os.getenv('MT5_PASSWORD')
            server = os.getenv('MT5_SERVER')

            if not all([login, password, server]):
                raise ValueError(
                    "MT5_LOGIN, MT5_PASSWORD, MT5_SERVER "
                    "must be set in .env for demo mode"
                )

        return {
            'login': login,
            'password': password,
            'server': server
        }

    def should_use_mt5(self) -> bool:
        """
        MT5を使用すべきか判定

        Returns:
            bool: True=MT5使用、False=使用しない
        """
        # バックテストモードではMT5を使用しない
        return not self.is_backtest()

    def get_data_source_description(self) -> str:
        """
        データソースの説明を取得（ログ用）

        Returns:
            str: データソースの説明
        """
        if self.is_backtest():
            try:
                start_date, end_date = self.get_backtest_period()
                symbol = self.get_backtest_symbol()
                return (
                    f"Backtest mode: {symbol} "
                    f"from {start_date.date()} to {end_date.date()} "
                    f"(Historical data from data/tick_data)"
                )
            except ValueError:
                return "Backtest mode: Configuration error"
        elif self.is_demo():
            return "Demo mode: Real-time data from MT5 (DEMO account)"
        else:
            return "Live mode: Real-time data from MT5 (LIVE account)"

    def __str__(self) -> str:
        """文字列表現"""
        return f"TradeModeConfig(mode={self.mode.value})"

    def __repr__(self) -> str:
        """詳細な文字列表現"""
        return self.__str__()


# グローバルインスタンス（シングルトンとして使用）
_config_instance: Optional[TradeModeConfig] = None


def get_trade_mode_config() -> TradeModeConfig:
    """
    トレードモード設定のグローバルインスタンスを取得

    Returns:
        TradeModeConfig: 設定インスタンス
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = TradeModeConfig()

    return _config_instance


# モジュールのエクスポート
__all__ = [
    'TradeMode',
    'TradeModeConfig',
    'get_trade_mode_config'
]
