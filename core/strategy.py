import pandas as pd
import pandas_ta as ta

class Strategy:
    def __init__(self, rsi_length=14, ema_length=50, 
                 rsi_long_threshold=40, rsi_short_threshold=65, filter_ema=True):
        """
        Configuración Estándar:
        - RSI Long < 40 (Sobreventa)
        - RSI Short > 65 (Sobrecompra)
        - Filter EMA = True (Operar solo a favor de la tendencia)
        """
        self.rsi_length = rsi_length
        self.ema_length = ema_length
        self.rsi_long_threshold = rsi_long_threshold
        self.rsi_short_threshold = rsi_short_threshold
        self.filter_ema = filter_ema

    def analyze(self, df):
        # Calcular indicadores
        df.ta.rsi(length=self.rsi_length, append=True)
        df.ta.ema(length=self.ema_length, append=True)
        
        # Obtener la última vela cerrada
        last_row = df.iloc[-1]
        
        # Extraer valores
        rsi_value = last_row[f'RSI_{self.rsi_length}']
        ema_value = last_row[f'EMA_{self.ema_length}']
        price_value = last_row['close']
        
        # Lógica de Señal LONG (Compra)
        # 1. El RSI debe indicar que está "barato" (menor a 30)
        long_condition = rsi_value < self.rsi_long_threshold
        
        # Lógica de Señal SHORT (Venta)
        # 1. El RSI debe indicar que está "caro" (mayor a 70)
        short_condition = rsi_value > self.rsi_short_threshold
        
        # Filtro de Tendencia (EMA)
        if self.filter_ema:
            # Para LONG: El precio debe estar POR ENCIMA de la EMA (Tendencia Alcista)
            long_condition = long_condition and (price_value > ema_value)
            
            # Para SHORT: El precio debe estar POR DEBAJO de la EMA (Tendencia Bajista)
            short_condition = short_condition and (price_value < ema_value)
        
        # Retorno de decisión
        if long_condition:
            return "LONG"
        elif short_condition:
            return "SHORT"
        
        return None