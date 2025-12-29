import math
from config.settings import settings
from core.execution import ExecutionEngine

class RiskManager:
    def __init__(self, exchange):
        self.exchange = exchange
        self.execution = ExecutionEngine(exchange)

    def _get_available_balance(self):
        """
        Si es LIVE: Consulta el saldo real de USDT en Binance Futures.
        Si es DRY_RUN: Devuelve un saldo virtual.
        """
        if not settings.IS_LIVE:
            return 20.0  # 💰 SALDO VIRTUAL

        try:
            balance = self.exchange.fetch_balance()
            return balance['USDT']['free']
        except Exception as e:
            print(f"[RISK] Error leyendo balance: {e}")
            return 0.0

    def calculate_and_execute(self, signal, current_price, stop_loss_pct, take_profit_pct):
        # 1. Obtener capital disponible
        balance = self._get_available_balance()
        
        if balance <= 0:
            print(f"[RISK] Saldo insuficiente ({balance} USDT).")
            return None

        # 2. CALCULAR TAMAÑO DE POSICIÓN BASADO EN RIESGO
        # Paso A: ¿Cuánto dinero estoy dispuesto a perder? (Ej. 1% de 1000 = $10)
        risk_amount = balance * settings.RISK_PER_TRADE
        
        # Paso B: Calcular el tamaño de la posición (Notional Value)
        # Fórmula: Tamaño = Dinero en Riesgo / % Distancia al Stop Loss
        # Ej: $10 / 0.01 (1%) = $1000 de tamaño de posición.
        target_size_usdt = risk_amount / stop_loss_pct

        # Paso C: Límite de Apalancamiento (Safety Cap)
        # No queremos exceder el apalancamiento configurado (ej. 5x)
        max_position_size = balance * settings.LEVERAGE
        
        if target_size_usdt > max_position_size:
            target_size_usdt = max_position_size
            # print(f"[RISK] Tamaño limitado por apalancamiento máximo ({settings.LEVERAGE}x)")

        # Paso D: Suelo Mínimo de Binance (Min Notional)
        MIN_BINANCE_ORDER = 6.0 
        if target_size_usdt < MIN_BINANCE_ORDER:
            # Si el cálculo da muy poco, forzamos el mínimo si tenemos margen
            if (MIN_BINANCE_ORDER / settings.LEVERAGE) <= balance:
                target_size_usdt = MIN_BINANCE_ORDER
            else:
                print(f"[RISK] Capital insuficiente para la orden mínima de Binance.")
                return None

        # 3. Convertir USDT a Cantidad de Cripto
        quantity = target_size_usdt / current_price
        
        # 4. Normalizar cantidad
        quantity = self._normalize_quantity(quantity)

        # 5. Ejecutar
        print(f"[RISK] Balance: {balance:.2f} | Risk: ${risk_amount:.2f} | Size: {target_size_usdt:.2f} USDT")
        
        side = 'buy' if signal == 'LONG' else 'sell'
        
        # Ejecutar Entrada
        order = self.execution.place_entry_order(settings.SYMBOL, side, quantity, current_price)
        
        if order:
            # Calcular precios de TP/SL
            if side == 'buy':
                sl_price = current_price * (1 - stop_loss_pct)
                tp_price = current_price * (1 + take_profit_pct)
            else:
                sl_price = current_price * (1 + stop_loss_pct)
                tp_price = current_price * (1 - take_profit_pct)

            # Normalizar precios
            sl_price = self.exchange.price_to_precision(settings.SYMBOL, sl_price)
            tp_price = self.exchange.price_to_precision(settings.SYMBOL, tp_price)

            # Ejecutar OCO (SL/TP)
            self.execution.place_oco_orders(settings.SYMBOL, side, quantity, current_price, sl_price, tp_price)
            
            # Agregamos datos extra al resultado
            order['average'] = current_price 
            return order
            
        return None

    def _normalize_quantity(self, quantity):
        # Cargar mercados si no están cargados (vital para cambiar de moneda)
        if not self.exchange.markets:
            self.exchange.load_markets()
            
        try:
            # Usar la precisión específica de SOL/USDT definida por Binance
            market = self.exchange.market(settings.SYMBOL)
            return self.exchange.amount_to_precision(settings.SYMBOL, quantity)
        except Exception as e:
            print(f"[RISK] Error normalizando cantidad: {e}")
            # Fallback seguro: 2 decimales para SOL (usualmente acepta 2 o 3)
            return round(quantity, 2)