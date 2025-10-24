"""
========================================
設定管理モジュール
========================================

ファイル名: config.py
パス: src/utils/config.py

【概要】
環境変数から設定を読み込み、システム全体で使用する設定を一元管理します。
.envファイルの値を型安全に取得し、デフォルト値を提供します。

【使用例】
```python
from src.utils.config import get_config

config = get_config()
print(config.gemini_model_pro)  # 'gemini-2.5-flash'
print(config.position_size_default)  # 0.1
print(config.rsi_period)  # 14
```

【作成日】2025-10-23
"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# 環境変数を読み込み（.envファイルの値を強制的に優先）
load_dotenv(override=True)


@dataclass
class Config:
    """
    システム設定を保持するデータクラス

    全ての設定値は環境変数から読み込まれ、適切な型に変換されます。
    環境変数が設定されていない場合は、デフォルト値を使用します。
    """

    # ========================================
    # トレードモード
    # ========================================
    trade_mode: str

    # ========================================
    # バックテスト設定
    # ========================================
    backtest_start_date: str
    backtest_end_date: str
    backtest_symbol: str
    backtest_initial_balance: float
    backtest_csv_path: Optional[str]

    # ========================================
    # LLM API Keys（マルチプロバイダー対応）
    # ========================================
    gemini_api_key: str
    openai_api_key: str
    anthropic_api_key: str

    # ========================================
    # LLM Model Settings（Phase別）
    # ========================================
    # 各Phaseで異なるプロバイダーのモデルを使用可能
    # プロバイダーはモデル名から自動判定（gemini-*/gpt-*/claude-*）
    model_daily_analysis: str             # Phase 1, 2用
    model_periodic_update: str            # Phase 3用
    model_position_monitor: str           # Phase 4用
    model_emergency_evaluation: str       # Phase 5用

    # 後方互換性のため保持（非推奨）
    gemini_model_daily_analysis: Optional[str]
    gemini_model_periodic_update: Optional[str]
    gemini_model_position_monitor: Optional[str]

    # AI分析パラメータ（プロバイダー共通）
    ai_temperature_daily_analysis: float
    ai_temperature_periodic_update: float
    ai_temperature_position_monitor: float
    ai_temperature_emergency_evaluation: float
    ai_max_tokens_daily_analysis: Optional[int]  # None=LLMデフォルト使用
    ai_max_tokens_periodic_update: Optional[int]
    ai_max_tokens_position_monitor: Optional[int]
    ai_max_tokens_emergency_evaluation: Optional[int]

    # ========================================
    # リスク管理
    # ========================================
    position_size_default: float
    max_positions: int
    risk_per_trade: float
    default_stop_loss_pips: float
    default_take_profit_pips: float

    # ========================================
    # テクニカル指標
    # ========================================
    ema_short_period: int
    ema_long_period: int
    rsi_period: int
    rsi_overbought: int
    rsi_oversold: int
    macd_fast: int
    macd_slow: int
    macd_signal: int
    atr_period: int
    bollinger_period: int
    bollinger_std_dev: float
    support_resistance_window: int

    # ========================================
    # Layer 3監視
    # ========================================
    layer3a_monitor_interval: int
    anomaly_price_change_threshold: float
    anomaly_spread_multiplier: float
    anomaly_volatility_multiplier: float
    anomaly_drawdown_threshold: float

    # ========================================
    # データベース
    # ========================================
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # ========================================
    # ロギング
    # ========================================
    log_level: str
    log_file: str
    debug_mode: bool


def _get_env_str(key: str, default: str) -> str:
    """環境変数を文字列として取得"""
    value = os.getenv(key, default)
    if value is None:
        return default
    # コメントを除去
    if '#' in value:
        value = value.split('#')[0]
    return value.strip()


def _get_env_int(key: str, default: int) -> int:
    """環境変数を整数として取得"""
    value_str = _get_env_str(key, str(default))
    try:
        return int(value_str)
    except ValueError:
        return default


def _get_env_float(key: str, default: float) -> float:
    """環境変数を浮動小数点数として取得"""
    value_str = _get_env_str(key, str(default))
    try:
        return float(value_str)
    except ValueError:
        return default


def _get_env_bool(key: str, default: bool) -> bool:
    """環境変数を真偽値として取得"""
    value_str = _get_env_str(key, str(default)).lower()
    return value_str in ('true', '1', 'yes', 'on')


def _get_env_optional_int(key: str) -> Optional[int]:
    """環境変数をOptional[int]として取得（未設定の場合はNone）"""
    value_str = os.getenv(key)
    if value_str is None or value_str.strip() == '':
        return None
    # コメントを除去
    if '#' in value_str:
        value_str = value_str.split('#')[0]
    value_str = value_str.strip()
    if value_str == '':
        return None
    try:
        return int(value_str)
    except ValueError:
        return None


def _get_env_optional_str(key: str) -> Optional[str]:
    """環境変数をOptional[str]として取得（未設定の場合はNone）"""
    value_str = os.getenv(key)
    if value_str is None or value_str.strip() == '':
        return None
    # コメントを除去
    if '#' in value_str:
        value_str = value_str.split('#')[0]
    value_str = value_str.strip()
    if value_str == '':
        return None
    return value_str


def load_config() -> Config:
    """
    環境変数から設定を読み込む

    Returns:
        Config: 設定オブジェクト
    """
    return Config(
        # トレードモード
        trade_mode=_get_env_str('TRADE_MODE', 'demo'),

        # バックテスト設定
        backtest_start_date=_get_env_str('BACKTEST_START_DATE', '2024-09-01'),
        backtest_end_date=_get_env_str('BACKTEST_END_DATE', '2024-09-30'),
        backtest_symbol=_get_env_str('BACKTEST_SYMBOL', 'USDJPY'),
        backtest_initial_balance=_get_env_float('BACKTEST_INITIAL_BALANCE', 1000000.0),
        backtest_csv_path=_get_env_str('BACKTEST_CSV_PATH', '') or None,

        # LLM API Keys
        gemini_api_key=_get_env_str('GEMINI_API_KEY', ''),
        openai_api_key=_get_env_str('OPENAI_API_KEY', ''),
        anthropic_api_key=_get_env_str('ANTHROPIC_API_KEY', ''),

        # LLM Models（新環境変数、後方互換性あり）
        # 注: .envファイルで必ず設定してください。デフォルト値は提供しません。
        model_daily_analysis=_get_env_str('MODEL_DAILY_ANALYSIS', '') or _get_env_str('GEMINI_MODEL_DAILY_ANALYSIS', ''),
        model_periodic_update=_get_env_str('MODEL_PERIODIC_UPDATE', '') or _get_env_str('GEMINI_MODEL_PERIODIC_UPDATE', ''),
        model_position_monitor=_get_env_str('MODEL_POSITION_MONITOR', '') or _get_env_str('GEMINI_MODEL_POSITION_MONITOR', ''),
        model_emergency_evaluation=_get_env_str('MODEL_EMERGENCY_EVALUATION', ''),

        # 後方互換性のため保持（非推奨）
        gemini_model_daily_analysis=_get_env_optional_str('GEMINI_MODEL_DAILY_ANALYSIS'),
        gemini_model_periodic_update=_get_env_optional_str('GEMINI_MODEL_PERIODIC_UPDATE'),
        gemini_model_position_monitor=_get_env_optional_str('GEMINI_MODEL_POSITION_MONITOR'),

        # AI分析パラメータ
        ai_temperature_daily_analysis=_get_env_float('AI_TEMPERATURE_DAILY_ANALYSIS', 0.3),
        ai_temperature_periodic_update=_get_env_float('AI_TEMPERATURE_PERIODIC_UPDATE', 0.3),
        ai_temperature_position_monitor=_get_env_float('AI_TEMPERATURE_POSITION_MONITOR', 0.2),
        ai_temperature_emergency_evaluation=_get_env_float('AI_TEMPERATURE_EMERGENCY_EVALUATION', 0.3),
        ai_max_tokens_daily_analysis=_get_env_optional_int('AI_MAX_TOKENS_DAILY_ANALYSIS'),
        ai_max_tokens_periodic_update=_get_env_optional_int('AI_MAX_TOKENS_PERIODIC_UPDATE'),
        ai_max_tokens_position_monitor=_get_env_optional_int('AI_MAX_TOKENS_POSITION_MONITOR'),
        ai_max_tokens_emergency_evaluation=_get_env_optional_int('AI_MAX_TOKENS_EMERGENCY_EVALUATION'),

        # リスク管理
        position_size_default=_get_env_float('POSITION_SIZE_DEFAULT', 0.1),
        max_positions=_get_env_int('MAX_POSITIONS', 3),
        risk_per_trade=_get_env_float('RISK_PER_TRADE', 2.0),
        default_stop_loss_pips=_get_env_float('DEFAULT_STOP_LOSS_PIPS', 50.0),
        default_take_profit_pips=_get_env_float('DEFAULT_TAKE_PROFIT_PIPS', 100.0),

        # テクニカル指標
        ema_short_period=_get_env_int('EMA_SHORT_PERIOD', 20),
        ema_long_period=_get_env_int('EMA_LONG_PERIOD', 50),
        rsi_period=_get_env_int('RSI_PERIOD', 14),
        rsi_overbought=_get_env_int('RSI_OVERBOUGHT', 70),
        rsi_oversold=_get_env_int('RSI_OVERSOLD', 30),
        macd_fast=_get_env_int('MACD_FAST', 12),
        macd_slow=_get_env_int('MACD_SLOW', 26),
        macd_signal=_get_env_int('MACD_SIGNAL', 9),
        atr_period=_get_env_int('ATR_PERIOD', 14),
        bollinger_period=_get_env_int('BOLLINGER_PERIOD', 20),
        bollinger_std_dev=_get_env_float('BOLLINGER_STD_DEV', 2.0),
        support_resistance_window=_get_env_int('SUPPORT_RESISTANCE_WINDOW', 20),

        # Layer 3監視
        layer3a_monitor_interval=_get_env_int('LAYER3A_MONITOR_INTERVAL', 15),
        anomaly_price_change_threshold=_get_env_float('ANOMALY_PRICE_CHANGE_THRESHOLD', 0.5),
        anomaly_spread_multiplier=_get_env_float('ANOMALY_SPREAD_MULTIPLIER', 3.0),
        anomaly_volatility_multiplier=_get_env_float('ANOMALY_VOLATILITY_MULTIPLIER', 2.0),
        anomaly_drawdown_threshold=_get_env_float('ANOMALY_DRAWDOWN_THRESHOLD', 3.0),

        # データベース
        db_host=_get_env_str('DB_HOST', 'localhost'),
        db_port=_get_env_int('DB_PORT', 5432),
        db_name=_get_env_str('DB_NAME', 'fx_autotrade'),
        db_user=_get_env_str('DB_USER', 'postgres'),
        db_password=_get_env_str('DB_PASSWORD', ''),

        # ロギング
        log_level=_get_env_str('LOG_LEVEL', 'INFO'),
        log_file=_get_env_str('LOG_FILE', 'logs/fx_autotrade.log'),
        debug_mode=_get_env_bool('DEBUG_MODE', False),
    )


# グローバルインスタンス（シングルトン）
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    設定のグローバルインスタンスを取得

    初回呼び出し時に環境変数から設定を読み込み、以降は同じインスタンスを返します。

    Returns:
        Config: 設定オブジェクト
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = load_config()

    return _config_instance


def reload_config() -> Config:
    """
    設定を再読み込み

    環境変数が変更された場合に、設定を再読み込みします。

    Returns:
        Config: 新しい設定オブジェクト
    """
    global _config_instance

    load_dotenv(override=True)  # 環境変数を再読み込み
    _config_instance = load_config()

    return _config_instance


# モジュールのエクスポート
__all__ = ['Config', 'get_config', 'reload_config']
