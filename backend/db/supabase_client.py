# ============================================================
# db/supabase_client.py — Conexión a Supabase (PostgreSQL)
#
# Supabase es la base de datos RELACIONAL del sistema.
# Almacena usuarios y roles con consistencia ACID:
# garantiza que no se dupliquen emails ni se rompan
# las relaciones entre tablas (integridad referencial).
# ============================================================

from supabase import create_client, Client
from config import SUPABASE_KEY, SUPABASE_URL

# URL pública del proyecto en Supabase

# Clave anon/pública: permite operaciones de lectura y escritura
# sobre las tablas que tienen RLS desactivado (roles y usuarios)

# Variable global para reutilizar la misma conexión (patrón Singleton)
_client: Client | None = None

def get_supabase() -> Client:
    """Devuelve el cliente de Supabase. Lo crea solo la primera vez (lazy init)."""
    global _client
    if _client is None:
        # create_client inicializa la conexión HTTP con la URL y la clave
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
