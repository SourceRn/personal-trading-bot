import time
import pandas as pd
from core.api_connector import BinanceConnector
from core.strategy import Strategy
from core.risk_manager import RiskManager
from core.execution import ExecutionEngine 
from utils.telegram_bot import send_message
from config.settings import settings

def fetch_data(exchange, symbol, timeframe):
    # CAMBIO CRITICO: Aumentamos limit de 100 a 300.
    # El ADX y las EMAs necesitan más historia para estabilizarse.
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
    
    # --- CONTROL DE PÉRDIDA DIARIA (CIRCUIT BREAKER) ---
    daily_pnl = 0.0
    # Calculamos cuánto es el monto máximo de pérdida en USDT
    initial_balance = risk_manager._get_available_balance()
    max_loss_usdt = initial_balance * settings.MAX_DAILY_LOSS
    
    mode_label = "🚨 LIVE TRADING 🚨" if settings.IS_LIVE else "DRY RUN (Paper Trading)"
    startup_msg = (f"🤖 Protocol Zero-Emotion Started\n"
                   f"Symbol: {settings.SYMBOL}\n"
                   f"Mode: {mode_label}\n"
                   f"Strategy: Hybrid (ADX Switcher)\n"
                   f"Daily Loss Limit: -{max_loss_usdt:.2f} USDT")
    print(startup_msg)
    send_message(startup_msg)

    while True:
        try:
            # 0. VERIFICACIÓN DE SEGURIDAD DIARIA
            if daily_pnl <= -max_loss_usdt:
                stop_msg = (f"⛔ BOT DETENIDO: Límite de pérdida diaria alcanzado.\n"
                            f"PnL Hoy: {daily_pnl:.2f} USDT\n"
                            f"Límite: -{max_loss_usdt:.2f} USDT")
                print(stop_msg)
                send_message(stop_msg)
                break # Rompe el ciclo while y apaga el bot

            # 1. Obtener datos
            df = fetch_data(exchange, settings.SYMBOL, settings.TIMEFRAME)
            
            # --- CAMBIO IMPORTANTE AQUÍ ---
            # Ahora analyze devuelve dos valores: la señal y el nombre de la estrategia usada
            signal, strategy_name = strategy.analyze(df) 
            
            current_price = df.iloc[-1]['close']
            
            # 2. GESTIÓN DE POSICIONES
            in_position = False

            if settings.IS_LIVE:
                qty = execution_engine.check_active_position(settings.SYMBOL)
                if abs(qty) > 0:
                    in_position = True
                    print(f"[GUARD] Posición LIVE detectada. Qty: {qty}. Esperando salida...")
            
            else:
                # DRY RUN LOGIC
                if dry_run_position:
                    in_position = True
                    entry = dry_run_position['entry']
                    sl = dry_run_position['sl']
                    tp = dry_run_position['tp']
                    side = dry_run_position['side']
                    qty_held = dry_run_position.get('qty', 0.0)
                    
                    close_signal = None
                    if side == 'buy':
                        if current_price <= sl: close_signal = "STOP LOSS"
                        elif current_price >= tp: close_signal = "TAKE PROFIT"     
                    elif side == 'sell':
                        if current_price >= sl: close_signal = "STOP LOSS"
                        elif current_price <= tp: close_signal = "TAKE PROFIT"
                    
                    if close_signal:
                        # CALCULO DE PnL REALISTA
                        price_diff = (current_price - entry) if side == 'buy' else (entry - current_price)
                        realized_pnl = price_diff * qty_held
                        
                        # Actualizamos el PnL Diario
                        daily_pnl += realized_pnl
                        
                        emoji = "✅" if realized_pnl > 0 else "❌"
                        msg = (f"{emoji} Posición CERRADA ({close_signal})\n"
                               f"-----------------------------\n"
                               f"PnL Operación: {realized_pnl:.4f} USDT\n"
                               f"📉 PnL Diario: {daily_pnl:.4f} USDT\n"
                               f"Precio Cierre: {current_price}")
                               
                        send_message(msg)
                        print(f"[SIMULATION] {msg}")
                        
                        dry_run_position = None 
                        in_position = False

                        # COOLDOWN
                        print("[COOLDOWN] ❄️ Enfriando motores por 5 minutos para evitar re-entrada...")
                        time.sleep(300) 

            # 3. Telemetría Mejorada
            status_msg = "EN POSICIÓN" if in_position else "BUSCANDO"
            
            # Formato de log más informativo
            print(f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] "
                  f"Mode: {'LIVE' if settings.IS_LIVE else 'DRY'} | "
                  f"Strat: {strategy_name} | "  # Muestra si es TREND o RANGE
                  f"Price: {current_price:.2f} | "
                  f"Status: {status_msg}")

            # 4. Ejecución
            if not in_position and signal:
                print(f"!!! SIGNAL DETECTED: {signal} via {strategy_name} !!!")
                
                order_result = risk_manager.calculate_and_execute(
                    signal=signal, 
                    current_price=current_price,
                    stop_loss_pct=settings.STOP_LOSS_PCT,
                    take_profit_pct=settings.TAKE_PROFIT_PCT
                )
                
                if order_result:
                    exec_price = float(order_result.get('average', current_price))
                    quantity = float(order_result.get('amount', 0))
                    
                    position_notional = quantity * exec_price
                    margin_used = position_notional / settings.LEVERAGE

                    sl_pct = settings.STOP_LOSS_PCT
                    tp_pct = settings.TAKE_PROFIT_PCT

                    if signal == 'LONG':
                        sl_price = exec_price * (1 - sl_pct)
                        tp_price = exec_price * (1 + tp_pct)
                        side_emoji = "🟢"
                    else:
                        sl_price = exec_price * (1 + sl_pct)
                        tp_price = exec_price * (1 - tp_pct)
                        side_emoji = "🔴"

                    msg = (
                        f"{side_emoji} ORDEN EJECUTADA ({'LIVE' if settings.IS_LIVE else 'SIM'}) via {strategy_name}\n"
                        f"-----------------------------\n"
                        f"Par: {settings.SYMBOL}\n"
                        f"Tipo: {signal} {settings.LEVERAGE}x\n"
                        f"💵 Entrada: ${exec_price:,.2f}\n"
                        f"📉 SL: ${sl_price:,.2f}\n"
                        f"🎯 TP: ${tp_price:,.2f}\n"
                        f"-----------------------------\n"
                        f"⚖️ Tamaño: ${position_notional:,.2f}\n"
                        f"💰 Margen: ${margin_used:,.2f}"
                    )
                    send_message(msg)

                    if not settings.IS_LIVE:
                        dry_run_position = {
                            'entry': exec_price,
                            'sl': sl_price,
                            'tp': tp_price,
                            'side': 'buy' if signal == 'LONG' else 'sell',
                            'qty': quantity
                        }

            time.sleep(60) 
            
        except Exception as e:
            print(f"CRITICAL LOOP ERROR: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()