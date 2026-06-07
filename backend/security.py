from fastapi import Header, HTTPException

from db.redis_client import get_redis


def optional_session(x_session_token: str | None = Header(None)) -> dict | None:
    if not x_session_token:
        return None
    data = get_redis().hgetall(f"session:{x_session_token}")
    if not data:
        raise HTTPException(401, "Sesion invalida o expirada")
    return data


def require_session(x_session_token: str | None = Header(None)) -> dict:
    if not x_session_token:
        raise HTTPException(401, "Token requerido")
    data = get_redis().hgetall(f"session:{x_session_token}")
    if not data:
        raise HTTPException(401, "Sesion invalida o expirada")
    return data


def ensure_admin(session: dict) -> dict:
    if str(session.get("rol")) != "2":
        raise HTTPException(403, "Se requiere rol administrador")
    return session
