"""Repara referencias inversas existentes sin borrar datos."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bson import ObjectId

from db.mongo_client import get_mongo


def repair_relations():
    db = get_mongo()
    db.eventos.update_many({"peliculas_libros": {"$exists": False}}, {"$set": {"peliculas_libros": []}})
    db.peliculas_libros.update_many({"personajes": {"$exists": False}}, {"$set": {"personajes": []}})
    db.peliculas_libros.update_many({"eventos": {"$exists": False}}, {"$set": {"eventos": []}})

    for personaje in db.personajes.find():
        for evento in personaje.get("eventos", []):
            if ObjectId.is_valid(evento.get("evento_id", "")):
                db.eventos.update_one(
                    {"_id": ObjectId(evento["evento_id"])},
                    {"$addToSet": {"participantes": {
                        "personaje_id": str(personaje["_id"]),
                        "nombre": personaje["nombre"],
                        "rol_en_evento": evento.get("rol_en_evento", "Participante"),
                    }}},
                )
        for obra in personaje.get("peliculas_libros", []):
            if ObjectId.is_valid(obra.get("id", "")):
                pelicula = db.peliculas_libros.find_one({"_id": ObjectId(obra["id"])})
                if pelicula:
                    db.personajes.update_one(
                        {"_id": personaje["_id"], "peliculas_libros.id": obra["id"]},
                        {"$set": {"peliculas_libros.$.titulo": pelicula["titulo"]}},
                    )
                    db.peliculas_libros.update_one(
                        {"_id": pelicula["_id"]},
                        {"$addToSet": {"personajes": {"id": str(personaje["_id"]), "nombre": personaje["nombre"]}}},
                    )

    torneo = db.eventos.find_one({"nombre": "Torneo de los Tres Magos"})
    if torneo:
        for pelicula in db.peliculas_libros.find({"titulo": "Harry Potter y el Cáliz de Fuego"}):
            db.peliculas_libros.update_one(
                {"_id": pelicula["_id"]},
                {"$addToSet": {"eventos": {"id": str(torneo["_id"]), "nombre": torneo["nombre"]}}},
            )
            db.eventos.update_one(
                {"_id": torneo["_id"]},
                {"$addToSet": {"peliculas_libros": {
                    "id": str(pelicula["_id"]), "titulo": pelicula["titulo"], "tipo": pelicula["tipo"],
                }}},
            )

    print("Relaciones inversas reparadas.")


if __name__ == "__main__":
    repair_relations()
