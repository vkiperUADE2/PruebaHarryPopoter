# ============================================================
# routes/actividad.py — Historial de actividad (RF 25–26–28)
#
# Este módulo consulta la base de datos Cassandra (Astra DB)
# para recuperar el historial de acciones de los usuarios.
#
# Cassandra fue elegida para auditoría porque está optimizada
# para escrituras masivas y consultas por clave de partición
# (user_id), garantizando baja latencia aunque haya millones
# de registros acumulados.
#
# Colecciones usadas:
#   - actividad_por_usuario: todas las vistas del usuario
#   - busquedas_por_usuario: todos los términos buscados
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from db.cassandra_client import get_cassandra
from security import require_session

router = APIRouter()


def _authorize(user_id: int, session: dict):
    if int(session["user_id"]) != user_id and str(session["rol"]) != "2":
        raise HTTPException(403, "No puede consultar la actividad de otro usuario")


def _clean(doc: dict) -> dict:
    """
    Elimina el campo '$vector' que Astra DB agrega internamente
    a cada documento. No es relevante para mostrar al usuario.
    """
    doc.pop("$vector", None)
    return doc


@router.get("/usuario/{user_id}")
def historial_usuario(user_id: int, session: dict = Depends(require_session)):
    """
    RF25 — Devuelve el historial COMPLETO de actividad de un usuario.
    Consulta la colección 'actividad_por_usuario' filtrando por user_id.
    Cada registro representa un contenido que el usuario visitó.
    """
    _authorize(user_id, session)
    try:
        # Obtiene la colección de actividad de Astra DB
        col = get_cassandra().get_collection("actividad_por_usuario")
        # Filtra todos los documentos donde user_id coincida
        docs = list(col.find({"user_id": user_id}))
        return [_clean(d) for d in docs]
    except Exception as e:
        raise HTTPException(503, f"Astra DB no disponible: {e}")


@router.get("/usuario/{user_id}/fecha/{fecha}")
def historial_por_fecha(user_id: int, fecha: str, session: dict = Depends(require_session)):
    """
    RF26 — Devuelve la actividad de un usuario FILTRADA por una fecha específica.
    La fecha debe estar en formato YYYY-MM-DD (ej: 2026-06-10).
    Permite al usuario ver exactamente qué consultó en un día determinado.
    """
    _authorize(user_id, session)
    try:
        col = get_cassandra().get_collection("actividad_por_usuario")
        # Doble filtro: por usuario Y por fecha (almacenada como string ISO)
        docs = list(col.find({"user_id": user_id, "fecha": fecha}))
        return [_clean(d) for d in docs]
    except Exception as e:
        raise HTTPException(503, f"Astra DB no disponible: {e}")


@router.get("/busquedas/{user_id}")
def busquedas_usuario(user_id: int, session: dict = Depends(require_session)):
    """
    RF28 — Devuelve el historial de búsquedas realizadas por el usuario.
    Consulta la colección 'busquedas_por_usuario' filtrando por user_id.
    Cada registro incluye el texto buscado y cuántos resultados se encontraron.
    """
    _authorize(user_id, session)
    try:
        col = get_cassandra().get_collection("busquedas_por_usuario")
        docs = list(col.find({"user_id": user_id}))
        return [_clean(d) for d in docs]
    except Exception as e:
        raise HTTPException(503, f"Astra DB no disponible: {e}")
