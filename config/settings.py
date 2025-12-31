import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    # --- CONFIGURACIÓN PRINCIPAL ---
    SYMBOL = "SOL/USDT".replace("/", "")
    
    # TIMEFRAME 1H: El rey del Day Trading (menos ruido, señales claras)
    TIMEFRAME = "1h" 
    
    # APALANCAMIENTO
    # 4x es el punto dulce para SL de ~2%. Riesgo controlado.
    LEVERAGE = 4 
    
    # GESTIÓN DE RIESGO CAPITAL
    RISK_PER_TRADE = 0.05   # 2% de tu cuenta por operación
    MAX_DAILY_LOSS = 0.1   # Circuit Breaker al 6% de pérdida diaria

    # --- GESTIÓN DINÁMICA DE ESTRATEGIAS (SOLUCIÓN "SÁBANA CORTA") ---
    
    # MODO RANGO (RSI): "Golpea y corre"
    # Buscamos entrar en reversiones y salir rápido.
    RANGE_TP = 0.025  # 2.5% Ganancia
    RANGE_SL = 0.015  # 1.5% Pérdida

    # MODO TENDENCIA (EMA): "Surfea la ola"
    # Damos espacio para que el precio corra.
    TREND_TP = 0.05   # 5.0% Ganancia
    TREND_SL = 0.025  # 2.5% Pérdida (Más amplio para aguantar volatilidad)

    # VALORES POR DEFECTO (Respaldo)
    STOP_LOSS_PCT = 0.018
    TAKE_PROFIT_PCT = 0.03

    # --- TRAILING STOP ---
    # Activamos el seguro cuando ganamos 1.5%
    TRAILING_TRIGGER = 0.015 
    # Dejamos 0.5% de espacio
    TRAILING_STEP = 0.005     

    # --- ALERTAS ---
    ALERT_PROXIMITY_PCT = 0.003 

    # --- CONFIGURACIÓN TÉCNICA ESTRATEGIAS ---
    # 1. El Juez (ADX)
    ADX_PERIOD = 14
    # Subimos a 30 para que el Rango tenga prioridad y no se corte antes de tiempo
    ADX_THRESHOLD = 30 

    # 2. Tendencia (EMA)
    EMA_FAST = 9
    EMA_SLOW = 21

    # 3. Rango (RSI)
    RSI_LENGTH = 14
    RSI_EMA_FILTER = 50 
    
    # Umbrales optimizados para 1H (Entrada temprana)
    RSI_LONG_THRESHOLD = 35  
    RSI_SHORT_THRESHOLD = 65 

    # --- CREDENCIALES ---
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TRADING_MODE = os.getenv("TRADING_MODE", "LIVE").upper()

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