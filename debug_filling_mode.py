"""
Filling Mode デバッグスクリプト

OANDAのUSDJPYがサポートしているfilling modeを確認します。
"""
import MetaTrader5 as mt5
from dotenv import load_dotenv
import os

load_dotenv()

print("=" * 80)
print("  Filling Mode デバッグ")
print("=" * 80)
print()

# MT5初期化
if not mt5.initialize():
    print("✗ MT5の初期化に失敗しました")
    print(f"  エラー: {mt5.last_error()}")
    exit(1)

# ログイン
mt5_login = os.getenv('MT5_LOGIN')
mt5_password = os.getenv('MT5_PASSWORD')
mt5_server = os.getenv('MT5_SERVER')

authorized = mt5.login(
    login=int(mt5_login),
    password=mt5_password,
    server=mt5_server
)

if not authorized:
    print("✗ ログインに失敗しました")
    print(f"  エラー: {mt5.last_error()}")
    mt5.shutdown()
    exit(1)

print(f"✓ ログイン成功: {mt5_login}")
print()

# USDJPYのシンボル情報を取得
symbol = "USDJPY"
symbol_info = mt5.symbol_info(symbol)

if symbol_info is None:
    print(f"✗ {symbol}の情報取得に失敗しました")
    mt5.shutdown()
    exit(1)

print(f"【{symbol} シンボル情報】")
print(f"  名前: {symbol_info.name}")
print(f"  説明: {symbol_info.description}")
print()

# Filling Mode情報
filling_mode = symbol_info.filling_mode
print("【Filling Mode サポート状況】")
print(f"  filling_mode値: {filling_mode} (binary: {bin(filling_mode)})")
print()

# 各モードのサポート状況を確認
print("  各モードの確認:")
print(f"    ORDER_FILLING_FOK (2)    : {'✓ サポート' if filling_mode & 2 else '✗ 非サポート'}")
print(f"    ORDER_FILLING_IOC (1)    : {'✓ サポート' if filling_mode & 1 else '✗ 非サポート'}")
print(f"    ORDER_FILLING_RETURN (4) : {'✓ サポート' if filling_mode & 4 else '✗ 非サポート'}")
print()

# 推奨モードを表示
if filling_mode & 4:
    recommended = "ORDER_FILLING_RETURN (4)"
    recommended_value = mt5.ORDER_FILLING_RETURN
elif filling_mode & 2:
    recommended = "ORDER_FILLING_FOK (2)"
    recommended_value = mt5.ORDER_FILLING_FOK
elif filling_mode & 1:
    recommended = "ORDER_FILLING_IOC (1)"
    recommended_value = mt5.ORDER_FILLING_IOC
else:
    recommended = "不明"
    recommended_value = None

print(f"【推奨Filling Mode】")
print(f"  {recommended}")
if recommended_value:
    print(f"  値: {recommended_value}")
print()

# その他の重要な情報
print("【トレード制限情報】")
print(f"  最小ロット: {symbol_info.volume_min}")
print(f"  最大ロット: {symbol_info.volume_max}")
print(f"  ロットステップ: {symbol_info.volume_step}")
print(f"  ストップレベル: {symbol_info.trade_stops_level} points")
print(f"  Point値: {symbol_info.point}")
print()

# 現在価格
tick = mt5.symbol_info_tick(symbol)
if tick:
    print("【現在価格】")
    print(f"  Bid: {tick.bid:.3f}")
    print(f"  Ask: {tick.ask:.3f}")
    print()

# MT5のバージョン情報
terminal_info = mt5.terminal_info()
if terminal_info:
    print("【MT5ターミナル情報】")
    print(f"  会社: {terminal_info.company}")
    print(f"  ビルド: {terminal_info.build}")
    print(f"  トレード許可: {terminal_info.trade_allowed}")
    print()

print("=" * 80)
print("デバッグ完了")
print("=" * 80)

mt5.shutdown()
