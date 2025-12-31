import requests
from config.settings import settings

def send_message(message):
    if not settings.TELEGRAM_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"  # <--- CAMBIO IMPORTANTE
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code != 200:
            print(f"❌ ERROR TELEGRAM: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ ERROR CONEXIÓN TELEGRAM: {e}")