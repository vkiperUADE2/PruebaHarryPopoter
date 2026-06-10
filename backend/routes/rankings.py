from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from db.redis_client import get_redis
from db.mongo_client import get_mongo
from security import require_session
from bson import ObjectId

router = APIRouter()


def _format_items(r, items):
    result = []
    for contenido_id, score in items:
        raw = r.hget("contenido:catalogo", contenido_id) or _resolve_content(contenido_id)
        tipo, nombre = raw.split("|", 1)
        result.append({
            "contenido_id": contenido_id,
            "contenido_nombre": nombre or contenido_id,
            "contenido_tipo": tipo or "contenido",
            "visitas": int(score),
        })
    return result


def _resolve_content(contenido_id: str) -> str:
    if not ObjectId.is_valid(contenido_id):
        return "|"
    db = get_mongo()
    for tipo, collection, label in [
        ("personajes", "personajes", "nombre"), ("casas", "casas", "nombre"),
        ("hechizos", "hechizos", "nombre"), ("eventos", "eventos", "nombre"),
        ("peliculas", "peliculas_libros", "titulo"), ("objetos", "objetos_magicos", "nombre"),
    ]:
        doc = db[collection].find_one({"_id": ObjectId(contenido_id)}, {label: 1})
        if doc:
            return f"{tipo}|{doc.get(label, '')}"
    return "|"


@router.get("/global")
def ranking_global(fecha: str = None, top: int = 10):
    if not fecha:
        fecha = date.today().isoformat()
    try:
        r = get_redis()
        items = r.zrevrange(f"ranking:global:{fecha}", 0, top - 1, withscores=True)
        return _format_items(r, items)
    except Exception as e:
        raise HTTPException(503, f"Redis no disponible: {e}")


@router.get("/usuario/{user_id}")
def ranking_usuario(user_id: int, top: int = 10, session: dict = Depends(require_session)):
    if int(session["user_id"]) != user_id and str(session["rol"]) != "2":
        raise HTTPException(403, "No puede consultar el ranking de otro usuario")
    try:
        r = get_redis()
        items = r.zrevrange(f"ranking:usuario:{user_id}", 0, top - 1, withscores=True)
        return _format_items(r, items)
    except Exception as e:
        raise HTTPException(503, f"Redis no disponible: {e}")
