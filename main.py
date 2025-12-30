import time
import pandas as pd
from core.api_connector import BinanceConnector
from core.strategy import Strategy
from core.risk_manager import RiskManager
from core.execution import ExecutionEngine 
from utils.telegram_bot import send_message
from config.settings import settings

def fetch_data(exchange, symbol, timeframe):
    bars = exchange.fetch_ohlcv(symbol, timeframe, limit=300)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def run_bot():
    connector = BinanceConnector()
    exchange = connector.get_exchange()
    
    strategy = Strategy()
    risk_manager = RiskManager(exchange)
    execution_engine = ExecutionEngine(exchange) 
    
    dry_run_position = None 
    
    # --- VARIABLES DE ESTADO ---
    last_strategy_name = "INICIANDO..."
    tp_alert_sent = False
    sl_alert_sent = False
    active_tp_price = 0.0
    active_sl_price = 0.0
    # ---------------------------

    daily_pnl = 0.0
    initial_balance = risk_manager._get_available_balance()
    max_loss_usdt = initial_balance * settings.MAX_DAILY_LOSS
    
    mode_label = "🚨 LIVE TRADING 🚨" if settings.IS_LIVE else "DRY RUN (Paper Trading)"
    
    startup_msg = (f"🤖 <b>Protocol Zero-Emotion Started</b>\n"
                   f"Symbol: <code>{settings.SYMBOL}</code>\n"
                   f"Mode: <b>{mode_label}</b>\n"
                   f"Timeframe: <b>{settings.TIMEFRAME}</b>\n"
                   f"Daily Loss Limit: -{max_loss_usdt:.2f} USDT")
    print(startup_msg)
    send_message(startup_msg)

    try:
        while True:
            # 0. VERIFICACIÓN DE SEGURIDAD
            if daily_pnl <= -max_loss_usdt:
                stop_msg = (f"⛔ <b>BOT DETENIDO</b>: Límite de pérdida diaria alcanzado.\n"
                            f"PnL Hoy: {daily_pnl:.2f} USDT")
                print(stop_msg)
                send_message(stop_msg)
                break 

            # 1. Obtener datos
            try:
                df = fetch_data(exchange, settings.SYMBOL, settings.TIMEFRAME)
            except Exception as e:
                print(f"Error fetching data: {e}")
                time.sleep(10)
                continue

            signal, strategy_name = strategy.analyze(df) 
            current_price = df.iloc[-1]['close']
            
            # --- DETECCIÓN CAMBIO DE ESTRATEGIA (ANTI-SPAM) ---
            current_strat_base = strategy_name.split(" ")[0]
            last_strat_base = last_strategy_name.split(" ")[0]

            if current_strat_base != last_strat_base:
                strat_msg = (f"🔄 <b>Cambio de Estrategia Detectado</b>\n"
                             f"Anterior: {last_strategy_name}\n"
                             f"Actual: <b>{strategy_name}</b>")
                send_message(strat_msg)
                
            last_strategy_name = strategy_name
            # --------------------------------------------------
            
            # 2. GESTIÓN DE POSICIONES
            in_position = False

            if settings.IS_LIVE:
                position_data = execution_engine.get_position_details(settings.SYMBOL)
                
                if position_data and float(position_data['amt']) != 0:
                    in_position = True
                    qty = float(position_data['amt'])
                    entry_price = float(position_data['entryPrice'])
                    side = 'buy' if qty > 0 else 'sell'
                    
                    # Recuperación de precios objetivo si se reinició el bot
                    if active_tp_price == 0: 
                        # Usamos valores por defecto para recuperar
                        tp_factor = (1 + settings.TAKE_PROFIT_PCT) if side == 'buy' else (1 - settings.TAKE_PROFIT_PCT)
                        sl_factor = (1 - settings.STOP_LOSS_PCT) if side == 'buy' else (1 + settings.STOP_LOSS_PCT)
                        active_tp_price = entry_price * tp_factor
                        active_sl_price = entry_price * sl_factor

                    # --- TRAILING STOP LOGIC (LIVE) ---
                    should_update = False
                    new_sl_price = 0.0
                    
                    if side == 'buy':
                        pnl_pct = (current_price - entry_price) / entry_price
                        if pnl_pct >= settings.TRAILING_TRIGGER:
                            target_sl = entry_price * (1 + settings.TRAILING_STEP)
                            if target_sl > entry_price: 
                                new_sl_price = target_sl
                                should_update = True
                    elif side == 'sell':
                        pnl_pct = (entry_price - current_price) / entry_price
                        if pnl_pct >= settings.TRAILING_TRIGGER:
                            target_sl = entry_price * (1 - settings.TRAILING_STEP)
                            if target_sl < entry_price:
                                new_sl_price = target_sl
                                should_update = True
                    
                    if should_update:
                        success = execution_engine.update_trailing_stop(settings.SYMBOL, new_sl_price, side)
                        if success:
                            active_sl_price = new_sl_price 
                            time.sleep(5) 
            
            else:
                # DRY RUN LOGIC
                if dry_run_position:
                    in_position = True
                    entry = dry_run_position['entry']
                    sl = dry_run_position['sl']
                    tp = dry_run_position['tp']
                    side = dry_run_position['side']
                    qty_held = dry_run_position.get('qty', 0.0)
                    
                    active_sl_price = sl
                    active_tp_price = tp

                    # Trailing Stop Dry Run
                    new_sl = None
                    sl_changed = False
                    if side == 'buy':
                        pnl_pct = (current_price - entry) / entry
                        if pnl_pct >= settings.TRAILING_TRIGGER:
                            target_sl = entry * (1 + settings.TRAILING_STEP)
                            if sl < target_sl: new_sl = target_sl; sl_changed = True
                    elif side == 'sell':
                        pnl_pct = (entry - current_price) / entry
                        if pnl_pct >= settings.TRAILING_TRIGGER:
                            target_sl = entry * (1 - settings.TRAILING_STEP)
                            if sl > target_sl: new_sl = target_sl; sl_changed = True
                    
                    if sl_changed and new_sl:
                        dry_run_position['sl'] = new_sl
                        active_sl_price = new_sl 
                        print(f"🛡️ TRAILING STOP ACTIVADO! SL movido a {new_sl:.2f}")
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
                        daily_pnl += realized_pnl
                        
                        emoji = "✅" if realized_pnl > 0 else "❌"
                        msg = (f"{emoji} <b>Posición CERRADA</b> ({close_signal})\n"
                               f"PnL Operación: <b>{realized_pnl:.4f} USDT</b>\n"
                               f"📉 PnL Diario: {daily_pnl:.4f} USDT\n"
                               f"Precio Cierre: {current_price}")
                        send_message(msg)
                        print(f"[SIMULATION] {msg}")
                        
                        dry_run_position = None 
                        in_position = False
                        active_sl_price = 0.0; active_tp_price = 0.0
                        tp_alert_sent = False; sl_alert_sent = False
                        print("[COOLDOWN] ❄️ Enfriando motores por 5 minutos...")
                        time.sleep(300) 

            # --- ALERTAS DE PROXIMIDAD ---
            if in_position and active_tp_price > 0 and active_sl_price > 0:
                dist_tp = abs(active_tp_price - current_price) / current_price
                dist_sl = abs(current_price - active_sl_price) / current_price
                
                if dist_tp <= settings.ALERT_PROXIMITY_PCT and not tp_alert_sent:
                    send_message(f"🚀 <b>Precio cerca del TAKE PROFIT</b>\nDistancia: {dist_tp*100:.2f}%")
                    tp_alert_sent = True
                
                if dist_sl <= settings.ALERT_PROXIMITY_PCT and not sl_alert_sent:
                    send_message(f"⚠️ <b>Precio cerca del STOP LOSS</b>\nDistancia: {dist_sl*100:.2f}%")
                    sl_alert_sent = True
            else:
                tp_alert_sent = False
                sl_alert_sent = False

            # 3. Telemetría
            status_msg = "EN POSICIÓN" if in_position else "BUSCANDO"
            print(f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] "
                  f"Strat: {strategy_name} | Price: {current_price:.2f} | {status_msg}")

            # 4. EJECUCIÓN (CON GESTIÓN DINÁMICA)
            if not in_position and signal:
                print(f"!!! SIGNAL DETECTED: {signal} via {strategy_name} !!!")
                
                # --- SELECCIÓN DINÁMICA DE TP/SL ---
                if "TREND" in strategy_name:
                    dynamic_sl = settings.TREND_SL
                    dynamic_tp = settings.TREND_TP
                    strat_type = "🌊 TENDENCIA"
                else:
                    dynamic_sl = settings.RANGE_SL
                    dynamic_tp = settings.RANGE_TP
                    strat_type = "🦀 RANGO"
                
                print(f"{strat_type}: Usando SL {dynamic_sl*100}% / TP {dynamic_tp*100}%")
                # -----------------------------------

                order_result = risk_manager.calculate_and_execute(
                    signal=signal, 
                    current_price=current_price,
                    stop_loss_pct=dynamic_sl,   # <--- USAMOS DINÁMICO
                    take_profit_pct=dynamic_tp  # <--- USAMOS DINÁMICO
                )
                
                if order_result:
                    exec_price = float(order_result.get('average', current_price))
                    quantity = float(order_result.get('amount', 0))
                    position_notional = quantity * exec_price
                    margin_used = position_notional / settings.LEVERAGE

                    # Cálculo de precios para Telegram usando los valores dinámicos
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

                    msg = (
                        f"{side_emoji} <b>ORDEN EJECUTADA</b> ({'LIVE' if settings.IS_LIVE else 'SIM'}) via {strategy_name}\n"
                        f"Par: <b>{settings.SYMBOL}</b>\n"
                        f"Tipo: <b>{signal}</b> {settings.LEVERAGE}x\n"
                        f"💵 Entrada: ${exec_price:,.2f}\n"
                        f"📉 SL: ${sl_price:,.2f} ({dynamic_sl*100}%)\n"
                        f"🎯 TP: ${tp_price:,.2f} ({dynamic_tp*100}%)\n"
                        f"💰 Margen: ${margin_used:,.2f}"
                    )
                    send_message(msg)

                    if not settings.IS_LIVE:
                        dry_run_position = {
                            'entry': exec_price, 'sl': sl_price, 'tp': tp_price,
                            'side': 'buy' if signal == 'LONG' else 'sell', 'qty': quantity
                        }

            time.sleep(60) 
            
    except KeyboardInterrupt:
        send_message("⚠️ <b>Bot detenido manualmente</b> (Ctrl+C)")
    except Exception as e:
        send_message(f"🚨 <b>ERROR CRÍTICO DEL SISTEMA:</b>\n<code>{str(e)}</code>")
        print(f"CRITICAL ERROR: {e}")
    finally:
        send_message("🛑 <b>Protocol Zero-Emotion APAGADO</b>")

if __name__ == "__main__":
    run_bot()