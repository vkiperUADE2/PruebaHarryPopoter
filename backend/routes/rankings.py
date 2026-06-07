# ============================================================
# routes/rankings.py — Rankings en tiempo real (RF 27)
#
# Usa Redis Sorted Sets (ZSET) para mantener rankings ordenados
# por cantidad de visitas. Redis los calcula en memoria RAM,
# lo que lo hace extremadamente rápido (O(log N) por operación).
#
# Claves usadas en Redis:
#   - ranking:global:{fecha}     → top contenido de todos los usuarios ese día
#   - ranking:usuario:{user_id}  → top contenido consultado por ese usuario
#
# Cada vez que alguien visita un personaje, hechizo, etc.,
# la ruta correspondiente en universo.py incrementa el puntaje
# de ese contenido en los ZSETs mediante ZINCRBY.
# ============================================================

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from db.redis_client import get_redis
from security import require_session

router = APIRouter()


@router.get("/global")
def ranking_global(fecha: str = None, top: int = 10):
    """
    RF27 — Devuelve el top N de contenidos más visitados en un día.
    Si no se especifica fecha, usa el día de hoy.
    Usa ZREVRANGE para obtener los elementos del ZSET ordenados
    de mayor a menor puntaje (más visitado primero).
    """
    # Si no se pasa fecha, usa la fecha actual en formato YYYY-MM-DD
    if not fecha:
        fecha = date.today().isoformat()
    try:
        r = get_redis()
        # zrevrange: devuelve elementos del índice 0 al top-1, ordenados desc
        # withscores=True incluye el puntaje (cantidad de visitas) en el resultado
        items = r.zrevrange(f"ranking:global:{fecha}", 0, top - 1, withscores=True)
        return [{"contenido_id": k, "visitas": int(v)} for k, v in items]
    except Exception as e:
        raise HTTPException(503, f"Redis no disponible: {e}")


@router.get("/usuario/{user_id}")
def ranking_usuario(user_id: int, top: int = 10, session: dict = Depends(require_session)):
    """
    RF27 — Devuelve el top N de contenidos más visitados por un usuario específico.
    Permite mostrar al usuario qué temas consulta con más frecuencia.
    """
    if int(session["user_id"]) != user_id and str(session["rol"]) != "2":
        raise HTTPException(403, "No puede consultar el ranking de otro usuario")
    try:
        r = get_redis()
        items = r.zrevrange(f"ranking:usuario:{user_id}", 0, top - 1, withscores=True)
        return [{"contenido_id": k, "visitas": int(v)} for k, v in items]
    except Exception as e:
        raise HTTPException(503, f"Redis no disponible: {e}")
