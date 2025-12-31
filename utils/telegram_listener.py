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

    # --- 3. BUCLE INFINITO (Polling) ---
    print("👂 Iniciando Polling de Telegram...")
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except Exception as e:
        print(f"⚠️ Error fatal en Telegram Listener: {e}")
        time.sleep(5)