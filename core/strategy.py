import pandas as pd
import pandas_ta as ta
from config.settings import settings
from core.shared_state import bot_state

class Strategy:
    def __init__(self):
        # Inicializamos en RANGE por seguridad
        # (Se sobrescribirá inmediatamente si usas FORCE_TREND)
        self.current_mode = "RANGE"

    def analyze(self, df):
        """
        Analiza el mercado y decide qué estrategia usar basado en STRATEGY_MODE y ADX.
        Retorna: (Señal, Nombre_Estrategia)
        """
        # --- 1. CALCULO DE INDICADORES ---
        # ADX
        adx_period = getattr(settings, 'ADX_PERIOD', 14)
        adx_df = df.ta.adx(length=adx_period)
        
        # Validación de datos
        if adx_df is None or adx_df.empty: return None, "WAITING_DATA"
        
        # Asignar columna ADX
        df['ADX'] = adx_df[f'ADX_{adx_period}']

        # EMAs (Tendencia)
        df['EMA_FAST'] = df.ta.ema(length=settings.EMA_FAST)
        df['EMA_SLOW'] = df.ta.ema(length=settings.EMA_SLOW)

        # RSI + EMA (Rango)
        df['RSI'] = df.ta.rsi(length=settings.RSI_LENGTH)
        df['EMA_FILTER'] = df.ta.ema(length=settings.RSI_EMA_FILTER)

        # Limpieza básica
        df.dropna(inplace=True)
        if len(df) < 2: return None, "WAITING_DATA"

        last = df.iloc[-1]
        prev = df.iloc[-2]
        adx_value = last['ADX']

        # --- 2. SELECCIÓN DE MODO (EL INTERRUPTOR MAESTRO) ---
        
        # Leemos el modo de la memoria
        mode_settings = bot_state.strategy_mode
        
        mode_to_use = None

        if mode_setting == "FORCE_TREND":
            mode_to_use = "TREND"
            
        elif mode_setting == "FORCE_RANGE":
            mode_to_use = "RANGE"
            
        else:
            # === MODO AUTO (TU LÓGICA DE HISTÉRESIS) ===
            
            # 1. Romper hacia arriba: Entrar a Trend
            if adx_value >= settings.ADX_THRESHOLD:
                self.current_mode = "TREND"
            
            # 2. Romper hacia abajo: Volver a Range solo si baja del buffer
            elif adx_value < (settings.ADX_THRESHOLD - 2):
                self.current_mode = "RANGE"
            
            # Si estamos en zona muerta (18-20), mantenemos el modo anterior
            mode_to_use = self.current_mode

        # --- 3. EJECUCIÓN DE LA ESTRATEGIA ACTIVA ---
        
        signal = None
        strategy_name = "WAITING..."

        if mode_to_use == "TREND":
            # === MODO TENDENCIA (EMA CROSS) ===
            # Etiqueta visual para saber si es forzado o natural
            suffix = "(FORCED)" if mode_setting == "FORCE_TREND" else f"(ADX {adx_value:.1f})"
            strategy_name = f"TREND {suffix}"
            
            signal = self._check_ema_cross(last, prev)

        else:
            # === MODO RANGO (RSI + EMA) ===
            suffix = "(FORCED)" if mode_setting == "FORCE_RANGE" else f"(ADX {adx_value:.1f})"
            strategy_name = f"RANGE {suffix}"
            
            signal = self._check_rsi_reversion(last)

        # Retornamos TUPLA para compatibilidad con tu main.py actual
        return signal, strategy_name

    def _check_ema_cross(self, last, prev):
        """Estrategia 1: Cruce de EMAs"""
        # Cruce Alcista
        if prev['EMA_FAST'] <= prev['EMA_SLOW'] and last['EMA_FAST'] > last['EMA_SLOW']:
            return "LONG"
        
        # Cruce Bajista
        if prev['EMA_FAST'] >= prev['EMA_SLOW'] and last['EMA_FAST'] < last['EMA_SLOW']:
            return "SHORT"
            
        return None

    def _check_rsi_reversion(self, last):
        """Estrategia 2: RSI + EMA Filter"""
        rsi = last['RSI']
        price = last['close']
        ema_filter = last['EMA_FILTER']

        # Lógica LONG
        if rsi < settings.RSI_LONG_THRESHOLD and price > ema_filter:
            return "LONG"
        
        # Lógica SHORT
        if rsi > settings.RSI_SHORT_THRESHOLD and price < ema_filter:
            return "SHORT"
            
        return None