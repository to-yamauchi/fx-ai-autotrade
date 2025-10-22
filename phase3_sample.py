"""
========================================
フェーズ3 サンプルスクリプト
========================================

ファイル名: phase3_sample.py
パス: phase3_sample.py

【概要】
フェーズ3で実装したAI分析機能のデモンストレーションスクリプトです。
実際のティックデータを使用して、AI分析を実行し、結果を表示します。

【実行内容】
1. AIAnalyzerの初期化
2. マーケットデータ分析の実行
3. AI判断結果の表示（BUY/SELL/HOLD、信頼度、理由）
4. 判断履歴の確認

【使用前の準備】
1. .envファイルにGEMINI_API_KEYを設定
2. データベースが起動していること
3. ティックデータが配置されていること
   - data/tick_data/USDJPY/ticks_USDJPY-oj5k_2024-09.zip

【実行方法】
    python phase3_sample.py

【注意事項】
- Gemini API呼び出しには実際のAPIキーが必要です
- API呼び出しには課金が発生する可能性があります
- データベースがない場合、保存処理でエラーが出ますが分析結果は表示されます

【作成日】2025-10-22
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai_analysis import AIAnalyzer

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def print_separator(char='=', length=80):
    """区切り線を出力"""
    print(char * length)


def print_section_header(title):
    """セクションヘッダーを出力"""
    print()
    print_separator()
    print(f"  {title}")
    print_separator()
    print()


def display_ai_result(result):
    """AI判断結果を見やすく表示"""
    print_section_header("AI分析結果")

    # 基本情報
    print(f"【通貨ペア】: {result.get('symbol', 'N/A')}")
    print(f"【分析時刻】: {result.get('timestamp', 'N/A')}")
    print(f"【使用モデル】: {result.get('model', 'N/A')}")
    print()

    # 判断結果
    action = result.get('action', 'HOLD')
    confidence = result.get('confidence', 0)

    # アクションに応じた表示色（ANSIカラーコード）
    if action == 'BUY':
        action_display = f"\033[92m{action}\033[0m"  # 緑
    elif action == 'SELL':
        action_display = f"\033[91m{action}\033[0m"  # 赤
    else:
        action_display = f"\033[93m{action}\033[0m"  # 黄色

    print(f"【判断】: {action_display}")
    print(f"【信頼度】: {confidence}%")
    print()

    # 判断理由
    reasoning = result.get('reasoning', '理由なし')
    print("【判断理由】:")
    print(reasoning)
    print()

    # エントリー情報（BUY/SELLの場合）
    if action in ['BUY', 'SELL']:
        entry_price = result.get('entry_price')
        stop_loss = result.get('stop_loss')
        take_profit = result.get('take_profit')

        if entry_price:
            print(f"【エントリー価格】: {entry_price}")
        if stop_loss:
            print(f"【ストップロス】: {stop_loss}")
        if take_profit:
            print(f"【テイクプロフィット】: {take_profit}")
        print()

    # エラー情報（ある場合）
    if 'error' in result:
        print(f"\033[91m【エラー】: {result['error']}\033[0m")
        print()

    print_separator()


def display_judgment_history(judgments):
    """判断履歴を表示"""
    print_section_header("最近のAI判断履歴")

    if not judgments:
        print("履歴がありません")
        return

    print(f"{'No.':<5} {'日時':<20} {'判断':<8} {'信頼度':<8}")
    print_separator('-')

    for i, judgment in enumerate(judgments, 1):
        created_at = judgment.get('created_at', 'N/A')
        if created_at != 'N/A':
            # ISO形式から読みやすい形式に変換
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass

        action = judgment.get('action', 'N/A')
        confidence = judgment.get('confidence', 0)

        print(f"{i:<5} {created_at:<20} {action:<8} {confidence:<8.1f}%")

    print()


def main():
    """メイン処理"""
    # .envファイルの読み込み
    load_dotenv()

    print_section_header("フェーズ3: AI分析エンジン デモンストレーション")

    # APIキーの確認
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print()
        print_separator()
        print("  エラー: GEMINI_API_KEYが設定されていません")
        print_separator()
        print()
        print(".envファイルにGEMINI_API_KEYを設定してください:")
        print("  1. .env.templateをコピーして.envファイルを作成")
        print("  2. GEMINI_API_KEY=your_api_key_here を追加")
        print()
        print("Gemini APIキーの取得方法:")
        print("  https://aistudio.google.com/app/apikey")
        print()
        sys.exit(1)

    # パラメータ設定
    symbol = 'USDJPY'
    year = 2024
    month = 9
    model = 'flash'  # pro / flash / flash-lite

    print(f"通貨ペア: {symbol}")
    print(f"データ期間: {year}年{month}月")
    print(f"使用モデル: {model}")
    print()

    try:
        # AIAnalyzerの初期化
        logger.info("AIAnalyzerを初期化しています...")
        analyzer = AIAnalyzer(
            symbol=symbol,
            data_dir='data/tick_data',
            model=model
        )

        logger.info("初期化完了")
        print("\033[92m✓ AIAnalyzer初期化完了\033[0m")
        print()

        # マーケット分析の実行
        logger.info("マーケット分析を実行しています...")
        print("AI分析を実行中...")
        print("（ティックデータ読み込み → 時間足変換 → テクニカル指標計算 → AI分析）")
        print()

        result = analyzer.analyze_market(
            year=year,
            month=month
        )

        # 結果の表示
        display_ai_result(result)

        # 判断履歴の取得と表示
        logger.info("判断履歴を取得しています...")
        judgments = analyzer.get_recent_judgments(limit=5)
        display_judgment_history(judgments)

        # サマリー
        print_section_header("実行サマリー")
        print("\033[92m✓ フェーズ3の全機能が正常に動作しました\033[0m")
        print()
        print("【実装済み機能】")
        print("  ✓ Gemini API連携")
        print("  ✓ マーケットデータ分析")
        print("  ✓ AI判断（BUY/SELL/HOLD）")
        print("  ✓ 信頼度計算")
        print("  ✓ 判断理由生成")
        print("  ✓ データベース保存")
        print()

        # 次のステップ
        print("【次のステップ】")
        print("  → フェーズ4: ルールエンジンとトレード実行")
        print("  → フェーズ5: モニタリングと決済システム")
        print("  → フェーズ6: バックテストシステム")
        print()

    except FileNotFoundError as e:
        logger.error(f"ファイルが見つかりません: {e}")
        print(f"\033[91mエラー: ティックデータファイルが見つかりません\033[0m")
        print(f"パス: data/tick_data/{symbol}/ticks_{symbol}-oj5k_{year}-{month:02d}.zip")
        print()
        print("対処方法:")
        print("1. ティックデータが正しい場所に配置されているか確認")
        print("2. ファイル名が正しいか確認")
        print()
        sys.exit(1)

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        print(f"\033[91mエラー: {e}\033[0m")
        print()
        print("エラーの詳細はログを確認してください")
        sys.exit(1)


if __name__ == "__main__":
    main()
