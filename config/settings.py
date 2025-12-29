import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    SYMBOL = "SOL/USDT".replace("/", "")
    TIMEFRAME = "5m"
    LEVERAGE = 5
    
    # GESTIÓN DE RIESGO
    RISK_PER_TRADE = 0.02   # SUGERENCIA: Sube a 2% ($0.40) para que el bot tenga holgura.
                            # Con 1% ($0.20) es seguro, pero con 2% ($0.40) cubres mejor las comisiones.
    
    MAX_DAILY_LOSS = 0.10   # 10% ($2.00). Si pierdes $2 en un día, para.
                            # Con una cuenta tan chica, un stop loss diario de 2% ($0.40) es muy estricto (una sola mala operación te detiene).

    # --- ESTRATEGIA DE SALIDA ---
    # Cambia estos valores para ajustar la estrategia globalmente
    STOP_LOSS_PCT = 0.01     # 1%
    TAKE_PROFIT_PCT = 0.02   # 2%

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