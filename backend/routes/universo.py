import logging
import re
import uuid
from datetime import date, datetime

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from db.cassandra_client import get_cassandra
from db.mongo_client import get_mongo
from db.redis_client import get_redis
from models import (
    AsociacionEventoIn, AsociacionPeliculaIn, CasaIn, EventoIn, HechizoIn,
    ObjetoIn, PeliculaIn, PersonajeIn,
)
from security import ensure_admin, optional_session, require_session


router = APIRouter()
log = logging.getLogger(__name__)

COLLECTIONS = {
    "personajes": ("personajes", "nombre", PersonajeIn),
    "casas": ("casas", "nombre", CasaIn),
    "hechizos": ("hechizos", "nombre", HechizoIn),
    "eventos": ("eventos", "nombre", EventoIn),
    "peliculas": ("peliculas_libros", "titulo", PeliculaIn),
    "objetos": ("objetos_magicos", "nombre", ObjetoIn),
}


def _admin(session: dict = Depends(require_session)) -> dict:
    return ensure_admin(session)


def _oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(400, "ID invalido")
    return ObjectId(value)


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


def _page(skip: int, limit: int) -> tuple[int, int]:
    return max(skip, 0), min(max(limit, 1), 100)


def _log_activity(user_id: int, contenido_id: str, nombre: str, tipo: str):
    try:
        get_cassandra().get_collection("actividad_por_usuario").insert_one({
            "user_id": user_id,
            "actividad_id": str(uuid.uuid1()),
            "tipo_actividad": "VIEW",
            "contenido_id": contenido_id,
            "contenido_tipo": tipo,
            "contenido_nombre": nombre,
            "created_at": datetime.utcnow().isoformat(),
            "fecha": date.today().isoformat(),
        })
    except Exception:
        log.exception("No se pudo registrar actividad")


def _log_busqueda(user_id: int, texto: str, cantidad: int):
    try:
        get_cassandra().get_collection("busquedas_por_usuario").insert_one({
            "user_id": user_id,
            "busqueda_id": str(uuid.uuid1()),
            "texto_busqueda": texto,
            "cantidad_resultados": cantidad,
            "created_at": datetime.utcnow().isoformat(),
        })
    except Exception:
        log.exception("No se pudo registrar busqueda")


def _update_ranking(user_id: int | None, contenido_id: str):
    try:
        r = get_redis()
        hoy = date.today().isoformat()
        with r.pipeline(transaction=True) as pipe:
            pipe.zincrby(f"ranking:global:{hoy}", 1, contenido_id)
            pipe.expire(f"ranking:global:{hoy}", 86400)
            if user_id:
                pipe.zincrby(f"ranking:usuario:{user_id}", 1, contenido_id)
            pipe.execute()
    except Exception:
        log.exception("No se pudo actualizar ranking")


def _session_id(session: dict | None) -> int | None:
    return int(session["user_id"]) if session else None


def _list(tipo: str, skip: int, limit: int):
    col, _, _ = COLLECTIONS[tipo]
    skip, limit = _page(skip, limit)
    return [_serialize(d) for d in get_mongo()[col].find().skip(skip).limit(limit)]


def _detail(tipo: str, item_id: str, bg: BackgroundTasks, session: dict | None):
    col, label, _ = COLLECTIONS[tipo]
    doc = get_mongo()[col].find_one({"_id": _oid(item_id)})
    if not doc:
        raise HTTPException(404, "Contenido no encontrado")
    uid = _session_id(session)
    bg.add_task(_update_ranking, uid, item_id)
    if uid:
        bg.add_task(_log_activity, uid, item_id, doc.get(label, ""), tipo)
    return _serialize(doc)


def _create(tipo: str, body: BaseModel):
    col, _, _ = COLLECTIONS[tipo]
    result = get_mongo()[col].insert_one(body.model_dump())
    return {"_id": str(result.inserted_id)}


def _update(tipo: str, item_id: str, body: BaseModel):
    col, _, _ = COLLECTIONS[tipo]
    db = get_mongo()
    result = get_mongo()[col].find_one_and_update(
        {"_id": _oid(item_id)}, {"$set": body.model_dump()}, return_document=True
    )
    if not result:
        raise HTTPException(404, "Contenido no encontrado")
    if tipo == "casas":
        db.personajes.update_many({"casa.id": item_id}, {"$set": {"casa.nombre": result["nombre"]}})
    elif tipo == "hechizos":
        db.personajes.update_many(
            {"hechizos.hechizo_id": item_id}, {"$set": {"hechizos.$[ref].nombre": result["nombre"]}},
            array_filters=[{"ref.hechizo_id": item_id}],
        )
    elif tipo == "eventos":
        db.personajes.update_many(
            {"eventos.evento_id": item_id}, {"$set": {"eventos.$[ref].nombre": result["nombre"]}},
            array_filters=[{"ref.evento_id": item_id}],
        )
    elif tipo == "peliculas":
        db.personajes.update_many(
            {"peliculas_libros.id": item_id}, {"$set": {"peliculas_libros.$[ref].titulo": result["titulo"]}},
            array_filters=[{"ref.id": item_id}],
        )
    elif tipo == "personajes":
        db.eventos.update_many(
            {"participantes.personaje_id": item_id}, {"$set": {"participantes.$[ref].nombre": result["nombre"]}},
            array_filters=[{"ref.personaje_id": item_id}],
        )
        db.peliculas_libros.update_many(
            {"personajes.id": item_id}, {"$set": {"personajes.$[ref].nombre": result["nombre"]}},
            array_filters=[{"ref.id": item_id}],
        )
    return _serialize(result)


def _delete(tipo: str, item_id: str):
    col, _, _ = COLLECTIONS[tipo]
    db = get_mongo()
    if tipo == "casas" and db.personajes.find_one({"casa.id": item_id}):
        raise HTTPException(409, "No se puede eliminar una casa asociada a personajes")
    if tipo == "hechizos" and db.personajes.find_one({"hechizos.hechizo_id": item_id}):
        raise HTTPException(409, "No se puede eliminar un hechizo asociado a personajes")
    if db[col].delete_one({"_id": _oid(item_id)}).deleted_count != 1:
        raise HTTPException(404, "Contenido no encontrado")
    if tipo == "eventos":
        db.personajes.update_many({}, {"$pull": {"eventos": {"evento_id": item_id}}})
    elif tipo == "peliculas":
        db.personajes.update_many({}, {"$pull": {"peliculas_libros": {"id": item_id}}})
    elif tipo == "personajes":
        db.eventos.update_many({}, {"$pull": {"participantes": {"personaje_id": item_id}}})
        db.peliculas_libros.update_many({}, {"$pull": {"personajes": {"id": item_id}}})
    return {"ok": True}


def _search(tipo: str, q: str, skip: int, limit: int):
    col, label, _ = COLLECTIONS[tipo]
    fields = [label]
    if tipo == "hechizos":
        fields += ["descripcion", "efecto"]
    elif tipo in ("eventos", "peliculas", "objetos"):
        fields += ["descripcion"]
    safe_q = re.escape(q)
    query = {"$or": [{f: {"$regex": safe_q, "$options": "i"}} for f in fields]}
    skip, limit = _page(skip, limit)
    return [_serialize(d) for d in get_mongo()[col].find(query).skip(skip).limit(limit)]


@router.get("/buscar")
def buscar_global(
    q: str = Query(min_length=1),
    skip: int = 0,
    limit: int = 20,
    bg: BackgroundTasks = None,
    session: dict | None = Depends(optional_session),
):
    results = []
    for tipo in COLLECTIONS:
        results.extend({"tipo": tipo, "contenido": d} for d in _search(tipo, q, skip, limit))
    if session and bg:
        bg.add_task(_log_busqueda, _session_id(session), q, len(results))
    return results


@router.post("/asociaciones/eventos")
def asociar_evento(body: AsociacionEventoIn, _: dict = Depends(_admin)):
    db = get_mongo()
    personaje = db.personajes.find_one({"_id": _oid(body.personaje_id)})
    evento = db.eventos.find_one({"_id": _oid(body.evento_id)})
    if not personaje or not evento:
        raise HTTPException(404, "Personaje o evento no encontrado")
    db.personajes.update_one({"_id": personaje["_id"]}, {"$addToSet": {"eventos": {
        "evento_id": body.evento_id, "nombre": evento["nombre"], "rol_en_evento": body.rol_en_evento
    }}})
    db.eventos.update_one({"_id": evento["_id"]}, {"$addToSet": {"participantes": {
        "personaje_id": body.personaje_id, "nombre": personaje["nombre"], "rol_en_evento": body.rol_en_evento
    }}})
    return {"ok": True}


@router.delete("/asociaciones/eventos")
def desasociar_evento(personaje_id: str, evento_id: str, _: dict = Depends(_admin)):
    db = get_mongo()
    db.personajes.update_one({"_id": _oid(personaje_id)}, {"$pull": {"eventos": {"evento_id": evento_id}}})
    db.eventos.update_one({"_id": _oid(evento_id)}, {"$pull": {"participantes": {"personaje_id": personaje_id}}})
    return {"ok": True}


@router.post("/asociaciones/peliculas")
def asociar_pelicula(body: AsociacionPeliculaIn, _: dict = Depends(_admin)):
    db = get_mongo()
    personaje = db.personajes.find_one({"_id": _oid(body.personaje_id)})
    pelicula = db.peliculas_libros.find_one({"_id": _oid(body.pelicula_id)})
    if not personaje or not pelicula:
        raise HTTPException(404, "Personaje o pelicula/libro no encontrado")
    db.personajes.update_one({"_id": personaje["_id"]}, {"$addToSet": {"peliculas_libros": {
        "id": body.pelicula_id, "titulo": pelicula["titulo"]
    }}})
    db.peliculas_libros.update_one({"_id": pelicula["_id"]}, {"$addToSet": {"personajes": {
        "id": body.personaje_id, "nombre": personaje["nombre"]
    }}})
    return {"ok": True}


@router.delete("/asociaciones/peliculas")
def desasociar_pelicula(personaje_id: str, pelicula_id: str, _: dict = Depends(_admin)):
    db = get_mongo()
    db.personajes.update_one({"_id": _oid(personaje_id)}, {"$pull": {"peliculas_libros": {"id": pelicula_id}}})
    db.peliculas_libros.update_one({"_id": _oid(pelicula_id)}, {"$pull": {"personajes": {"id": personaje_id}}})
    return {"ok": True}


def register_crud(tipo: str, model: type[BaseModel]):
    async def listar(skip: int = 0, limit: int = 50, _: dict | None = Depends(optional_session)):
        return _list(tipo, skip, limit)

    async def buscar(
        q: str = Query(min_length=1), skip: int = 0, limit: int = 50,
        bg: BackgroundTasks = None, session: dict | None = Depends(optional_session),
    ):
        results = _search(tipo, q, skip, limit)
        if session and bg:
            bg.add_task(_log_busqueda, _session_id(session), q, len(results))
        return results

    async def detalle(item_id: str, bg: BackgroundTasks, session: dict | None = Depends(optional_session)):
        return _detail(tipo, item_id, bg, session)

    async def crear(body: model, _: dict = Depends(_admin)):  # type: ignore[valid-type]
        return _create(tipo, body)

    async def modificar(item_id: str, body: model, _: dict = Depends(_admin)):  # type: ignore[valid-type]
        return _update(tipo, item_id, body)

    async def eliminar(item_id: str, _: dict = Depends(_admin)):
        return _delete(tipo, item_id)

    router.add_api_route(f"/{tipo}", listar, methods=["GET"], name=f"listar_{tipo}")
    router.add_api_route(f"/{tipo}/buscar", buscar, methods=["GET"], name=f"buscar_{tipo}")
    router.add_api_route(f"/{tipo}/{{item_id}}", detalle, methods=["GET"], name=f"detalle_{tipo}")
    router.add_api_route(f"/{tipo}", crear, methods=["POST"], status_code=201, name=f"crear_{tipo}")
    router.add_api_route(f"/{tipo}/{{item_id}}", modificar, methods=["PUT"], name=f"modificar_{tipo}")
    router.add_api_route(f"/{tipo}/{{item_id}}", eliminar, methods=["DELETE"], name=f"eliminar_{tipo}")


for _tipo, (_, _, _model) in COLLECTIONS.items():
    register_crud(_tipo, _model)
