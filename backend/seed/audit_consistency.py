"""Audita referencias bidireccionales de MongoDB sin modificar datos."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bson import ObjectId

from db.mongo_client import get_mongo


def audit_consistency() -> list[str]:
    db = get_mongo()
    errors: list[str] = []

    for character in db.personajes.find():
        character_id = str(character["_id"])
        house = character.get("casa", {})
        if not ObjectId.is_valid(house.get("id", "")) or not db.casas.find_one(
            {"_id": ObjectId(house["id"]), "nombre": house.get("nombre")}
        ):
            errors.append(f"Personaje {character_id}: casa inexistente o desactualizada")

        for spell in character.get("hechizos", []):
            if not ObjectId.is_valid(spell.get("hechizo_id", "")) or not db.hechizos.find_one(
                {"_id": ObjectId(spell["hechizo_id"]), "nombre": spell.get("nombre")}
            ):
                errors.append(f"Personaje {character_id}: hechizo inexistente o desactualizado")

        for event in character.get("eventos", []):
            reverse = db.eventos.find_one({
                "_id": ObjectId(event["evento_id"]),
                "participantes": {"$elemMatch": {"personaje_id": character_id}},
            }) if ObjectId.is_valid(event.get("evento_id", "")) else None
            if not reverse:
                errors.append(f"Personaje {character_id}: evento sin referencia inversa")

        for work in character.get("peliculas_libros", []):
            reverse = db.peliculas_libros.find_one({
                "_id": ObjectId(work["id"]),
                "personajes": {"$elemMatch": {"id": character_id}},
            }) if ObjectId.is_valid(work.get("id", "")) else None
            if not reverse:
                errors.append(f"Personaje {character_id}: obra sin referencia inversa")

    for work in db.peliculas_libros.find():
        work_id = str(work["_id"])
        for event in work.get("eventos", []):
            reverse = db.eventos.find_one({
                "_id": ObjectId(event["id"]),
                "peliculas_libros": {"$elemMatch": {"id": work_id}},
            }) if ObjectId.is_valid(event.get("id", "")) else None
            if not reverse:
                errors.append(f"Obra {work_id}: evento sin referencia inversa")

    return errors


if __name__ == "__main__":
    issues = audit_consistency()
    if issues:
        print(f"Se encontraron {len(issues)} inconsistencias:")
        for issue in issues:
            print(f"- {issue}")
        raise SystemExit(1)
    print("Consistencia MongoDB verificada: no se encontraron referencias rotas.")
