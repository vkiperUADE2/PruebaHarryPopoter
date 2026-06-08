# ============================================================
# db/mongo_client.py — Conexión a MongoDB Atlas
#
# MongoDB es la base de datos de documentos del sistema.
# Almacena todo el universo Harry Potter: personajes, casas,
# hechizos, eventos, películas/libros y objetos mágicos.
# Se eligió MongoDB por su esquema flexible y su capacidad
# de embeber subdocumentos (ej: la casa dentro del personaje),
# lo que optimiza las lecturas al evitar JOINs.
# ============================================================

from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.database import Database
from config import MONGODB_DB_NAME, MONGODB_URI

# URI de conexión a MongoDB Atlas (incluye usuario, contraseña y cluster)

# Nombre de la base de datos dentro del cluster

# Variable global para reutilizar la misma conexión (patrón Singleton)
_client: MongoClient | None = None
_indexes_ready = False

def get_mongo() -> Database:
    """Devuelve la base de datos harry_potter. Crea el cliente solo la primera vez."""
    global _client, _indexes_ready
    if _client is None:
        # ServerApi("1") usa la versión estable de la API de MongoDB Atlas
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
