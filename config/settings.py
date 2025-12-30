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

    # --- NUEVO: TRAILING STOP ---
    TRAILING_TRIGGER = 0.01  
    TRAILING_STEP = 0.005    

    # --- NUEVO: ALERTAS ---
    # Avisar si el precio está a un 0.2% de distancia del TP o SL
    ALERT_PROXIMITY_PCT = 0.002 

    # --- ESTRATEGIA DE SALIDA ---
    STOP_LOSS_PCT = 0.01     
    TAKE_PROFIT_PCT = 0.02   

    # --- CONFIGURACIÓN ESTRATEGIAS ---
    ADX_PERIOD = 14
    ADX_THRESHOLD = 25  

    EMA_FAST = 9
    EMA_SLOW = 21

    RSI_LENGTH = 14
    RSI_EMA_FILTER = 50 
    RSI_LONG_THRESHOLD = 40
    RSI_SHORT_THRESHOLD = 65

    # ... Credenciales ...
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