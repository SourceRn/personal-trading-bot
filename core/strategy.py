import pandas as pd
import pandas_ta as ta
from config.settings import settings

class Strategy:
    def __init__(self):
        # Inicializamos en RANGE por seguridad (más conservador al inicio)
        self.current_mode = "RANGE"

    def analyze(self, df):
        """
        Analiza el mercado y decide qué estrategia usar basado en el ADX.
        Retorna: (Señal, Nombre_Estrategia)
        Ejemplo: ("LONG", "EMA_CROSS") o (None, "RSI_RANGE")
        """
        # --- 1. CALCULO DE INDICADORES ---
        # ADX (El Juez)
        adx_df = df.ta.adx(length=settings.ADX_PERIOD)
        if adx_df is None or adx_df.empty: return None, "WAITING_DATA"
        
        # Asignamos el valor actual del ADX a la columna 'ADX' del df principal
        df['ADX'] = adx_df[f'ADX_{settings.ADX_PERIOD}']

        # EMAs para Cruce (Tendencia)
        df['EMA_FAST'] = df.ta.ema(length=settings.EMA_FAST)
        df['EMA_SLOW'] = df.ta.ema(length=settings.EMA_SLOW)

        # Indicadores para Rango (RSI + EMA Filtro)
        df['RSI'] = df.ta.rsi(length=settings.RSI_LENGTH)
        df['EMA_FILTER'] = df.ta.ema(length=settings.RSI_EMA_FILTER)

        # Limpieza de NaNs (necesario al inicio)
        df.dropna(inplace=True)
        if len(df) < 2: return None, "WAITING_DATA"

        # Datos actuales y previos (para detectar cruces)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # --- 2. EL JUEZ: SELECCIÓN DE ESTRATEGIA CON HISTÉRESIS ---
        adx_value = last['ADX']
        
        # Lógica de Histéresis (Buffer de 5 puntos para evitar parpadeo)
        # Solo cambiamos a TREND si el ADX rompe con fuerza hacia arriba
        if adx_value >= settings.ADX_THRESHOLD:
            self.current_mode = "TREND"
        
        # Solo regresamos a RANGE si el ADX se debilita claramente (Threshold - 5)
        # Ejemplo: Si umbral es 25, debe bajar de 20 para volver a Range.
        elif adx_value < (settings.ADX_THRESHOLD - 5):
            self.current_mode = "RANGE"
            
        # NOTA: Si el ADX está entre 20 y 25, self.current_mode NO cambia.
        # Esto elimina el ruido cuando el ADX oscila (24.9 -> 25.1 -> 24.8).

        # --- 3. EJECUCIÓN DE LA ESTRATEGIA ACTIVA ---
        if self.current_mode == "TREND":
            # === MODO TENDENCIA (EMA CROSS) ===
            strategy_name = f"TREND (ADX {adx_value:.1f})"
            signal = self._check_ema_cross(last, prev)
        else:
            # === MODO RANGO (RSI + EMA) ===
            strategy_name = f"RANGE (ADX {adx_value:.1f})"
            signal = self._check_rsi_reversion(last)

        return signal, strategy_name

    def _check_ema_cross(self, last, prev):
        """Estrategia 1: Cruce de EMAs"""
        # Cruce Alcista (Golden Cross): Rápida cruza hacia arriba a la Lenta
        if prev['EMA_FAST'] <= prev['EMA_SLOW'] and last['EMA_FAST'] > last['EMA_SLOW']:
            return "LONG"
        
        # Cruce Bajista (Death Cross): Rápida cruza hacia abajo a la Lenta
        if prev['EMA_FAST'] >= prev['EMA_SLOW'] and last['EMA_FAST'] < last['EMA_SLOW']:
            return "SHORT"
            
        return None

    def _check_rsi_reversion(self, last):
        """Estrategia 2: Tu estrategia original (RSI + EMA Filter)"""
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