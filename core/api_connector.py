import ccxt
from config.settings import settings

class BinanceConnector:
    def __init__(self):
        self.exchange = self._connect()

    def _connect(self):
        # Configuración estándar para Binance Futures (Live)
        config = {
            'apiKey': settings.API_KEY,
            'secret': settings.SECRET_KEY,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Vital para operar en derivados
                'adjustForTimeDifference': True,
                # Optimizaciones para inicio rápido
                'fetchCurrencies': False,
                'fetchMarkets': ['linear'], # Filtra solo contratos USDT-Margined
            }
        }

        print(f"[API] 🔌 Estableciendo conexión con Binance Futures...")

        # Instanciamos CCXT (Por defecto conecta a URLs de producción)
        exchange = ccxt.binance(config)
        
        # Validamos la conexión cargando los mercados
        # Esto lanzará un error inmediato si las claves están mal o no hay internet
        try:
            exchange.load_markets()
            print("[API] ✅ Conexión exitosa (Datos Reales).")
        except Exception as e:
            print(f"[API] ❌ Error crítico de conexión: {e}")
            raise e

        return exchange

    def get_exchange(self):
        return self.exchange