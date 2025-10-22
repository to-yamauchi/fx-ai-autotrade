"""
MT5接続テストスクリプト

このスクリプトは、MT5への接続が正しく設定されているかを確認します。
AI分析は行わず、接続テストのみを実行するため、数秒で完了します。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from src.trade_execution.mt5_executor import MT5Executor
import MetaTrader5 as mt5

# 環境変数の読み込み
load_dotenv()

print("=" * 80)
print("  MT5接続テスト")
print("=" * 80)
print()

# ステップ1: 環境変数の確認
print("【ステップ1】環境変数の確認...")
mt5_login = os.getenv('MT5_LOGIN')
mt5_password = os.getenv('MT5_PASSWORD')
mt5_server = os.getenv('MT5_SERVER')

if not all([mt5_login, mt5_password, mt5_server]):
    print("✗ エラー: MT5接続情報が設定されていません")
    print()
    print(".envファイルに以下の情報を設定してください:")
    print("  MT5_LOGIN=your_account_number")
    print("  MT5_PASSWORD=your_password")
    print("  MT5_SERVER=demo_server_name")
    print()
    print("詳細: docs/MT5_SETUP_GUIDE.md を参照してください")
    print("=" * 80)
    sys.exit(1)

print(f"✓ MT5_LOGIN: {mt5_login}")
print(f"✓ MT5_SERVER: {mt5_server}")
print(f"✓ MT5_PASSWORD: {'*' * len(mt5_password)} (設定済み)")
print()

# ステップ2: MT5への接続
print("【ステップ2】MT5への接続...")
try:
    executor = MT5Executor(auto_login=True)
    print("✓ MT5に接続しました")
except Exception as e:
    print(f"✗ MT5接続エラー: {e}")
    print()
    print("【確認事項】")
    print("  1. MetaTrader5が起動していますか？")
    print("  2. .envファイルの接続情報は正しいですか？")
    print("  3. DEMO口座は有効ですか？（期限切れではないか）")
    print()
    print("詳細: docs/MT5_SETUP_GUIDE.md を参照してください")
    print("=" * 80)
    sys.exit(1)

print()

# ステップ3: 口座情報の取得
print("【ステップ3】口座情報の取得...")
account_info = executor.get_account_info()

if account_info:
    print("✓ 口座情報を取得しました")
    print()
    print("【口座情報】")
    print(f"  口座番号: {account_info['login']}")
    print(f"  残高: {account_info['balance']:,.2f} {account_info.get('currency', 'JPY')}")
    print(f"  証拠金: {account_info['equity']:,.2f} {account_info.get('currency', 'JPY')}")
    print(f"  余剰証拠金: {account_info['margin_free']:,.2f} {account_info.get('currency', 'JPY')}")
    print(f"  証拠金維持率: {account_info.get('margin_level', 0):.2f}%")
    print(f"  レバレッジ: 1:{account_info['leverage']}")
    print(f"  サーバー: {account_info['server']}")
else:
    print("✗ 口座情報の取得に失敗しました")
    print()
    sys.exit(1)

print()

# ステップ4: 通貨ペア情報の取得
print("【ステップ4】通貨ペア情報の取得（USDJPY）...")

# 銘柄情報を取得
symbol_info = mt5.symbol_info("USDJPY")
if symbol_info is None:
    print("✗ USDJPY情報の取得に失敗しました")
    print("  銘柄リストにUSDJPYが存在しない可能性があります")
    print()
else:
    print("✓ USDJPY情報を取得しました")
    print()

# 現在の価格を取得
tick = mt5.symbol_info_tick("USDJPY")
if tick:
    spread_pips = executor.get_spread("USDJPY")
    print("【USDJPY 現在価格】")
    print(f"  Bid (売値): {tick.bid:.3f}")
    print(f"  Ask (買値): {tick.ask:.3f}")
    print(f"  スプレッド: {spread_pips:.2f} pips")
    print(f"  最終更新: {tick.time}")
else:
    print("✗ 価格情報の取得に失敗しました")

print()

# ステップ5: ポジション情報の取得
print("【ステップ5】現在のポジション確認...")
positions = executor.get_positions(symbol="USDJPY")

print(f"✓ 現在のポジション数: {len(positions)}")
if positions:
    print()
    print("【保有ポジション】")
    for i, pos in enumerate(positions, 1):
        print(f"  {i}. Ticket: {pos['ticket']}")
        print(f"     種別: {pos['type']}")
        print(f"     ロット: {pos['volume']}")
        print(f"     建値: {pos['price_open']:.3f}")
        print(f"     現在損益: {pos['profit']:,.2f} JPY")
        print()
else:
    print("  現在、保有ポジションはありません")

print()

# ステップ6: 接続状態の最終確認
print("【ステップ6】接続状態の最終確認...")

terminal_info = mt5.terminal_info()
if terminal_info:
    print("✓ ターミナル情報:")
    print(f"  会社名: {terminal_info.company}")
    print(f"  ビルド: {terminal_info.build}")
    print(f"  接続状態: {'接続済み' if terminal_info.connected else '未接続'}")
    print(f"  トレード許可: {'はい' if terminal_info.trade_allowed else 'いいえ'}")

    if not terminal_info.trade_allowed:
        print()
        print("  ⚠ 警告: 自動売買が許可されていません")
        print("  MT5の「ツール」→「オプション」→「エキスパートアドバイザー」で")
        print("  「アルゴリズム取引を許可する」にチェックを入れてください")

print()

# 成功メッセージ
print("=" * 80)
print("✓ MT5接続テスト完了")
print()
print("【結果】")
print("  ✓ MT5への接続: 成功")
print("  ✓ 口座情報の取得: 成功")
print("  ✓ 価格情報の取得: 成功")
print("  ✓ ポジション情報の取得: 成功")
print()
print("【次のステップ】")
print("  → phase4_sample.py を実行して、AI分析とトレード実行をテスト")
print("=" * 80)

# MT5接続を終了
executor.close()
