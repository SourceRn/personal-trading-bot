import telebot
from telebot import types
from datetime import datetime
import time
from config.settings import settings
from core.shared_state import bot_state

# Inicializamos el bot a nivel global para que los decoradores (@bot) funcionen bien
if settings.TELEGRAM_TOKEN:
    bot = telebot.TeleBot(settings.TELEGRAM_TOKEN)
else:
    bot = None
    print("⚠️ ADVERTENCIA: No se encontró TELEGRAM_TOKEN en settings.")

def start_telegram_listener():
    """
    Función principal que inicia la escucha de mensajes.
    Se ejecuta en su propio hilo desde main.py.
    """
    if not bot:
        return

    print("👂 Telegram Command Listener Iniciado...")

    # --- 1. CONFIGURACIÓN DEL MENÚ DE COMANDOS (UX) ---
    # Esto crea el botón "Menú" azul en Telegram con las opciones
    try:
        print("⚙️ Configurando menú de comandos en Telegram...")
        bot.set_my_commands([
            types.BotCommand("posicion", "🟢 Ver operación activa (PnL)"),
            types.BotCommand("scan", "🔍 Escanear mercado (RSI/ADX)"),
            types.BotCommand("balance", "💰 Ver saldo y PnL diario"),
            types.BotCommand("status", "📊 Estado del sistema"),
            types.BotCommand("stop", "🛑 Apagado de emergencia")
        ])
    except Exception as e:
        print(f"⚠️ No se pudo configurar el menú visual: {e}")

    # --- 2. DEFINICIÓN DE COMANDOS ---

    # COMANDO: /status
    @bot.message_handler(commands=['status', 'bot'])
    def cmd_status(message):
        # Calculamos uptime si existe la variable, si no, mostramos "N/A"
        try:
            uptime_val = str(datetime.now() - bot_state.uptime).split('.')[0]
        except:
            uptime_val = "Calculando..."

        msg = (
            f"🤖 <b>SYSTEM STATUS</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"⏱️ Uptime: <code>{uptime_val}</code>\n"
            f"⚙️ Modo: <b>{bot_state.mode}</b>\n"
            f"🧠 Estrategia: <b>{bot_state.strategy_name}</b>\n"
            f"💲 Precio: <code>{bot_state.last_price}</code>"
        )
        bot.reply_to(message, msg, parse_mode="HTML")

    # COMANDO: /balance
    @bot.message_handler(commands=['balance', 'wallet'])
    def cmd_balance(message):
        msg = (
            f"💰 <b>BILLETERA (Futuros)</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💵 Total: <b>${bot_state.balance_total:.2f} USDT</b>\n"
            f"📉 PnL Diario: <b>{bot_state.daily_pnl:.2f} USDT</b>"
        )
        bot.reply_to(message, msg, parse_mode="HTML")

    # COMANDO: /posicion
    @bot.message_handler(commands=['posicion', 'pos'])
    def cmd_pos(message):
        if not bot_state.in_position:
            bot.reply_to(message, "😴 <b>Sin posiciones abiertas.</b>\nEl bot está buscando oportunidades...", parse_mode="HTML")
            return

        emoji = "🟢" if bot_state.pos_type == "LONG" else "🔴"
        pnl_raw = bot_state.current_pnl_pct * 100
        
        msg = (
            f"{emoji} <b>POSICIÓN ACTIVA</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"Tipo: <b>{bot_state.pos_type}</b> ({settings.SYMBOL})\n"
            f"Entrada: <code>${bot_state.entry_price:,.4f}</code>\n"
            f"Actual: <code>${bot_state.last_price:,.4f}</code>\n"
            f"PnL: <b>{pnl_raw:.2f}%</b>"
        )
        bot.reply_to(message, msg, parse_mode="HTML")

    # COMANDO: /scan
    @bot.message_handler(commands=['analizar', 'scan'])
    def cmd_scan(message):
        # Interpretación visual rápida
        rsi = bot_state.rsi
        adx = bot_state.adx
        
        rsi_status = "Sobreventa" if rsi < 35 else "Sobrecompra" if rsi > 65 else "Neutral"
        adx_status = "Tendencia Fuerte" if adx > 25 else "Rango / Débil"
        
        msg = (
            f"🔍 <b>RAYOS-X MERCADO ({settings.TIMEFRAME})</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📊 <b>Indicadores:</b>\n"
            f"• RSI: <code>{rsi:.1f}</code> ({rsi_status})\n"
            f"• ADX: <code>{adx:.1f}</code> ({adx_status})\n"
            f"• Precio: <code>{bot_state.last_price}</code>\n\n"
            f"<i>Estrategia: {bot_state.strategy_name}</i>"
        )
        bot.reply_to(message, msg, parse_mode="HTML")

    # COMANDO: /stop
    @bot.message_handler(commands=['stop'])
    def cmd_stop(message):
        bot.reply_to(message, "🛑 <b>Recibido. Iniciando secuencia de apagado...</b>", parse_mode="HTML")
        bot_state.running = False # Esto rompe el bucle en main.py

    # COMANDO: /mode (Menú Interactivo)
    @bot.message_handler(commands=['mode', 'modo'])
    def cmd_mode(message):
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # Definimos los botones
        btn_auto = types.InlineKeyboardButton("🧠 AUTO (ADX Inteligente)", callback_data="set_mode_auto")
        btn_trend = types.InlineKeyboardButton("🌊 FORZAR TENDENCIA (EMA)", callback_data="set_mode_trend")
        btn_range = types.InlineKeyboardButton("🎯 FORZAR RANGO (RSI)", callback_data="set_mode_range")
        
        markup.add(btn_auto, btn_trend, btn_range)
        
        current_mode = bot_state.strategy_mode
        msg = (f"⚙️ <b>PANEL DE CONTROL DE ESTRATEGIA</b>\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"Modo Actual: <b>{current_mode}</b>\n\n"
               f"Selecciona el nuevo comportamiento:")
               
        bot.reply_to(message, msg, reply_markup=markup, parse_mode="HTML")

    # MANEJADOR DE CLICS EN BOTONES (Callbacks)
    @bot.callback_query_handler(func=lambda call: call.data.startswith('set_mode_'))
    def callback_mode_handler(call):
        new_mode = "AUTO"
        text_mode = "🧠 AUTO"
        
        if call.data == "set_mode_trend":
            new_mode = "FORCE_TREND"
            text_mode = "🌊 FORCE TREND"
        elif call.data == "set_mode_range":
            new_mode = "FORCE_RANGE"
            text_mode = "🎯 FORCE RANGE"
        
        # 1. Actualizamos la memoria del bot INSTANTÁNEAMENTE
        bot_state.strategy_mode = new_mode
        
        # 2. Feedback al usuario (Popup pequeño)
        bot.answer_callback_query(call.id, f"Modo actualizado a: {new_mode}")
        
        # 3. Editamos el mensaje original para confirmar el cambio
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ <b>ESTRATEGIA ACTUALIZADA</b>\n\nNuevo Modo: <b>{new_mode}</b>\n<i>El cambio se aplicará en la siguiente vela.</i>",
                parse_mode="HTML"
            )
        except:
            pass
    
    # COMANDO: /config (Ver configuración actual)
    @bot.message_handler(commands=['config', 'conf', 'settings'])
    def cmd_config(message):
        # 1. Determinamos el modo activo real desde la memoria
        active_mode = bot_state.strategy_mode
        
        msg = (
            f"⚙️ <b>CONFIGURACIÓN ACTUAL</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>🧠 MODO DE ESTRATEGIA</b>\n"
            f"• Base: <code>{settings.STRATEGY_MODE}</code>\n"
            f"• Activo: <b>{active_mode}</b>\n\n"
            
            f"<b>🎮 GENERAL</b>\n"
            f"• Par: <code>{settings.SYMBOL}</code>\n"
            f"• Timeframe: <code>{settings.TIMEFRAME}</code>\n"
            f"• Apalancamiento: <code>{settings.LEVERAGE}x</code>\n\n"

            f"<b>🛡️ RIESGO</b>\n"
            f"• Riesgo/Trade: <code>{settings.RISK_PER_TRADE*100}%</code>\n"
            f"• Max Pérdida Día: <code>{settings.MAX_DAILY_LOSS*100}%</code>\n"
            f"• Piso Mínimo: <code>${getattr(settings, 'MIN_DAILY_LOSS_USD', 1.0)}</code>\n\n"

            f"<b>🌊 TENDENCIA (Trend)</b>\n"
            f"• TP: <code>{settings.TREND_TP*100}%</code> | SL: <code>{settings.TREND_SL*100}%</code>\n"
            f"• Trailing Trigger: <code>{settings.TREND_TRAILING_TRIGGER*100}%</code>\n"
            f"• Trailing Step: <code>{settings.TREND_TRAILING_STEP*100}%</code>\n\n"

            f"<b>🎯 RANGO (Range)</b>\n"
            f"• TP: <code>{settings.RANGE_TP*100}%</code> | SL: <code>{settings.RANGE_SL*100}%</code>\n"
            f"• Trailing Trigger: <code>{settings.RANGE_TRAILING_TRIGGER*100}%</code>\n"
            f"• Trailing Step: <code>{settings.RANGE_TRAILING_STEP*100}%</code>\n\n"
            
            f"<b>📊 INDICADORES</b>\n"
            f"• ADX Umbral: <code>{settings.ADX_THRESHOLD}</code>\n"
            f"• EMAs: <code>{settings.EMA_FAST}/{settings.EMA_SLOW}</code>\n"
            f"• RSI Límites: <code>{settings.RSI_LONG_THRESHOLD}/{settings.RSI_SHORT_THRESHOLD}</code>"
        )
        
        bot.reply_to(message, msg, parse_mode="HTML")

    # --- 3. BUCLE INFINITO (Polling) ---
    print("👂 Iniciando Polling de Telegram...")
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except Exception as e:
        print(f"⚠️ Error fatal en Telegram Listener: {e}")
        time.sleep(5)