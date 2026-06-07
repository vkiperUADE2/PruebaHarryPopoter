# ============================================================
# db/cassandra_client.py — Conexión a Cassandra (Astra DB)
#
# Cassandra (vía DataStax Astra DB) es la base de datos de
# AUDITORÍA del sistema. Registra todas las acciones de los
# usuarios (qué consultaron, cuándo y qué buscaron).
# Se eligió por su alta capacidad de escritura concurrente,
# ideal para logs inmutables que se acumulan continuamente.
#
# Se conecta usando la librería astrapy con la Data API de Astra,
# que expone Cassandra como una API de documentos (similar a MongoDB).
# ============================================================

from astrapy import DataAPIClient
from astrapy.database import Database
from config import ASTRA_DB_URL, ASTRA_TOKEN

# URL del endpoint de la base de datos en Astra DB

# Token de autenticación generado en el panel de Astra DB

# Nombres de las colecciones que se usan en la auditoría:
# - actividad_por_usuario: registra qué contenido vio cada usuario
# - busquedas_por_usuario: registra qué términos buscó cada usuario
COLLECTIONS = ["actividad_por_usuario", "busquedas_por_usuario"]

# Variable global para reutilizar la misma conexión (patrón Singleton)
_db: Database | None = None

def get_cassandra() -> Database:
    """
    Devuelve la base de datos de Astra DB.
    La primera vez que se llama, se conecta y crea las colecciones
    si todavía no existen (inicialización automática del esquema).
    """
    global _db
    if _db is None:
        # Inicializamos el cliente de la Data API de Astra
        client = DataAPIClient()
        db = client.get_database(ASTRA_DB_URL, token=ASTRA_TOKEN)

        # Consultamos qué colecciones ya existen
        existing = db.list_collection_names()

        # Creamos las colecciones que faltan (idempotente: no falla si ya existen)
        for col in COLLECTIONS:
            if col not in existing:
                db.create_collection(col)

        _db = db
    return _db
