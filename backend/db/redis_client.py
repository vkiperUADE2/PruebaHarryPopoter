# ============================================================
# db/redis_client.py — Conexión a Redis
#
# Redis es la base de datos EN MEMORIA del sistema.
# Se usa para dos propósitos:
#   1. Sesiones de usuario: almacena datos del usuario logueado
#      bajo la clave "session:{token}" con expiración automática (TTL).
#   2. Rankings en tiempo real: usa Sorted Sets (ZSET) para mantener
#      un conteo ordenado de las consultas más realizadas.
# ============================================================

import redis
from config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_USERNAME

# Variable global para reutilizar la misma conexión (patrón Singleton)
_client: redis.Redis | None = None

def get_redis() -> redis.Redis:
    """Devuelve el cliente de Redis. Lo crea solo la primera vez (lazy init)."""
    global _client
    if _client is None:
        _client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
            decode_responses=True,  # devuelve strings en vez de bytes
        )
    return _client
