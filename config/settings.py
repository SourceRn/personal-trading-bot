import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    # --- CONFIGURACIÓN PRINCIPAL ---
    SYMBOL = "SOL/USDT".replace("/", "")
    
    # Mantenemos 1h: Es el equilibrio perfecto entre ruido y tendencia para Day Trading
    TIMEFRAME = "1h" 
    
    # APALANCAMIENTO CONSERVADOR
    # Con un Stop Loss del 1.8%, usar 5x es el límite máximo seguro (1.8% * 5 = 9% riesgo)
    # Recomendación: Empieza con 3x o 4x.
    LEVERAGE = 4 
    
    # GESTIÓN DE RIESGO
    RISK_PER_TRADE = 0.02   # 2% de tu cuenta por operación
    MAX_DAILY_LOSS = 0.06   # Si pierdes 6% en un día, se apaga (protección más estricta)

    # --- TRAILING STOP (DINÁMICA INTELIGENTE) ---
    # ACTIVACIÓN TEMPRANA:
    # No esperamos al 2%. Si ya ganamos un 1.5%, activamos el seguro.
    TRAILING_TRIGGER = 0.015  # 1.5%
    
    # ESPACIO AJUSTADO:
    # Si el precio retrocede 0.5%, cerramos. Aseguramos la ganancia rápido.
    TRAILING_STEP = 0.005     # 0.5%

    # --- ALERTAS ---
    ALERT_PROXIMITY_PCT = 0.003 

    # --- ESTRATEGIA DE SALIDA (Realista) ---
    # STOP LOSS TÉCNICO:
    # En 1h, un 1.8% suele quedar por debajo del mínimo de la vela anterior.
    # Es suficiente para respirar, pero corta las pérdidas rápido si falla.
    STOP_LOSS_PCT = 0.018    # 1.8% 
    
    # TAKE PROFIT ALCANZABLE:
    # Un movimiento del 3% en SOL es muy común en un día volátil.
    # Es mucho más fácil tocar el 3% que el 6%.
    TAKE_PROFIT_PCT = 0.03   # 3.0% (Ratio 1:1.6 aprox)

    # --- CONFIGURACIÓN ESTRATEGIAS ---
    ADX_PERIOD = 14
    ADX_THRESHOLD = 25 

    EMA_FAST = 9
    EMA_SLOW = 21

    RSI_LENGTH = 14
    RSI_EMA_FILTER = 50 
    
    # Filtros RSI
    # Mantenemos la exigencia alta para no operar en ruido.
    RSI_LONG_THRESHOLD = 30  
    RSI_SHORT_THRESHOLD = 70 

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