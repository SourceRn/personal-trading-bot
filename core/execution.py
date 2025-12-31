import os
from config.settings import settings
from utils.telegram_bot import send_message

class ExecutionEngine:
    def __init__(self, exchange):
        self.exchange = exchange
    
    def place_entry_order(self, symbol, side, quantity, price=None):
        """
        Ejecuta una orden de mercado para entrar en posición.
        """
        print(f"--- ORDER REQUEST ({settings.TRADING_MODE}) ---")
        print(f"Side: {side} | Qty: {quantity} | Symbol: {symbol}")

        if not settings.IS_LIVE:
            return {
                'id': f'sim_{os.urandom(4).hex()}',
                'status': 'closed',
                'average': price if price else 0.0,
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
            print(f"✅ Order Executed: {order['id']}")
            return order
        except Exception as e:
            msg = f"❌ EXECUTION ERROR: {str(e)}"
            print(msg)
            send_message(msg)
            return None

    def place_oco_orders(self, symbol, side, quantity, entry_price, sl_price, tp_price):
        """
        Coloca Stop Loss y Take Profit iniciales.
        """
        if not settings.IS_LIVE:
            return

        try:
            close_side = 'sell' if side == 'buy' else 'buy'
            
            # 1. STOP LOSS
            sl_params = {'stopPrice': sl_price, 'closePosition': True}
            self.exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side=close_side,
                amount=None,
                price=None,
                params=sl_params
            )
            print(f"🛡️ Stop Loss puesto en: {sl_price}")

            # 2. TAKE PROFIT
            tp_params = {'stopPrice': tp_price, 'closePosition': True}
            self.exchange.create_order(
                symbol=symbol,
                type='TAKE_PROFIT_MARKET',
                side=close_side,
                amount=None,
                price=None,
                params=tp_params
            )
            print(f"💰 Take Profit puesto en: {tp_price}")
            
        except Exception as e:
            print(f"⚠️ Error colocando OCO (SL/TP): {e}")
            send_message(f"⚠️ <b>Advertencia SL/TP:</b>\n{str(e)}")

    def check_active_position(self, symbol):
        if not settings.IS_LIVE:
            return False
        try:
            pos = self.get_position_details(symbol)
            if pos and float(pos['amt']) != 0:
                return True
            return False
        except Exception:
            return False

    def get_position_details(self, symbol):
        """
        Obtiene los detalles de la posición actual con NORMALIZACIÓN AGRESIVA.
        Resuelve el problema de 'SOLUSDT' vs 'SOL/USDT:USDT'.
        """
        if not settings.IS_LIVE:
            return None

        try:
            # Pedimos TODO a Binance
            all_positions = self.exchange.fetch_positions()
            target_position = None

            # --- FUNCIÓN DE LIMPIEZA (FILTRO NUCLEAR) ---
            # Convierte "SOL/USDT:USDT" -> "SOLUSDT"
            # Convierte "SOL/USDT" -> "SOLUSDT"
            def clean_symbol(s):
                if not s: return ""
                return s.replace("/", "").split(":")[0]
            # --------------------------------------------

            # Limpiamos el símbolo que buscamos (el de settings)
            target_clean = clean_symbol(symbol)

            for p in all_positions:
                api_symbol = p['symbol']
                api_clean = clean_symbol(api_symbol)
                
                # Extraemos cantidad de forma segura
                raw_amt = p.get('contracts') or p.get('amount') or p.get('info', {}).get('positionAmt', 0)
                amt = float(raw_amt)
                
                # Debug solo si encontramos dinero real (para no llenar el log)
                if amt != 0:
                    print(f"🔎 REVISANDO: API='{api_symbol}' (Clean: {api_clean}) vs TARGET='{symbol}' (Clean: {target_clean})")

                # COMPARACIÓN: Si los nombres limpios son iguales, ES LA NUESTRA
                if target_clean == api_clean:
                    target_position = p
                    break
            
            if target_position:
                raw_amt = target_position.get('contracts') or target_position.get('amount') or target_position.get('info', {}).get('positionAmt', 0)
                entry_price = target_position.get('entryPrice') or target_position.get('info', {}).get('entryPrice', 0)
                
                return {
                    'symbol': target_position['symbol'], # Devolvemos el símbolo real de Binance
                    'amt': float(raw_amt),
                    'entryPrice': float(entry_price)
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
            
            msg = (f"🛡️ <b>TRAILING STOP ACTIVADO</b>\n"
                   f"Simbolo: <b>{symbol}</b>\n"
                   f"Nuevo SL: <code>{new_sl_price:.4f}</code>\n"
                   f"<i>Ganancia protegida.</i>")
            send_message(msg)

            return True

        except Exception as e:
            print(f"[EXEC ERROR] Fallo al actualizar SL: {e}")
            send_message(f"⚠️ <b>Error Trailing Stop:</b> {str(e)}")
            return False