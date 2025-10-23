"""
========================================
システム起動チェックモジュール
========================================

ファイル名: startup_checker.py
パス: src/utils/startup_checker.py

【概要】
システム起動前に必要な環境・設定・接続をチェックします。
モード（backtest/demo/live）ごとに必要な項目をチェックし、
問題があれば詳細なエラーメッセージを出力します。

【チェック項目】
全モード共通:
- 環境変数の設定確認
- データベース接続確認
- Gemini APIキー確認

バックテストモード:
- バックテスト期間設定確認
- データファイル存在確認

DEMO/本番モード:
- MT5接続情報確認
- MT5起動確認
- MT5ログイン確認

【使用例】
```python
from src.utils.startup_checker import StartupChecker

checker = StartupChecker()
is_ok, errors = checker.check_all()
if not is_ok:
    for error in errors:
        print(error)
    sys.exit(1)
```

【作成日】2025-10-23
"""

import os
import psycopg2
from typing import Tuple, List
import MetaTrader5 as mt5
from datetime import datetime

from src.utils.trade_mode import get_trade_mode_config, TradeMode


class StartupChecker:
    """
    システム起動チェッククラス

    モード別に必要な項目をチェックし、問題があれば詳細なエラーを返します。
    """

    def __init__(self):
        """初期化"""
        self.mode_config = get_trade_mode_config()
        self.errors = []
        self.warnings = []

    def check_all(self) -> Tuple[bool, List[str]]:
        """
        すべての起動チェックを実行

        Returns:
            Tuple[bool, List[str]]: (チェック成功, エラーメッセージリスト)
        """
        print("=" * 80)
        print("  システム起動チェック")
        print("=" * 80)
        print()
        print(f"モード: {self.mode_config.get_mode().value.upper()}")
        print(f"説明: {self.mode_config.get_data_source_description()}")
        print()

        # 共通チェック
        self._check_environment_variables()
        self._check_database_connection()
        self._check_gemini_api_key()

        # モード別チェック
        if self.mode_config.is_backtest():
            self._check_backtest_requirements()
        elif self.mode_config.is_demo() or self.mode_config.is_live():
            self._check_mt5_requirements()

        # 結果表示
        print("-" * 80)
        if self.warnings:
            print("⚠ 警告:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()

        if self.errors:
            print("✗ エラー:")
            for error in self.errors:
                print(f"  - {error}")
            print()
            print("=" * 80)
            return False, self.errors
        else:
            print("✓ すべてのチェックが成功しました")
            print("=" * 80)
            print()
            return True, []

    def _check_environment_variables(self):
        """環境変数の基本チェック"""
        print("[1/6] 環境変数チェック...")

        # TRADE_MODE
        trade_mode = os.getenv('TRADE_MODE')
        if not trade_mode:
            self.errors.append("TRADE_MODE が設定されていません")
        else:
            # 値をクリーンアップ（コメント除去、空白除去）
            if '#' in trade_mode:
                trade_mode = trade_mode.split('#')[0]
            trade_mode = trade_mode.strip()

            # 検証
            if trade_mode not in ['backtest', 'demo', 'live']:
                self.errors.append(
                    f"TRADE_MODE が不正です: {trade_mode} "
                    f"(有効な値: backtest, demo, live)"
                )
            else:
                print(f"  ✓ TRADE_MODE: {trade_mode}")

        # データベース設定
        db_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER']
        for var in db_vars:
            if not os.getenv(var):
                self.errors.append(f"{var} が設定されていません")

        if all(os.getenv(var) for var in db_vars):
            print(f"  ✓ データベース設定: OK")

    def _check_database_connection(self):
        """データベース接続チェック"""
        print("[2/6] データベース接続チェック...")

        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5432)),
                database=os.getenv('DB_NAME', 'fx_autotrade'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', ''),
                connect_timeout=5
            )

            # テーブル存在確認
            cursor = conn.cursor()
            table_names = self.mode_config.get_table_names()

            for table_type, table_name in table_names.items():
                cursor.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = %s)",
                    (table_name,)
                )
                exists = cursor.fetchone()[0]

                if not exists:
                    self.errors.append(
                        f"テーブル '{table_name}' が存在しません。"
                        f"database_schema_extended.sql を実行してください。"
                    )
                else:
                    print(f"  ✓ テーブル '{table_name}': 存在")

            cursor.close()
            conn.close()

            if not any(f"テーブル" in e for e in self.errors):
                print(f"  ✓ データベース接続: 成功")

        except psycopg2.OperationalError as e:
            self.errors.append(f"データベース接続エラー: {e}")
        except Exception as e:
            self.errors.append(f"データベースチェックエラー: {e}")

    def _check_gemini_api_key(self):
        """Gemini APIキーチェック"""
        print("[3/6] Gemini APIキーチェック...")

        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            self.errors.append("GEMINI_API_KEY が設定されていません")
        elif api_key == 'your_gemini_api_key_here':
            self.errors.append("GEMINI_API_KEY が初期値のままです")
        else:
            # APIキーの形式チェック（長さのみ）
            if len(api_key) < 20:
                self.warnings.append("GEMINI_API_KEY が短すぎる可能性があります")
            else:
                print(f"  ✓ GEMINI_API_KEY: 設定済み")

    def _check_backtest_requirements(self):
        """バックテストモード固有のチェック"""
        print("[4/6] バックテスト設定チェック...")

        # 期間設定チェック
        try:
            start_date, end_date = self.mode_config.get_backtest_period()
            symbol = self.mode_config.get_backtest_symbol()

            print(f"  ✓ バックテスト期間: {start_date.date()} ～ {end_date.date()}")
            print(f"  ✓ 対象シンボル: {symbol}")

        except ValueError as e:
            self.errors.append(f"バックテスト設定エラー: {e}")
            return

        # データファイル存在チェック
        print("[5/6] データファイルチェック...")

        data_dir = f"data/tick_data/{symbol}"
        if not os.path.exists(data_dir):
            self.errors.append(
                f"データディレクトリが存在しません: {data_dir}"
            )
            return

        # 必要な月のリストを生成
        months_needed = []
        current = start_date.replace(day=1)
        while current <= end_date:
            months_needed.append((current.year, current.month))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        # 各月のファイル存在確認
        missing_files = []
        for year, month in months_needed:
            filename = f"ticks_{symbol}-oj5k_{year:04d}-{month:02d}.zip"
            filepath = os.path.join(data_dir, filename)

            if not os.path.exists(filepath):
                missing_files.append(f"{year}-{month:02d}")

        if missing_files:
            self.errors.append(
                f"以下の期間のデータファイルが見つかりません: "
                f"{', '.join(missing_files)}"
            )
        else:
            print(f"  ✓ データファイル: {len(months_needed)}ヶ月分すべて存在")

        print("[6/6] MT5接続チェック...")
        print(f"  - バックテストモードはMT5不要: スキップ")

    def _check_mt5_requirements(self):
        """DEMO/本番モード固有のチェック"""
        print("[4/6] データファイルチェック...")
        print(f"  - {self.mode_config.get_mode().value.upper()}モードはデータファイル不要: スキップ")

        print("[5/6] MT5設定チェック...")

        # MT5接続情報チェック
        try:
            credentials = self.mode_config.get_mt5_credentials()

            # 初期値チェック
            if credentials['login'] == 'your_mt5_login_number':
                self.errors.append("MT5_LOGIN が初期値のままです")
                return

            if credentials['password'] == 'your_mt5_password':
                self.errors.append("MT5_PASSWORD が初期値のままです")
                return

            if credentials['server'] == 'your_mt5_server_name':
                self.errors.append("MT5_SERVER が初期値のままです")
                return

            print(f"  ✓ MT5ログイン: {credentials['login']}")
            print(f"  ✓ MT5サーバー: {credentials['server']}")

        except ValueError as e:
            self.errors.append(f"MT5設定エラー: {e}")
            return

        # MT5接続テスト
        print("[6/6] MT5接続テスト...")

        # MT5初期化チェック
        if not mt5.initialize():
            error_code = mt5.last_error()
            self.errors.append(
                f"MT5が起動していません (エラーコード: {error_code}). "
                f"MetaTrader5を起動してください。"
            )
            return

        print(f"  ✓ MT5起動: 確認")

        # MT5ログインチェック
        try:
            authorized = mt5.login(
                login=int(credentials['login']),
                password=credentials['password'],
                server=credentials['server']
            )

            if not authorized:
                error_code = mt5.last_error()
                self.errors.append(
                    f"MT5ログインに失敗しました (エラーコード: {error_code}). "
                    f"ログイン情報を確認してください。"
                )
                mt5.shutdown()
                return

            # 口座情報取得
            account_info = mt5.account_info()
            if account_info:
                print(f"  ✓ MT5ログイン: 成功")
                print(f"    口座番号: {account_info.login}")
                print(f"    残高: {account_info.balance:,.0f} {account_info.currency}")
                print(f"    サーバー: {account_info.server}")

            mt5.shutdown()

        except Exception as e:
            self.errors.append(f"MT5接続テストエラー: {e}")
            mt5.shutdown()


# モジュールのエクスポート
__all__ = ['StartupChecker']
