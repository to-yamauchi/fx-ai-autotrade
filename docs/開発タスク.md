# FX自動トレードシステム - 開発タスク詳細

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **種別**: 実装計画書
- **対象読者**: 開発者

---

## 目次
1. [開発フェーズ概要](#1-開発フェーズ概要)
2. [Phase 1: 基礎実装](#2-phase-1-基礎実装)
3. [Phase 2: AI統合](#3-phase-2-ai統合)
4. [Phase 3: トレード実行](#4-phase-3-トレード実行)
5. [Phase 4: バックテスト](#5-phase-4-バックテスト)
6. [Phase 5: デモ運用](#6-phase-5-デモ運用)
7. [Phase 6: 本番運用](#7-phase-6-本番運用)

---

## 1. 開発フェーズ概要

### 1.1 全体スケジュール

| Phase | 期間 | 主要成果物 | 検証方法 |
|-------|------|----------|---------|
| **Phase 1** | Week 1-2 | 共通ライブラリ、データ処理、DB | ユニットテスト |
| **Phase 2** | Week 3 | AI分析、ルール生成 | ルールJSON検証 |
| **Phase 3** | Week 3-4 | ルールエンジン、トレード実行 | デモ口座テスト |
| **Phase 4** | Week 4 | バックテスト | 過去データ検証 |
| **Phase 5** | Week 5-8 | デモ運用、調整 | 4週間実績 |
| **Phase 6** | Week 9- | 本番運用 | リアルトレード |

### 1.2 優先順位の原則

1. **安全装置優先**: Layer 1緊急停止を最優先で実装
2. **データ基盤**: 共通ライブラリとデータベースを先に構築
3. **段階的統合**: 各モジュールを独立してテスト後に統合
4. **継続的検証**: 各フェーズ終了時に必ず検証

---

## 2. Phase 1: 基礎実装（Week 1-2）

### 2.1 目標

**データ処理と安全装置の構築**

- MT5からの安定したデータ取得
- 基本的な安全装置（Layer 1）の実装
- データベース設計と実装
- 共通ライブラリの整備

### 2.2 タスク一覧

#### 2.2.1 環境セットアップ (Priority: 最高)

**タスク**: プロジェクト環境の構築

**成果物**:
- [ ] Pythonプロジェクト構造作成
- [ ] 仮想環境セットアップ
- [ ] 依存パッケージリスト作成 (requirements.txt)
- [ ] Git初期化と.gitignore設定
- [ ] 基本的なディレクトリ構造作成

**実装手順**:
```bash
# 1. ディレクトリ作成
mkdir -p src/{lib,modules,orchestrator}
mkdir -p src/lib/{database,mt5,config,utils,exceptions}
mkdir -p data/{market,rules,backtest,logs,reports}
mkdir -p config scripts/{setup,batch,utils} tests

# 2. requirements.txt作成
cat > requirements.txt << EOF
MetaTrader5>=5.0.45
pandas>=2.0.0
numpy>=1.24.0
TA-Lib>=0.4.26
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pyyaml>=6.0
python-dotenv>=1.0.0
APScheduler>=3.10.0
google-generativeai>=0.3.0
EOF

# 3. 開発用依存パッケージ
cat > requirements-dev.txt << EOF
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
black>=23.7.0
flake8>=6.1.0
mypy>=1.5.0
EOF
```

**検証**:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -c "import MetaTrader5; import pandas; import sqlalchemy; print('OK')"
```

**所要時間**: 2時間

---

#### 2.2.2 共通ライブラリ: 設定管理 (Priority: 最高)

**タスク**: 設定ファイルの読み込みと管理

**ファイル**: `src/lib/config/settings.py`

**機能**:
- YAML設定ファイルの読み込み
- 環境変数の読み込み
- 設定の検証

**実装**:
```python
# src/lib/config/settings.py
import yaml
import os
from pathlib import Path
from typing import Dict, Any

class Settings:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """設定ファイルを読み込み"""
        config_dir = Path(__file__).parent.parent.parent.parent / "config"

        # 基本設定
        with open(config_dir / "settings.yaml", "r") as f:
            self._config.update(yaml.safe_load(f))

        # DB設定
        with open(config_dir / "database.yaml", "r") as f:
            self._config["database"] = yaml.safe_load(f)

        # MT5設定
        with open(config_dir / "mt5.yaml", "r") as f:
            self._config["mt5"] = yaml.safe_load(f)

        # シークレット（環境変数優先）
        if os.path.exists(config_dir / "secrets.yaml"):
            with open(config_dir / "secrets.yaml", "r") as f:
                secrets = yaml.safe_load(f)
                self._config["secrets"] = secrets

    def get(self, key: str, default=None):
        """設定値取得"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            value = value.get(k)
            if value is None:
                return default
        return value

# グローバルインスタンス
settings = Settings()
```

**設定ファイル例**:
```yaml
# config/settings.yaml
app:
  name: "FX Auto Trade System"
  version: "1.0.0"
  environment: "development"  # development / staging / production

trading:
  symbol: "USDJPY"
  base_lot: 0.1
  max_positions: 1

timeframes:
  daily: 30
  h4: 50
  h1: 100
  m15: 100
```

**テスト**:
```python
# src/lib/config/tests/test_settings.py
def test_settings_singleton():
    s1 = Settings()
    s2 = Settings()
    assert s1 is s2

def test_get_config():
    s = Settings()
    assert s.get("app.name") == "FX Auto Trade System"
    assert s.get("trading.symbol") == "USDJPY"
```

**所要時間**: 3時間

---

#### 2.2.3 共通ライブラリ: ロガー (Priority: 最高)

**タスク**: 統一されたロギング機能

**ファイル**: `src/lib/utils/logger.py`

**機能**:
- モジュール別ログファイル
- ログレベル管理
- ログローテーション

**実装**:
```python
# src/lib/utils/logger.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    ロガーを取得

    Args:
        name: ロガー名（通常は __name__）
        log_file: ログファイル名（Noneの場合は標準出力のみ）
        level: ログレベル
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)

    # フォーマット
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラ（オプション）
    if log_file:
        log_dir = Path(__file__).parent.parent.parent.parent / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_dir / log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
```

**使用例**:
```python
from src.lib.utils.logger import get_logger

logger = get_logger(__name__, "data_processing.log")
logger.info("Processing started")
logger.error("Error occurred", exc_info=True)
```

**所要時間**: 2時間

---

#### 2.2.4 データベース設計 (Priority: 最高)

**タスク**: データベーススキーマ設計と実装

**ファイル**: `src/lib/database/models.py`

**テーブル設計**:

**1. market_data**: 市場データスナップショット
```sql
CREATE TABLE market_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,  -- D1, H4, H1, M15
    data JSONB NOT NULL,  -- 標準化データJSON全体
    data_hash VARCHAR(64) NOT NULL,  -- SHA-256ハッシュ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp, symbol, timeframe)
);
CREATE INDEX idx_market_data_timestamp ON market_data(timestamp);
CREATE INDEX idx_market_data_symbol ON market_data(symbol);
```

**2. ai_decisions**: AI判断履歴
```sql
CREATE TABLE ai_decisions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    decision_type VARCHAR(20) NOT NULL,  -- morning, update, review, position_eval
    model VARCHAR(50) NOT NULL,  -- gemini-2.5-pro, gemini-2.5-flash 等
    prompt_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    rules_json JSONB,  -- 生成されたルールJSON
    confidence FLOAT,
    cost FLOAT,  -- API利用コスト
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_decisions_timestamp ON ai_decisions(timestamp);
CREATE INDEX idx_ai_decisions_type ON ai_decisions(decision_type);
```

**3. trades**: トレード記録
```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    ticket BIGINT UNIQUE NOT NULL,  -- MT5のチケット番号
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL,  -- BUY / SELL
    lot_size FLOAT NOT NULL,
    entry_price FLOAT NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_price FLOAT,
    exit_time TIMESTAMP,
    profit FLOAT,
    stop_loss FLOAT,
    take_profit FLOAT,
    exit_reason VARCHAR(50),  -- 決済理由
    ai_decision_id INTEGER REFERENCES ai_decisions(id),
    rules_json JSONB,  -- エントリー時のルール
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_trades_entry_time ON trades(entry_time);
CREATE INDEX idx_trades_symbol ON trades(symbol);
```

**4. positions**: 現在のポジション
```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    ticket BIGINT UNIQUE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL,
    lot_size FLOAT NOT NULL,
    entry_price FLOAT NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    current_price FLOAT,
    unrealized_pnl FLOAT,
    stop_loss FLOAT,
    take_profit FLOAT,
    rules_json JSONB,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**5. risk_alerts**: リスクアラート
```sql
CREATE TABLE risk_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,  -- drawdown_5, drawdown_7, emergency_stop 等
    severity VARCHAR(10) NOT NULL,  -- INFO, WARNING, DANGER
    message TEXT NOT NULL,
    data JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_risk_alerts_created_at ON risk_alerts(created_at);
```

**SQLAlchemy モデル実装**:
```python
# src/lib/database/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, BIGINT
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class MarketData(Base):
    __tablename__ = 'market_data'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    symbol = Column(String(10), nullable=False)
    timeframe = Column(String(5), nullable=False)
    data = Column(JSONB, nullable=False)
    data_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class AIDecision(Base):
    __tablename__ = 'ai_decisions'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    decision_type = Column(String(20), nullable=False)
    model = Column(String(50), nullable=False)
    prompt_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    rules_json = Column(JSONB)
    confidence = Column(Float)
    cost = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

class Trade(Base):
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    ticket = Column(BIGINT, unique=True, nullable=False)
    symbol = Column(String(10), nullable=False)
    direction = Column(String(4), nullable=False)
    lot_size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime, nullable=False)
    exit_price = Column(Float)
    exit_time = Column(DateTime)
    profit = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    exit_reason = Column(String(50))
    ai_decision_id = Column(Integer)
    rules_json = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Position(Base):
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    ticket = Column(BIGINT, unique=True, nullable=False)
    symbol = Column(String(10), nullable=False)
    direction = Column(String(4), nullable=False)
    lot_size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime, nullable=False)
    current_price = Column(Float)
    unrealized_pnl = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    rules_json = Column(JSONB)
    last_updated = Column(DateTime, server_default=func.now())

class RiskAlert(Base):
    __tablename__ = 'risk_alerts'

    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
```

**DB初期化スクリプト**:
```python
# scripts/setup/init_database.py
from sqlalchemy import create_engine
from src.lib.database.models import Base
from src.lib.config.settings import settings

def init_database():
    db_config = settings.get("database")

    # 接続文字列構築
    db_url = f"postgresql://{db_config['user']}:{db_config['password']}@" \
             f"{db_config['host']}:{db_config['port']}/{db_config['database']}"

    engine = create_engine(db_url)

    # テーブル作成
    Base.metadata.create_all(engine)

    print("Database initialized successfully")

if __name__ == "__main__":
    init_database()
```

**所要時間**: 6時間

---

#### 2.2.5 共通ライブラリ: DB接続管理 (Priority: 最高)

**タスク**: データベース接続の管理

**ファイル**: `src/lib/database/connection.py`

**実装**:
```python
# src/lib/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from src.lib.config.settings import settings

class DatabaseConnection:
    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """DB接続初期化"""
        db_config = settings.get("database")

        db_url = f"postgresql://{db_config['user']}:{db_config['password']}@" \
                 f"{db_config['host']}:{db_config['port']}/{db_config['database']}"

        self._engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True  # 接続確認
        )

        self._session_factory = sessionmaker(bind=self._engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """セッションコンテキストマネージャ"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# グローバルインスタンス
db = DatabaseConnection()

# 使用例
def get_db_session():
    return db.get_session()
```

**使用例**:
```python
from src.lib.database.connection import get_db_session
from src.lib.database.models import Trade

with get_db_session() as session:
    trades = session.query(Trade).filter(Trade.symbol == "USDJPY").all()
```

**所要時間**: 3時間

---

#### 2.2.6 モジュール: データ処理エンジン - MT5接続 (Priority: 最高)

**タスク**: MT5との接続管理

**ファイル**: `src/lib/mt5/connector.py`

**機能**:
- MT5への接続
- 再接続処理
- 接続状態監視

**実装**:
```python
# src/lib/mt5/connector.py
import MetaTrader5 as mt5
from typing import Optional
import time
from src.lib.utils.logger import get_logger
from src.lib.config.settings import settings

logger = get_logger(__name__, "mt5_connector.log")

class MT5Connector:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self) -> bool:
        """MT5初期化"""
        if self._initialized:
            return True

        mt5_config = settings.get("mt5")

        if not mt5.initialize():
            logger.error(f"MT5 initialize failed: {mt5.last_error()}")
            return False

        # ログイン
        if mt5_config.get("account"):
            authorized = mt5.login(
                login=mt5_config["account"],
                password=mt5_config["password"],
                server=mt5_config["server"]
            )

            if not authorized:
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False

        self._initialized = True
        logger.info("MT5 initialized successfully")
        return True

    def shutdown(self):
        """MT5シャットダウン"""
        if self._initialized:
            mt5.shutdown()
            self._initialized = False
            logger.info("MT5 shutdown")

    def reconnect(self, max_retries: int = 3) -> bool:
        """再接続"""
        for attempt in range(max_retries):
            logger.info(f"Reconnecting to MT5 (attempt {attempt + 1}/{max_retries})")
            self.shutdown()
            time.sleep(1)
            if self.initialize():
                return True

        logger.error("MT5 reconnection failed")
        return False

    def is_connected(self) -> bool:
        """接続状態確認"""
        if not self._initialized:
            return False

        # ターミナル情報取得で接続確認
        terminal_info = mt5.terminal_info()
        return terminal_info is not None

# グローバルインスタンス
mt5_connector = MT5Connector()
```

**所要時間**: 4時間

---

#### 2.2.7 モジュール: データ処理エンジン - データ取得 (Priority: 高)

**タスク**: MT5からの市場データ取得

**ファイル**: `src/lib/mt5/data_fetcher.py`

**機能**:
- ティックデータ取得
- OHLC時間足データ取得
- エラーハンドリング

**実装**:
```python
# src/lib/mt5/data_fetcher.py
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from typing import Optional
from src.lib.mt5.connector import mt5_connector
from src.lib.utils.logger import get_logger

logger = get_logger(__name__, "data_fetcher.log")

class DataFetcher:

    def __init__(self):
        self.connector = mt5_connector

    def get_rates(
        self,
        symbol: str,
        timeframe: int,
        count: int,
        start_pos: int = 0
    ) -> Optional[pd.DataFrame]:
        """
        OHLC時間足データ取得

        Args:
            symbol: 通貨ペア
            timeframe: 時間足 (mt5.TIMEFRAME_*)
            count: 取得本数
            start_pos: 開始位置（0が最新）

        Returns:
            DataFrame or None
        """
        if not self.connector.is_connected():
            logger.warning("MT5 not connected, trying to reconnect")
            if not self.connector.reconnect():
                return None

        rates = mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)

        if rates is None or len(rates) == 0:
            logger.error(f"Failed to get rates: {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        logger.debug(f"Fetched {len(df)} bars for {symbol} {timeframe}")
        return df

    def get_tick(self, symbol: str) -> Optional[dict]:
        """
        最新ティック取得

        Returns:
            dict: {'bid': float, 'ask': float, 'time': datetime}
        """
        if not self.connector.is_connected():
            if not self.connector.reconnect():
                return None

        tick = mt5.symbol_info_tick(symbol)

        if tick is None:
            logger.error(f"Failed to get tick: {mt5.last_error()}")
            return None

        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'time': datetime.fromtimestamp(tick.time),
            'spread': (tick.ask - tick.bid) * 100000  # pips (5桁)
        }
```

**所要時間**: 4時間

---

#### 2.2.8 モジュール: データ処理エンジン - テクニカル指標計算 (Priority: 高)

**タスク**: テクニカル指標の計算

**ファイル**: `src/modules/data_processing/indicator_calculator.py`

**機能**:
- EMA, RSI, MACD, ATR, ボリンジャーバンド計算
- サポート・レジスタンスレベル算出

**実装概要**:
```python
# src/modules/data_processing/indicator_calculator.py
import pandas as pd
import talib

class IndicatorCalculator:

    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
        """EMA計算"""
        return talib.EMA(df['close'], timeperiod=period)

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """RSI計算"""
        return talib.RSI(df['close'], timeperiod=period)

    @staticmethod
    def calculate_macd(df: pd.DataFrame):
        """MACD計算"""
        macd, signal, hist = talib.MACD(
            df['close'],
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        return {'macd': macd, 'signal': signal, 'histogram': hist}

    # ... 他の指標も同様に実装
```

**所要時間**: 6時間

---

### 2.3 Phase 1 完了基準

- [ ] 全ユニットテストが通過
- [ ] MT5からデータ取得可能
- [ ] データベースへの保存・読み込み可能
- [ ] テクニカル指標が正しく計算できる
- [ ] ログが正常に出力される

---

## 3. Phase 2: AI統合（Week 3）

### 3.1 目標

**AI分析機能の実装**

- Gemini APIの統合
- 朝の分析機能
- 定期更新機能
- ルールJSON生成

### 3.2 タスク一覧

#### 3.2.1 Gemini APIクライアント (Priority: 最高)

**ファイル**: `src/modules/ai_analysis/gemini_client.py`

**機能**:
- Gemini APIへのリクエスト
- モデル選択（Pro, Flash, Flash-Lite）
- コスト計算
- リトライ処理

**実装概要**:
```python
# src/modules/ai_analysis/gemini_client.py
import google.generativeai as genai
from typing import Dict, Any

class GeminiClient:

    def __init__(self):
        genai.configure(api_key=settings.get("secrets.gemini_api_key"))

    def generate(
        self,
        prompt: str,
        model: str = "gemini-2.5-pro",
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        AI生成

        Args:
            prompt: プロンプト
            model: モデル名
            temperature: 温度パラメータ

        Returns:
            {'text': str, 'token_count': dict, 'cost': float}
        """
        model_obj = genai.GenerativeModel(model)
        response = model_obj.generate_content(
            prompt,
            generation_config={'temperature': temperature}
        )

        # コスト計算
        cost = self._calculate_cost(
            model,
            response.usage_metadata.prompt_token_count,
            response.usage_metadata.candidates_token_count
        )

        return {
            'text': response.text,
            'token_count': {
                'input': response.usage_metadata.prompt_token_count,
                'output': response.usage_metadata.candidates_token_count
            },
            'cost': cost
        }
```

**所要時間**: 5時間

---

#### 3.2.2 プロンプトビルダー (Priority: 高)

**ファイル**: `src/modules/ai_analysis/prompt_builder.py`

**機能**:
- 標準化データからプロンプト生成
- 分析タイプ別のプロンプトテンプレート

**所要時間**: 6時間

---

#### 3.2.3 ルール生成器 (Priority: 高)

**ファイル**: `src/modules/ai_analysis/rule_generator.py`

**機能**:
- AI応答からルールJSON生成
- バリデーション

**所要時間**: 5時間

---

### 3.3 Phase 2 完了基準

- [ ] Gemini APIからの応答取得成功
- [ ] ルールJSONが正しく生成される
- [ ] データベースにAI判断が記録される
- [ ] コスト計算が正確

---

## 4. Phase 3: トレード実行（Week 3-4）

### 4.1 目標

**完全な自動トレードシステムの実装**

- ルールエンジンの実装
- Layer 1/2/3監視
- エントリー・決済システム

### 4.2 タスク一覧

#### 4.2.1 Layer 1: 緊急停止 (Priority: 最高)

**ファイル**: `src/modules/rule_engine/layer1_emergency.py`

**機能**:
- 100msごとの監視
- 口座2%損失検知
- ハードストップ50pips
- 即座の決済実行

**所要時間**: 8時間

---

#### 4.2.2 エントリー監視 (Priority: 高)

**ファイル**: `src/modules/rule_engine/entry_monitor.py`

**機能**:
- ルールJSONの条件チェック
- エントリー条件判定

**所要時間**: 6時間

---

### 4.3 Phase 3 完了基準

- [ ] デモ口座でエントリー成功
- [ ] Layer 1緊急停止が動作
- [ ] トレード記録がDBに保存

---

## 5. Phase 4: バックテスト（Week 4）

### 5.1 タスク一覧

#### 5.1.1 バックテストエンジン

**ファイル**: `src/modules/backtest/backtester.py`

**所要時間**: 10時間

---

## 6. Phase 5: デモ運用（Week 5-8）

### 6.1 目標

4週間のデモ口座実運用で調整

---

## 7. Phase 6: 本番運用（Week 9-）

### 7.1 目標

実資金での運用開始

---

## 8. まとめ

各フェーズの開発タスクを段階的に実装し、継続的にテストを実施します。
