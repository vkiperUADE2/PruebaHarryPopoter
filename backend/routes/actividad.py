from fastapi import APIRouter, Depends, HTTPException
from db.cassandra_client import get_cassandra
from security import require_session

router = APIRouter()


def _authorize(user_id: int, session: dict):
    if int(session["user_id"]) != user_id and str(session["rol"]) != "2":
        raise HTTPException(403, "No puede consultar la actividad de otro usuario")


def _clean(doc: dict) -> dict:
    doc.pop("$vector", None)
    return doc


@router.get("/usuario/{user_id}")
def historial_usuario(user_id: int, session: dict = Depends(require_session)):
    _authorize(user_id, session)
    try:
        col = get_cassandra().get_collection("actividad_por_usuario")
        docs = list(col.find({"user_id": user_id}))
        return [_clean(d) for d in docs]
    except Exception as e:
        raise HTTPException(503, f"Astra DB no disponible: {e}")


@router.get("/usuario/{user_id}/fecha/{fecha}")
def historial_por_fecha(user_id: int, fecha: str, session: dict = Depends(require_session)):
    _authorize(user_id, session)
    try:
        col = get_cassandra().get_collection("actividad_por_usuario")
        docs = list(col.find({"user_id": user_id, "fecha": fecha}))
        return [_clean(d) for d in docs]
    except Exception as e:
        raise HTTPException(503, f"Astra DB no disponible: {e}")


@router.get("/busquedas/{user_id}")
def busquedas_usuario(user_id: int, session: dict = Depends(require_session)):
    _authorize(user_id, session)
    try:
        col = get_cassandra().get_collection("busquedas_por_usuario")
        docs = list(col.find({"user_id": user_id}))
        return [_clean(d) for d in docs]
    except Exception as e:
        raise HTTPException(503, f"Astra DB no disponible: {e}")
