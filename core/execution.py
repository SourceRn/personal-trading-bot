import os
from config.settings import settings

class ExecutionEngine:
    def __init__(self, exchange):
        self.exchange = exchange
    
    def place_entry_order(self, symbol, side, quantity, price=None):
        print(f"--- ORDER REQUEST ({settings.TRADING_MODE}) ---")
        print(f"Side: {side} | Qty: {quantity} | Symbol: {symbol}")

        if not settings.IS_LIVE:
            return {
                'id': f'sim_{os.urandom(4).hex()}',
                'status': 'closed',
                'average': price,
                'symbol': symbol,
                'side': side,
                'amount': quantity
            }

        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side.lower(),
                amount=quantity
            )
            print(f"Order Executed: {order['id']}")
            return order
        except Exception as e:
            print(f"EXECUTION ERROR: {e}")
            return None

    def place_oco_orders(self, symbol, side, quantity, entry_price, sl_price, tp_price):
        if not settings.IS_LIVE:
            print(f" [SIMULATION] Virtual SL: {sl_price}")
            print(f" [SIMULATION] Virtual TP: {tp_price}")
            return

        sl_side = 'sell' if side == 'buy' else 'buy'
        
        try:
            self.exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side=sl_side,
                amount=quantity,
                params={'stopPrice': sl_price}
            )
            print(f"Stop Loss set at {sl_price}")

            self.exchange.create_order(
                symbol=symbol,
                type='TAKE_PROFIT_MARKET',
                side=sl_side,
                amount=quantity,
                params={'stopPrice': tp_price}
            )
            print(f"Take Profit set at {tp_price}")

        except Exception as e:
            print(f"OCO ERROR: {e}")

    def check_active_position(self, symbol):
        """
        Devuelve la cantidad (size) de la posición actual.
        Si es 0, no hay posición.
        """
        if not settings.IS_LIVE:
            # En Dry Run, la gestión de estado se hace en memoria (main.py)
            return 0.0

        try:
            # fetch_positions es específico para Futuros
            positions = self.exchange.fetch_positions([symbol])
            for pos in positions:
                if pos['symbol'] == symbol:
                    return float(pos['contracts']) # o pos['info']['positionAmt']
            return 0.0
        except Exception as e:
            print(f"[EXECUTION] Error verificando posiciones: {e}")
            return 0.0