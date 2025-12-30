import os
from config.settings import settings
from utils.telegram_bot import send_message # <--- IMPORTAR ESTO

class ExecutionEngine:
    def __init__(self, exchange):
        self.exchange = exchange
    
    # ... (place_entry_order, place_oco_orders, check_active_position IGUAL QUE ANTES) ...
    # SOLO VOY A MOSTRAR LOS MÉTODOS QUE NECESITAN CAMBIOS, MANTÉN LOS DEMÁS IGUAL.

    def place_entry_order(self, symbol, side, quantity, price=None):
        # ... (Tu código existente sin cambios aquí) ...
        # (Copia tu función original aquí, no hay cambios lógicos, solo espacio)
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

    # ... (place_oco_orders y check_active_position SIN CAMBIOS) ...
    def place_oco_orders(self, symbol, side, quantity, entry_price, sl_price, tp_price):
         # ... (Tu código existente) ...
         pass 

    def check_active_position(self, symbol):
         # ... (Tu código existente) ...
         pass

    def get_position_details(self, symbol):
         # ... (Tu código existente) ...
         try:
            positions = self.exchange.fetch_positions([symbol])
            for pos in positions:
                if pos['symbol'] == symbol:
                    return {
                        'amt': float(pos['contracts']), 
                        'entryPrice': float(pos['entryPrice'])
                    }
            return None
         except Exception as e:
            print(f"[EXEC ERROR] No se pudo leer posición: {e}")
            return None

    def update_trailing_stop(self, symbol, new_sl_price, side):
        """
        Actualiza el SL en Binance y NOTIFICA a Telegram.
        """
        try:
            self.exchange.cancel_all_orders(symbol)
            
            sl_side = 'sell' if side == 'buy' else 'buy'
            
            params = {
                'stopPrice': new_sl_price,
                'closePosition': True 
            }
            
            self.exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side=sl_side,
                amount=None, 
                price=None,
                params=params
            )
            
            print(f"[EXEC] SL actualizado exitosamente a {new_sl_price}")
            
            # --- NUEVO: Notificación Enriquecida ---
            msg = (f"🛡️ <b>TRAILING STOP ACTIVADO</b>\n"
                   f"Simbolo: <b>{symbol}</b>\n"
                   f"Nuevo SL: <code>{new_sl_price:.4f}</code>\n"
                   f"<i>Ganancia asegurada.</i>")
            send_message(msg)
            # ---------------------------------------

            return True

        except Exception as e:
            print(f"[EXEC ERROR] Fallo al actualizar SL: {e}")
            return False