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
    AsociacionEventoIn, AsociacionPeliculaEventoIn, AsociacionPeliculaIn,
    CasaIn, EventoIn, HechizoIn, ObjetoIn, PeliculaIn, PersonajeIn,
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


def _validate_character_references(db, data: dict) -> dict:
    house_id = data["casa"]["id"]
    house = db.casas.find_one({"_id": _oid(house_id)})
    if not house:
        raise HTTPException(400, "La casa seleccionada no existe")
    data["casa"] = {"id": house_id, "nombre": house["nombre"]}

    spell_ids = [spell["hechizo_id"] for spell in data.get("hechizos", [])]
    if len(spell_ids) != len(set(spell_ids)):
        raise HTTPException(400, "Un personaje no puede tener hechizos repetidos")
    canonical_spells = []
    for spell_id in spell_ids:
        spell = db.hechizos.find_one({"_id": _oid(spell_id)})
        if not spell:
            raise HTTPException(400, "Uno de los hechizos seleccionados no existe")
        canonical_spells.append({"hechizo_id": spell_id, "nombre": spell["nombre"]})
    data["hechizos"] = canonical_spells
    return data


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


def _update_ranking(user_id: int | None, contenido_id: str, nombre: str, tipo: str):
    try:
        r = get_redis()
        hoy = date.today().isoformat()
        with r.pipeline(transaction=True) as pipe:
            pipe.zincrby(f"ranking:global:{hoy}", 1, contenido_id)
            pipe.expire(f"ranking:global:{hoy}", 86400)
            pipe.hset("contenido:catalogo", contenido_id, f"{tipo}|{nombre}")
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
    bg.add_task(_update_ranking, uid, item_id, doc.get(label, ""), tipo)
    if uid:
        bg.add_task(_log_activity, uid, item_id, doc.get(label, ""), tipo)
    return _serialize(doc)


def _create(tipo: str, body: BaseModel):
    col, _, _ = COLLECTIONS[tipo]
    db = get_mongo()
    data = body.model_dump()
    if tipo == "personajes":
        data = _validate_character_references(db, data)
        data["eventos"] = []
        data["peliculas_libros"] = []
    elif tipo == "eventos":
        data["participantes"] = []
        data["peliculas_libros"] = []
    elif tipo == "peliculas":
        data["personajes"] = []
        data["eventos"] = []
    result = db[col].insert_one(data)
    return {"_id": str(result.inserted_id)}


def _update(tipo: str, item_id: str, body: BaseModel):
    col, _, _ = COLLECTIONS[tipo]
    db = get_mongo()
    existing = db[col].find_one({"_id": _oid(item_id)})
    if not existing:
        raise HTTPException(404, "Contenido no encontrado")
    data = body.model_dump()
    if tipo == "personajes":
        data = _validate_character_references(db, data)
        data["eventos"] = existing.get("eventos", [])
        data["peliculas_libros"] = existing.get("peliculas_libros", [])
    elif tipo == "eventos":
        data["participantes"] = existing.get("participantes", [])
        data["peliculas_libros"] = existing.get("peliculas_libros", [])
    elif tipo == "peliculas":
        data["personajes"] = existing.get("personajes", [])
        data["eventos"] = existing.get("eventos", [])
    result = get_mongo()[col].find_one_and_update(
        {"_id": existing["_id"]}, {"$set": data}, return_document=True
    )
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
        db.peliculas_libros.update_many(
            {"eventos.id": item_id}, {"$set": {"eventos.$[ref].nombre": result["nombre"]}},
            array_filters=[{"ref.id": item_id}],
        )
    elif tipo == "peliculas":
        db.personajes.update_many(
            {"peliculas_libros.id": item_id}, {"$set": {"peliculas_libros.$[ref].titulo": result["titulo"]}},
            array_filters=[{"ref.id": item_id}],
        )
        db.eventos.update_many(
            {"peliculas_libros.id": item_id},
            {"$set": {"peliculas_libros.$[ref].titulo": result["titulo"], "peliculas_libros.$[ref].tipo": result["tipo"]}},
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
        db.peliculas_libros.update_many({}, {"$pull": {"eventos": {"id": item_id}}})
    elif tipo == "peliculas":
        db.personajes.update_many({}, {"$pull": {"peliculas_libros": {"id": item_id}}})
        db.eventos.update_many({}, {"$pull": {"peliculas_libros": {"id": item_id}}})
    elif tipo == "personajes":
        db.eventos.update_many({}, {"$pull": {"participantes": {"personaje_id": item_id}}})
        db.peliculas_libros.update_many({}, {"$pull": {"personajes": {"id": item_id}}})
    return {"ok": True}


def _search(tipo: str, q: str, skip: int, limit: int):
    col, label, _ = COLLECTIONS[tipo]
    fields = {
        "personajes": ["nombre", "rol", "alineacion", "casa.nombre", "hechizos.nombre", "eventos.nombre", "peliculas_libros.titulo"],
        "casas": ["nombre", "fundador", "mascota", "valores"],
        "hechizos": ["nombre", "descripcion", "efecto"],
        "eventos": ["nombre", "descripcion", "participantes.nombre"],
        "peliculas": ["titulo", "tipo", "descripcion", "personajes.nombre", "eventos.nombre"],
        "objetos": ["nombre", "descripcion", "tipo"],
    }[tipo]
    safe_q = re.escape(q)
    query = {"$or": [{f: {"$regex": safe_q, "$options": "i"}} for f in fields]}
    skip, limit = _page(skip, limit)
    return [_serialize(d) for d in get_mongo()[col].find(query).skip(skip).limit(limit)]


@router.get("/{tipo}/cantidad")
def cantidad(tipo: str, q: str | None = None, _: dict | None = Depends(optional_session)):
    if tipo not in COLLECTIONS:
        raise HTTPException(404, "Categoria no encontrada")
    col, _, _ = COLLECTIONS[tipo]
    if not q:
        return {"cantidad": get_mongo()[col].count_documents({})}
    safe_q = re.escape(q)
    fields = {
        "personajes": ["nombre", "rol", "alineacion", "casa.nombre", "hechizos.nombre", "eventos.nombre", "peliculas_libros.titulo"],
        "casas": ["nombre", "fundador", "mascota", "valores"],
        "hechizos": ["nombre", "descripcion", "efecto"],
        "eventos": ["nombre", "descripcion", "participantes.nombre"],
        "peliculas": ["titulo", "tipo", "descripcion", "personajes.nombre", "eventos.nombre"],
        "objetos": ["nombre", "descripcion", "tipo"],
    }[tipo]
    query = {"$or": [{field: {"$regex": safe_q, "$options": "i"}} for field in fields]}
    return {"cantidad": get_mongo()[col].count_documents(query)}


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
    person_ref = {"evento_id": body.evento_id, "nombre": evento["nombre"], "rol_en_evento": body.rol_en_evento}
    event_ref = {"personaje_id": body.personaje_id, "nombre": personaje["nombre"], "rol_en_evento": body.rol_en_evento}
    db.personajes.update_one({"_id": personaje["_id"]}, {"$addToSet": {"eventos": person_ref}})
    try:
        db.eventos.update_one({"_id": evento["_id"]}, {"$addToSet": {"participantes": event_ref}})
    except Exception:
        db.personajes.update_one({"_id": personaje["_id"]}, {"$pull": {"eventos": {"evento_id": body.evento_id}}})
        raise
    return {"ok": True}


@router.delete("/asociaciones/eventos")
def desasociar_evento(personaje_id: str, evento_id: str, _: dict = Depends(_admin)):
    db = get_mongo()
    personaje = db.personajes.find_one({"_id": _oid(personaje_id)})
    evento = db.eventos.find_one({"_id": _oid(evento_id)})
    if not personaje or not evento:
        raise HTTPException(404, "Personaje o evento no encontrado")
    db.personajes.update_one({"_id": personaje["_id"]}, {"$pull": {"eventos": {"evento_id": evento_id}}})
    db.eventos.update_one({"_id": evento["_id"]}, {"$pull": {"participantes": {"personaje_id": personaje_id}}})
    return {"ok": True}


@router.post("/asociaciones/peliculas")
def asociar_pelicula(body: AsociacionPeliculaIn, _: dict = Depends(_admin)):
    db = get_mongo()
    personaje = db.personajes.find_one({"_id": _oid(body.personaje_id)})
    pelicula = db.peliculas_libros.find_one({"_id": _oid(body.pelicula_id)})
    if not personaje or not pelicula:
        raise HTTPException(404, "Personaje o pelicula/libro no encontrado")
    person_ref = {"id": body.pelicula_id, "titulo": pelicula["titulo"]}
    movie_ref = {"id": body.personaje_id, "nombre": personaje["nombre"]}
    db.personajes.update_one({"_id": personaje["_id"]}, {"$addToSet": {"peliculas_libros": person_ref}})
    try:
        db.peliculas_libros.update_one({"_id": pelicula["_id"]}, {"$addToSet": {"personajes": movie_ref}})
    except Exception:
        db.personajes.update_one({"_id": personaje["_id"]}, {"$pull": {"peliculas_libros": {"id": body.pelicula_id}}})
        raise
    return {"ok": True}


@router.delete("/asociaciones/peliculas")
def desasociar_pelicula(personaje_id: str, pelicula_id: str, _: dict = Depends(_admin)):
    db = get_mongo()
    personaje = db.personajes.find_one({"_id": _oid(personaje_id)})
    pelicula = db.peliculas_libros.find_one({"_id": _oid(pelicula_id)})
    if not personaje or not pelicula:
        raise HTTPException(404, "Personaje o pelicula/libro no encontrado")
    db.personajes.update_one({"_id": personaje["_id"]}, {"$pull": {"peliculas_libros": {"id": pelicula_id}}})
    db.peliculas_libros.update_one({"_id": pelicula["_id"]}, {"$pull": {"personajes": {"id": personaje_id}}})
    return {"ok": True}


@router.post("/asociaciones/peliculas-eventos")
def asociar_pelicula_evento(body: AsociacionPeliculaEventoIn, _: dict = Depends(_admin)):
    db = get_mongo()
    pelicula = db.peliculas_libros.find_one({"_id": _oid(body.pelicula_id)})
    evento = db.eventos.find_one({"_id": _oid(body.evento_id)})
    if not pelicula or not evento:
        raise HTTPException(404, "Pelicula/libro o evento no encontrado")
    movie_ref = {"id": body.evento_id, "nombre": evento["nombre"]}
    event_ref = {"id": body.pelicula_id, "titulo": pelicula["titulo"], "tipo": pelicula["tipo"]}
    db.peliculas_libros.update_one({"_id": pelicula["_id"]}, {"$addToSet": {"eventos": movie_ref}})
    try:
        db.eventos.update_one({"_id": evento["_id"]}, {"$addToSet": {"peliculas_libros": event_ref}})
    except Exception:
        db.peliculas_libros.update_one({"_id": pelicula["_id"]}, {"$pull": {"eventos": {"id": body.evento_id}}})
        raise
    return {"ok": True}


@router.delete("/asociaciones/peliculas-eventos")
def desasociar_pelicula_evento(pelicula_id: str, evento_id: str, _: dict = Depends(_admin)):
    db = get_mongo()
    pelicula = db.peliculas_libros.find_one({"_id": _oid(pelicula_id)})
    evento = db.eventos.find_one({"_id": _oid(evento_id)})
    if not pelicula or not evento:
        raise HTTPException(404, "Pelicula/libro o evento no encontrado")
    db.peliculas_libros.update_one({"_id": pelicula["_id"]}, {"$pull": {"eventos": {"id": evento_id}}})
    db.eventos.update_one({"_id": evento["_id"]}, {"$pull": {"peliculas_libros": {"id": pelicula_id}}})
    return {"ok": True}


def register_crud(tipo: str, model: type[BaseModel]):
    def listar(skip: int = 0, limit: int = 50, _: dict | None = Depends(optional_session)):
        return _list(tipo, skip, limit)

    def buscar(
        q: str = Query(min_length=1), skip: int = 0, limit: int = 50,
        bg: BackgroundTasks = None, session: dict | None = Depends(optional_session),
    ):
        results = _search(tipo, q, skip, limit)
        if session and bg:
            bg.add_task(_log_busqueda, _session_id(session), q, len(results))
        return results

    def detalle(item_id: str, bg: BackgroundTasks, session: dict | None = Depends(optional_session)):
        return _detail(tipo, item_id, bg, session)

    def crear(body: model, _: dict = Depends(_admin)):  # type: ignore[valid-type]
        return _create(tipo, body)

    def modificar(item_id: str, body: model, _: dict = Depends(_admin)):  # type: ignore[valid-type]
        return _update(tipo, item_id, body)

    def eliminar(item_id: str, _: dict = Depends(_admin)):
        return _delete(tipo, item_id)

    router.add_api_route(f"/{tipo}", listar, methods=["GET"], name=f"listar_{tipo}")
    router.add_api_route(f"/{tipo}/buscar", buscar, methods=["GET"], name=f"buscar_{tipo}")
    router.add_api_route(f"/{tipo}/{{item_id}}", detalle, methods=["GET"], name=f"detalle_{tipo}")
    router.add_api_route(f"/{tipo}", crear, methods=["POST"], status_code=201, name=f"crear_{tipo}")
    router.add_api_route(f"/{tipo}/{{item_id}}", modificar, methods=["PUT"], name=f"modificar_{tipo}")
    router.add_api_route(f"/{tipo}/{{item_id}}", eliminar, methods=["DELETE"], name=f"eliminar_{tipo}")


for _tipo, (_, _, _model) in COLLECTIONS.items():
    register_crud(_tipo, _model)
