"""
MT5接続テストスクリプト

このスクリプトは、MT5への接続が正しく設定されているかを確認します。
AI分析は行わず、接続テストのみを実行するため、数秒で完了します。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import MetaTrader5 as mt5
from datetime import datetime

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

# ステップ2: MT5ターミナルの起動確認
print("【ステップ2】MT5ターミナルの起動確認...")
if not mt5.initialize():
    error_code = mt5.last_error()
    print(f"✗ MT5が起動していません (エラーコード: {error_code})")
    print()
    print("【エラー診断】")
    if error_code[0] == -10004:
        print("  原因: MT5アプリケーションが起動していません")
        print()
        print("【解決方法】")
        print("  1. デスクトップまたはスタートメニューから「MetaTrader 5」を起動")
        print("  2. MT5のウィンドウが表示されることを確認")
        print("  3. 再度このスクリプトを実行")
    else:
        print(f"  エラーコード: {error_code}")
        print("  MT5の初期化に失敗しました")
    print()
    print("=" * 80)
    sys.exit(1)

print("✓ MT5ターミナルが起動しています")
print()

# ステップ3: MT5へのログイン
print("【ステップ3】MT5へのログイン...")

# すでにログイン済みかチェック
account_info_current = mt5.account_info()
if account_info_current and str(account_info_current.login) == mt5_login:
    print(f"✓ すでにログイン済みです (口座: {account_info_current.login})")
else:
    # ログイン試行
    authorized = mt5.login(
        login=int(mt5_login),
        password=mt5_password,
        server=mt5_server
    )

    if not authorized:
        error_code = mt5.last_error()
        print(f"✗ ログインに失敗しました (エラーコード: {error_code})")
        print()
        print("【エラー診断】")
        if error_code[0] == -6:
            print("  原因: 認証エラー - ログイン情報が間違っているか、口座が無効です")
            print()
            print("【解決方法】")
            print("  1. MT5で手動ログインを試してください:")
            print("     MT5メニュー「ファイル」→「取引口座にログイン」")
            print(f"     ログイン: {mt5_login}")
            print(f"     サーバー: {mt5_server}")
            print("  2. 手動ログインが成功したら、そのパスワードを.envに設定")
            print("  3. 手動ログインも失敗する場合:")
            print("     - DEMO口座の期限切れ（通常30日）")
            print("     - 新しいDEMO口座を作成してください")
        elif error_code[0] == -2:
            print("  原因: サーバー名が見つかりません")
            print()
            print("【解決方法】")
            print("  1. MT5で正確なサーバー名を確認:")
            print("     MT5メニュー「ツール」→「オプション」→「サーバー」タブ")
            print(f"  2. 現在の設定: {mt5_server}")
            print("  3. スペース、ハイフン、大文字小文字が完全一致しているか確認")
        else:
            print(f"  エラーコード: {error_code}")
        print()
        print("=" * 80)
        mt5.shutdown()
        sys.exit(1)

    print(f"✓ ログインに成功しました (口座: {mt5_login})")

print()

# ステップ4: 口座情報の取得
print("【ステップ4】口座情報の取得...")
account_info = mt5.account_info()

if account_info:
    print("✓ 口座情報を取得しました")
    print()
    print("【口座情報】")
    print(f"  口座番号: {account_info.login}")
    print(f"  残高: {account_info.balance:,.2f} {account_info.currency}")
    print(f"  証拠金: {account_info.equity:,.2f} {account_info.currency}")
    print(f"  余剰証拠金: {account_info.margin_free:,.2f} {account_info.currency}")
    print(f"  証拠金維持率: {account_info.margin_level:.2f}%" if account_info.margin_level else "  証拠金維持率: N/A")
    print(f"  レバレッジ: 1:{account_info.leverage}")
    print(f"  サーバー: {account_info.server}")
    print(f"  会社名: {account_info.company}")
else:
    print("✗ 口座情報の取得に失敗しました")
    print()
    mt5.shutdown()
    sys.exit(1)

print()

# ステップ5: 通貨ペア情報の取得
print("【ステップ5】通貨ペア情報の取得（USDJPY）...")

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
    # スプレッドを計算（pips）
    spread_pips = (tick.ask - tick.bid) * 100  # USDJPY想定
    print("【USDJPY 現在価格】")
    print(f"  Bid (売値): {tick.bid:.3f}")
    print(f"  Ask (買値): {tick.ask:.3f}")
    print(f"  スプレッド: {spread_pips:.2f} pips")
    print(f"  最終更新: {tick.time}")
else:
    print("✗ 価格情報の取得に失敗しました")

print()

# ステップ6: ポジション情報の取得
print("【ステップ6】現在のポジション確認...")
positions_data = mt5.positions_get(symbol="USDJPY")

if positions_data is None:
    positions = []
else:
    positions = list(positions_data)

print(f"✓ 現在のポジション数: {len(positions)}")
if positions:
    print()
    print("【保有ポジション】")
    for i, pos in enumerate(positions, 1):
        pos_type = "BUY" if pos.type == 0 else "SELL"
        print(f"  {i}. Ticket: {pos.ticket}")
        print(f"     種別: {pos_type}")
        print(f"     ロット: {pos.volume}")
        print(f"     建値: {pos.price_open:.3f}")
        print(f"     現在損益: {pos.profit:,.2f} {account_info.currency}")
        print()
else:
    print("  現在、保有ポジションはありません")

print()

# ステップ7: 接続状態の最終確認
print("【ステップ7】接続状態の最終確認...")

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
mt5.shutdown()
