from dataclasses import dataclass
from datetime import datetime

@dataclass
class BotState:
    # Información General
    symbol: str = "SOL/USDT"
    mode: str = "INIT"
    uptime: datetime = datetime.now()
    
    # Datos de Mercado en tiempo real
    last_price: float = 0.0
    strategy_name: str = "ESPERANDO DATOS..."
    
    # Indicadores (Para el comando /analizar)
    rsi: float = 0.0
    adx: float = 0.0
    
    # Estado de la Cuenta
    daily_pnl: float = 0.0
    balance_total: float = 0.0
    
    # Posición Actual
    in_position: bool = False
    pos_type: str = "NONE" # LONG o SHORT
    entry_price: float = 0.0
    current_pnl_pct: float = 0.0
    
    # Control
    running: bool = True  # Para apagar el bot remotamente

# Instancia global que compartiremos
bot_state = BotState()