from astrapy import DataAPIClient
from astrapy.database import Database
from config import ASTRA_DB_URL, ASTRA_TOKEN

COLLECTIONS = ["actividad_por_usuario", "busquedas_por_usuario"]

_db: Database | None = None

def get_cassandra() -> Database:
    global _db
    if _db is None:
        client = DataAPIClient()
        db = client.get_database(ASTRA_DB_URL, token=ASTRA_TOKEN)
        existing = db.list_collection_names()
        for col in COLLECTIONS:
            if col not in existing:
                db.create_collection(col)
        _db = db
    return _db
