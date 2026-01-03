import time
import threading
import sys
import os
import pandas as pd
from datetime import datetime

# Módulos propios
from core.api_connector import BinanceConnector
from core.strategy import Strategy
from core.risk_manager import RiskManager
from core.execution import ExecutionEngine 
from core.shared_state import bot_state
from utils.telegram_bot import send_message
from utils.telegram_listener import start_telegram_listener
from config.settings import settings

def fetch_data(exchange, symbol, timeframe):
    bars = exchange.fetch_ohlcv(symbol, timeframe, limit=300)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def run_bot():
    # --- INICIO DEL HILO DE TELEGRAM (LISTENER) ---
    t_listener = threading.Thread(target=start_telegram_listener, daemon=True)
    t_listener.start()
    
    # --- INICIALIZACIÓN ---
    print("🚀 Inicializando componentes...")
    connector = BinanceConnector()
    exchange = connector.get_exchange()
    strategy = Strategy()
    risk_manager = RiskManager(exchange)
    execution_engine = ExecutionEngine(exchange) 
    
    dry_run_position = None 
    
    # Variables locales
    last_strategy_name = "INICIANDO..."
    tp_alert_sent = False
    sl_alert_sent = False
    active_tp_price = 0.0
    active_sl_price = 0.0
    
    # Estado inicial
    bot_state.mode = "LIVE" if settings.IS_LIVE else "DRY RUN"
    
    # Cargamos el modo por defecto desde settings a la memoria dinámica
    # (Esto permite que el comando /mode funcione desde el inicio)
    bot_state.strategy_mode = settings.STRATEGY_MODE 
    
    # Intento inicial de obtener balance
    try:
        bot_state.balance_total = risk_manager._get_available_balance()
    except:
        bot_state.balance_total = 0.0

    startup_msg = (f"🤖 <b>Protocol Zero-Emotion Started</b>\n"
                   f"Service PID: {os.getpid()}\n"
                   f"Mode: <b>{bot_state.mode}</b>\n"
                   f"Strategy Mode: <b>{bot_state.strategy_mode}</b>\n"
                   f"Timeframe: <b>{settings.TIMEFRAME}</b>\n"
                   f"Listener: ACTIVO ✅")
    print(startup_msg)
    sys.stdout.flush() 
    send_message(startup_msg)

    try:
        while bot_state.running: 
            
            # --- GESTIÓN DE RIESGO PROFESIONAL ---
            percentage_limit = bot_state.balance_total * settings.MAX_DAILY_LOSS
            min_usd_floor = getattr(settings, 'MIN_DAILY_LOSS_USD', 1.0)
            final_limit_usd = max(percentage_limit, min_usd_floor)

            if bot_state.daily_pnl <= (final_limit_usd * -1):
                stop_msg = f"⛔ BOT DETENIDO: Límite de pérdida diaria alcanzado ({bot_state.daily_pnl:.2f} USDT)"
                print(stop_msg)
                send_message(stop_msg)
                break 

            # -------------------------------------

            # 1. OBTENCIÓN DE DATOS
            try:
                df = fetch_data(exchange, settings.SYMBOL, settings.TIMEFRAME)
            except Exception as e:
                print(f"Error fetching data: {e}")
                time.sleep(10)
                continue

            # Análisis
            # La estrategia lee bot_state.strategy_mode internamente
            signal_data = strategy.analyze(df) 
            
            # Desempaquetado seguro (Tuple vs None)
            if signal_data:
                signal = signal_data[0]
                strategy_name = signal_data[1]
            else:
                signal = None
                strategy_name = "WAITING..."

            current_price = df.iloc[-1]['close']
            
            # Telemetría
            bot_state.last_price = current_price
            bot_state.strategy_name = strategy_name
            if 'RSI' in df.columns: bot_state.rsi = df.iloc[-1]['RSI']
            if 'ADX' in df.columns: bot_state.adx = df.iloc[-1]['ADX']

            # Detección Cambio Estrategia (Visual)
            current_strat_base = strategy_name.split(" ")[0]
            last_strat_base = last_strategy_name.split(" ")[0]

            if current_strat_base != last_strat_base:
                send_message(f"🔄 <b>Cambio de Estrategia</b>: {last_strat_base} -> <b>{current_strat_base}</b>")
            last_strategy_name = strategy_name

            # 2. GESTIÓN DE POSICIONES
            in_position = False
            
            # --- SELECCIÓN AUTOMÁTICA DE PARÁMETROS DE TRAILING ---
            # Determinamos qué configuración usar según el nombre de la estrategia activa
            # o el tipo de posición que estamos gestionando.
            if "TREND" in strategy_name or "TREND" in last_strategy_name:
                active_trailing_trigger = settings.TREND_TRAILING_TRIGGER
                active_trailing_step = settings.TREND_TRAILING_STEP
            else:
                active_trailing_trigger = settings.RANGE_TRAILING_TRIGGER
                active_trailing_step = settings.RANGE_TRAILING_STEP

            # --- LÓGICA LIVE ---
            if settings.IS_LIVE:
                if not in_position:
                    try:
                        bot_state.balance_total = risk_manager._get_available_balance()
                    except: pass

                position_data = execution_engine.get_position_details(settings.SYMBOL)
                
                if position_data and float(position_data['amt']) != 0:
                    in_position = True
                    qty = float(position_data['amt'])
                    entry_price = float(position_data['entryPrice'])
                    side = 'buy' if qty > 0 else 'sell'
                    
                    bot_state.in_position = True
                    bot_state.pos_type = "LONG" if side == 'buy' else "SHORT"
                    bot_state.entry_price = entry_price
                    pnl_pct_real = (current_price - entry_price) / entry_price if side == 'buy' else (entry_price - current_price) / entry_price
                    bot_state.current_pnl_pct = pnl_pct_real
                    
                    # Inicialización de precios TP/SL visuales si se reinició el bot
                    if active_tp_price == 0: 
                        tp_factor = (1 + settings.TAKE_PROFIT_PCT) if side == 'buy' else (1 - settings.TAKE_PROFIT_PCT)
                        sl_factor = (1 - settings.STOP_LOSS_PCT) if side == 'buy' else (1 + settings.STOP_LOSS_PCT)
                        active_tp_price = entry_price * tp_factor
                        active_sl_price = entry_price * sl_factor

                    # ==========================================
                    #    TRAILING STOP DINÁMICO (AUTOMATIZADO)
                    # ==========================================
                    should_update = False
                    new_sl_price = 0.0
                    
                    # Usamos active_trailing_trigger y step seleccionados arriba automáticamente
                    if pnl_pct_real >= active_trailing_trigger:
                        
                        if side == 'buy':
                            # SL persigue al precio desde abajo
                            target_sl = current_price * (1 - active_trailing_step)
                            if target_sl > active_sl_price:
                                new_sl_price = target_sl
                                should_update = True
                        
                        elif side == 'sell':
                            # SL persigue al precio desde arriba
                            target_sl = current_price * (1 + active_trailing_step)
                            if active_sl_price == 0 or target_sl < active_sl_price:
                                new_sl_price = target_sl
                                should_update = True
                    
                    if should_update:
                        print(f"🔄 Trailing Stop ({'TREND' if 'TREND' in strategy_name else 'RANGE'}): Moviendo SL a {new_sl_price:.4f}")
                        success = execution_engine.update_trailing_stop(settings.SYMBOL, new_sl_price, side)
                        if success:
                            active_sl_price = new_sl_price 
                            time.sleep(2)
                    # ==========================================

                else:
                    bot_state.in_position = False 

            # --- LÓGICA DRY RUN ---
            else:
                if dry_run_position:
                    in_position = True
                    entry = dry_run_position['entry']
                    sl = dry_run_position['sl']
                    tp = dry_run_position['tp']
                    side = dry_run_position['side']
                    qty_held = dry_run_position.get('qty', 0.0)
                    
                    # Sincronización visual
                    active_sl_price = sl
                    active_tp_price = tp
                    
                    bot_state.in_position = True
                    bot_state.pos_type = "LONG" if side == 'buy' else "SHORT"
                    bot_state.entry_price = entry
                    pnl_pct_sim = (current_price - entry) / entry if side == 'buy' else (entry - current_price) / entry
                    bot_state.current_pnl_pct = pnl_pct_sim

                    # TRAILING STOP DRY RUN (DINÁMICO)
                    new_sl = None
                    sl_changed = False
                    
                    if pnl_pct_sim >= active_trailing_trigger:
                        if side == 'buy':
                            target_sl = current_price * (1 - active_trailing_step)
                            if sl < target_sl: 
                                new_sl = target_sl; sl_changed = True
                        elif side == 'sell':
                            target_sl = current_price * (1 + active_trailing_step)
                            if sl > target_sl: 
                                new_sl = target_sl; sl_changed = True
                    
                    if sl_changed and new_sl:
                        dry_run_position['sl'] = new_sl
                        active_sl_price = new_sl
                        send_message(f"🛡️ <b>SL ACTUALIZADO</b> a <code>{new_sl:.2f}</code> (Trailing)")
                        sl = new_sl 

                    # Cierre Dry Run
                    close_signal = None
                    if side == 'buy':
                        if current_price <= sl: close_signal = "STOP LOSS"
                        elif current_price >= tp: close_signal = "TAKE PROFIT"     
                    elif side == 'sell':
                        if current_price >= sl: close_signal = "STOP LOSS"
                        elif current_price <= tp: close_signal = "TAKE PROFIT"
                    
                    if close_signal:
                        price_diff = (current_price - entry) if side == 'buy' else (entry - current_price)
                        realized_pnl = price_diff * qty_held
                        bot_state.daily_pnl += realized_pnl 
                        
                        emoji = "✅" if realized_pnl > 0 else "❌"
                        msg = (f"{emoji} <b>Posición CERRADA</b> ({close_signal})\n"
                               f"PnL: <b>{realized_pnl:.4f} USDT</b>\n"
                               f"Cierre: {current_price}")
                        send_message(msg)
                        
                        dry_run_position = None 
                        in_position = False
                        bot_state.in_position = False
                        active_sl_price = 0.0; active_tp_price = 0.0
                        tp_alert_sent = False; sl_alert_sent = False
                        time.sleep(300) 
                else:
                    bot_state.in_position = False

            # --- ALERTAS DE PROXIMIDAD ---
            if in_position and active_tp_price > 0 and active_sl_price > 0:
                dist_tp = abs(active_tp_price - current_price) / current_price
                dist_sl = abs(current_price - active_sl_price) / current_price
                
                if dist_tp <= settings.ALERT_PROXIMITY_PCT and not tp_alert_sent:
                    send_message(f"🚀 <b>Cerca del TP</b> ({dist_tp*100:.2f}%)")
                    tp_alert_sent = True
                
                if dist_sl <= settings.ALERT_PROXIMITY_PCT and not sl_alert_sent:
                    send_message(f"⚠️ <b>Cerca del SL</b> ({dist_sl*100:.2f}%)")
                    sl_alert_sent = True
            else:
                tp_alert_sent = False; sl_alert_sent = False

            # --- EXECUTION (Entrada) ---
            if not in_position and signal:
                if "TREND" in strategy_name:
                    dynamic_sl = settings.TREND_SL; dynamic_tp = settings.TREND_TP
                else:
                    dynamic_sl = settings.RANGE_SL; dynamic_tp = settings.RANGE_TP
                
                print(f"SIGNAL: {signal} | SL: {dynamic_sl} | TP: {dynamic_tp}")
                
                order_result = risk_manager.calculate_and_execute(
                    signal, current_price, dynamic_sl, dynamic_tp
                )
                
                if order_result:
                    exec_price = float(order_result.get('average', current_price))
                    quantity = float(order_result.get('amount', 0))
                    
                    if signal == 'LONG':
                        sl_price = exec_price * (1 - dynamic_sl)
                        tp_price = exec_price * (1 + dynamic_tp)
                        side_emoji = "🟢"
                    else:
                        sl_price = exec_price * (1 + dynamic_sl)
                        tp_price = exec_price * (1 - dynamic_tp)
                        side_emoji = "🔴"
                    
                    active_sl_price = sl_price
                    active_tp_price = tp_price

                    msg = (f"{side_emoji} <b>ORDEN EJECUTADA</b>\n"
                           f"Estrategia: <b>{strategy_name}</b>\n"
                           f"Entrada: ${exec_price:,.2f}\n"
                           f"SL: ${sl_price:,.2f} | TP: ${tp_price:,.2f}")
                    send_message(msg)

                    if not settings.IS_LIVE:
                        dry_run_position = {
                            'entry': exec_price, 'sl': sl_price, 'tp': tp_price,
                            'side': 'buy' if signal == 'LONG' else 'sell', 'qty': quantity
                        }

            # Flush logs
            sys.stdout.flush()
            time.sleep(60) 
            
    except KeyboardInterrupt:
        send_message("⚠️ <b>Bot detenido manualmente</b>")
    except Exception as e:
        send_message(f"🚨 <b>ERROR CRÍTICO:</b> {str(e)}")
        print(f"CRITICAL ERROR: {e}")
    finally:
        send_message("🛑 <b>Servicio APAGADO</b>")

if __name__ == "__main__":
    run_bot()