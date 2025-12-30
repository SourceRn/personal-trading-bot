import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    SYMBOL = "SOL/USDT".replace("/", "")
    TIMEFRAME = "5m"
    LEVERAGE = 5
    
    # GESTIÓN DE RIESGO
    RISK_PER_TRADE = 0.02   
    MAX_DAILY_LOSS = 0.10   

    # --- ESTRATEGIA DE SALIDA ---
    STOP_LOSS_PCT = 0.01     
    TAKE_PROFIT_PCT = 0.02   

    # --- CONFIGURACIÓN ESTRATEGIAS ---
    # 1. El Juez (Selector)
    ADX_PERIOD = 14
    ADX_THRESHOLD = 25  # >25 = Tendencia, <25 = Rango

    # 2. Estrategia Tendencia (EMA Cross)
    EMA_FAST = 9
    EMA_SLOW = 21

    # 3. Estrategia Rango (Tu actual RSI + EMA)
    RSI_LENGTH = 14
    RSI_EMA_FILTER = 50 # EMA para filtrar dirección en estrategia RSI
    RSI_LONG_THRESHOLD = 45
    RSI_SHORT_THRESHOLD = 55

    # ... (Resto de tus credenciales Telegram/API sin cambios) ...
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TRADING_MODE = os.getenv("TRADING_MODE", "dry_run").upper()

    @property
    def IS_LIVE(self):
        return self.TRADING_MODE == "LIVE"

    @property
    def API_KEY(self):
        return os.getenv("BINANCE_API_KEY")

    @property
    def SECRET_KEY(self):
        return os.getenv("BINANCE_SECRET_KEY")

settings = Settings()