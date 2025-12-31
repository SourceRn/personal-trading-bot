import os
from config.settings import settings
from utils.telegram_bot import send_message

class ExecutionEngine:
    def __init__(self, exchange):
        self.exchange = exchange
    
    def place_entry_order(self, symbol, side, quantity, price=None):
        """
        Ejecuta una orden de mercado para entrar en posición.
        Maneja tanto modo LIVE como simulación (Dry Run).
        """
        print(f"--- ORDER REQUEST ({settings.TRADING_MODE}) ---")
        print(f"Side: {side} | Qty: {quantity} | Symbol: {symbol}")

        # --- MODO SIMULACIÓN ---
        if not settings.IS_LIVE:
            return {
                'id': f'sim_{os.urandom(4).hex()}',
                'status': 'closed',
                'average': price if price else 0.0,
                'symbol': symbol,
                'side': side,
                'amount': quantity
            }

        # --- MODO REAL ---
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
            error_msg = f"❌ EXECUTION ERROR: {str(e)}"
            print(error_msg)
            send_message(f"🚨 <b>Error de Ejecución:</b>\n{str(e)}")
            return None

    def place_oco_orders(self, symbol, side, quantity, entry_price, sl_price, tp_price):
        """
        Coloca Stop Loss y Take Profit iniciales.
        En Binance Futures, esto se hace enviando dos órdenes condicionales separadas.
        """
        if not settings.IS_LIVE:
            return # En simulacion lo maneja el main loop

        try:
            # Definir lado opuesto para cerrar
            close_side = 'sell' if side == 'buy' else 'buy'
            
            # 1. STOP LOSS
            sl_params = {'stopPrice': sl_price, 'closePosition': True}
            self.exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side=close_side,
                amount=None, # closePosition=True no requiere monto
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
            send_message(f"⚠️ <b>Advertencia:</b> SL/TP no se pudieron colocar automáticamente.\n{str(e)}")

    def check_active_position(self, symbol):
        """
        Verifica si hay una posición abierta consultando el saldo de la moneda.
        """
        if not settings.IS_LIVE:
            return False

        try:
            # Obtenemos detalles completos
            pos = self.get_position_details(symbol)
            if pos and float(pos['amt']) != 0:
                return True
            return False
        except Exception:
            return False

    def get_position_details(self, symbol):
        """
        Obtiene los detalles de la posición actual (Tamaño, Precio Entrada).
        Incluye depuración para arreglar el problema del nombre del símbolo.
        """
        if not settings.IS_LIVE:
            return None

        try:
            # Obtenemos TODAS las posiciones de riesgo del usuario
            # Usamos fetch_positions sin argumentos para ver todo lo que hay
            all_positions = self.exchange.fetch_positions()
            
            # --- BLOQUE DE DEPURACIÓN (TEMPORAL) ---
            # Esto imprimirá en el log qué símbolos está viendo realmente el bot
            # Solo imprime si encuentra posiciones abiertas para no saturar
            # ---------------------------------------
            
            target_position = None

            for p in all_positions:
                # Estandarizamos el simbolo que viene de la API para compararlo
                api_symbol = p['symbol']
                
                # Extraemos la cantidad (puede venir como 'contracts', 'amount' o 'positionAmt')
                raw_amt = p.get('contracts') or p.get('amount') or p.get('info', {}).get('positionAmt', 0)
                amt = float(raw_amt)

                # Si tiene cantidad distinta de 0, imprimimos para depurar
                if amt != 0:
                    print(f"🔎 POSICIÓN ENCONTRADA: Símbolo='{api_symbol}' | Amt={amt}")

                # Lógica de coincidencia flexible
                # Comparamos: 'SOL/USDT' (config) con 'SOL/USDT:USDT' (api) o 'SOLUSDT'
                # 1. Coincidencia exacta
                if api_symbol == symbol:
                    target_position = p
                    break
                
                # 2. Coincidencia parcial (Si symbol es 'SOL/USDT' y api es 'SOL/USDT:USDT')
                if symbol in api_symbol: 
                    target_position = p
                    break
                
                # 3. Coincidencia sin barra (Si symbol es 'SOL/USDT' y api es 'SOLUSDT')
                symbol_no_slash = symbol.replace("/", "")
                if symbol_no_slash == api_symbol:
                    target_position = p
                    break

            if target_position:
                # Normalizamos los datos de retorno
                raw_amt = target_position.get('contracts') or target_position.get('amount') or target_position.get('info', {}).get('positionAmt', 0)
                entry_price = target_position.get('entryPrice') or target_position.get('info', {}).get('entryPrice', 0)
                
                return {
                    'symbol': target_position['symbol'],
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
        Primero cancela órdenes abiertas y luego pone la nueva.
        """
        try:
            # 1. Cancelar órdenes abiertas para este par (quita el SL anterior)
            self.exchange.cancel_all_orders(symbol)
            
            # 2. Definir lado de cierre
            sl_side = 'sell' if side == 'buy' else 'buy'
            
            params = {
                'stopPrice': new_sl_price,
                'closePosition': True 
            }
            
            # 3. Crear nueva orden de Stop
            self.exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side=sl_side,
                amount=None, 
                price=None,
                params=params
            )
            
            print(f"[EXEC] SL actualizado exitosamente a {new_sl_price}")
            
            # Notificación
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