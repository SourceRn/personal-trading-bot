import telebot
import threading
import time
from config.settings import settings
from core.shared_state import bot_state

def start_telegram_listener():
    if not settings.TELEGRAM_TOKEN:
        print("⚠️ No Telegram Token found for Listener")
        return

    bot = telebot.TeleBot(settings.TELEGRAM_TOKEN)
    print("👂 Telegram Command Listener Iniciado...")

    # --- COMANDO /STATUS ---
    @bot.message_handler(commands=['status', 'bot'])
    def cmd_status(message):
        uptime_str = str(datetime.now() - bot_state.uptime).split('.')[0]
        msg = (
            f"🤖 <b>SYSTEM STATUS</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"⏱️ Uptime: <code>{uptime_str}</code>\n"
            f"⚙️ Modo: <b>{bot_state.mode}</b>\n"
            f"🧠 Estrategia: <b>{bot_state.strategy_name}</b>\n"
            f"💲 Precio: <code>{bot_state.last_price}</code>"
        )
        bot.reply_to(message, msg, parse_mode="HTML")

    # --- COMANDO /BALANCE (Wallet) ---
    @bot.message_handler(commands=['balance', 'wallet'])
    def cmd_balance(message):
        msg = (
            f"💰 <b>BILLETERA (Futuros)</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💵 Total: <b>${bot_state.balance_total:.2f} USDT</b>\n"
            f"📉 PnL Diario: <b>{bot_state.daily_pnl:.2f} USDT</b>"
        )
        bot.reply_to(message, msg, parse_mode="HTML")

    # --- COMANDO /POSICION ---
    @bot.message_handler(commands=['posicion', 'pos'])
    def cmd_pos(message):
        if not bot_state.in_position:
            bot.reply_to(message, "😴 <b>Sin posiciones abiertas.</b>", parse_mode="HTML")
            return

        emoji = "🟢" if bot_state.pos_type == "LONG" else "🔴"
        pnl_emoji = "profit" if bot_state.current_pnl_pct >= 0 else "loss"
        
        msg = (
            f"{emoji} <b>POSICIÓN ACTIVA</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"Tipo: <b>{bot_state.pos_type}</b>\n"
            f"Entrada: <code>{bot_state.entry_price}</code>\n"
            f"Actual: <code>{bot_state.last_price}</code>\n"
            f"PnL: <b>{bot_state.current_pnl_pct*100:.2f}%</b>"
        )
        bot.reply_to(message, msg, parse_mode="HTML")

    # --- COMANDO /ANALIZAR (Scan) ---
    @bot.message_handler(commands=['analizar', 'scan'])
    def cmd_scan(message):
        # Interpretación rápida para dar feedback visual
        rsi_status = "Sobreventa" if bot_state.rsi < 35 else "Sobrecompra" if bot_state.rsi > 65 else "Neutral"
        adx_status = "Tendencia" if bot_state.adx > 30 else "Rango"
        
        msg = (
            f"🔍 <b>RAYOS-X MERCADO</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📊 <b>Indicadores Técnicos:</b>\n"
            f"• RSI (14): <code>{bot_state.rsi:.1f}</code> ({rsi_status})\n"
            f"• ADX (14): <code>{bot_state.adx:.1f}</code> ({adx_status})\n"
            f"• Precio: <code>{bot_state.last_price}</code>\n\n"
            f"<i>Decisión del Bot: {bot_state.strategy_name}</i>"
        )
        bot.reply_to(message, msg, parse_mode="HTML")

    # --- COMANDO /STOP (Apagado de Emergencia) ---
    @bot.message_handler(commands=['stop'])
    def cmd_stop(message):
        bot.reply_to(message, "🛑 <b>Recibido. Iniciando secuencia de apagado...</b>", parse_mode="HTML")
        bot_state.running = False # Esto romperá el bucle en main.py

    # Iniciar polling en bucle infinito (robusto ante caídas de red)
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Error en Telegram Listener: {e}")