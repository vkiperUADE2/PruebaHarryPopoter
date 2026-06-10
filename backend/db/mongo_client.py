from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.database import Database
from config import MONGODB_DB_NAME, MONGODB_URI

_client: MongoClient | None = None
_indexes_ready = False

def get_mongo() -> Database:
    global _client, _indexes_ready
    if _client is None:
        _client = MongoClient(MONGODB_URI, server_api=ServerApi("1"))
    db = _client[MONGODB_DB_NAME]
    if not _indexes_ready:
        db.personajes.create_index("nombre")
        db.personajes.create_index([("rol", "text"), ("alineacion", "text"), ("casa.nombre", "text")])
        db.casas.create_index("nombre")
        db.casas.create_index("fundador")
        db.hechizos.create_index("nombre")
        db.eventos.create_index("nombre")
        db.peliculas_libros.create_index("titulo")
        db.objetos_magicos.create_index("nombre")
        _indexes_ready = True
    return db
