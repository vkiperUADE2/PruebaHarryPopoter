import secrets

from fastapi import APIRouter, Depends, HTTPException, Header
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from db.redis_client import get_redis
from db.supabase_client import get_supabase
from security import ensure_admin, require_session


router = APIRouter()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_TTL = 3600


class RegisterIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RolIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=50)
    descripcion: str = Field(default="", max_length=255)


class UsuarioAdminIn(BaseModel):
    rol_id: int = Field(ge=1)
    activo: bool = True


def _admin(session: dict = Depends(require_session)) -> dict:
    return ensure_admin(session)


@router.post("/register", status_code=201)
def register(body: RegisterIn):
    sb = get_supabase()
    existing = sb.table("usuarios").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(400, "Email ya registrado")
    result = sb.table("usuarios").insert({
        "nombre": body.nombre,
        "email": body.email,
        "password_hash": pwd.hash(body.password),
        "rol_id": 1,
        "activo": True,
    }).execute()
    user = result.data[0]
    return {"id": user["id"], "nombre": user["nombre"], "email": user["email"]}


@router.post("/login")
def login(body: LoginIn):
    result = get_supabase().table("usuarios").select("*").eq(
        "email", body.email
    ).eq("activo", True).execute()
    if not result.data or not pwd.verify(body.password, result.data[0]["password_hash"]):
        raise HTTPException(401, "Credenciales invalidas")
    user = result.data[0]
    token = secrets.token_urlsafe(32)
    r = get_redis()
    r.hset(f"session:{token}", mapping={
        "user_id": user["id"],
        "nombre": user["nombre"],
        "email": user["email"],
        "rol": str(user["rol_id"]),
    })
    r.expire(f"session:{token}", SESSION_TTL)
    return {
        "token": token,
        "user_id": user["id"],
        "nombre": user["nombre"],
        "email": user["email"],
        "rol_id": user["rol_id"],
    }


@router.post("/logout")
def logout(x_session_token: str | None = Header(None)):
    if x_session_token:
        get_redis().delete(f"session:{x_session_token}")
    return {"ok": True}


@router.get("/me")
def me(session: dict = Depends(require_session)):
    return session


@router.get("/roles")
def listar_roles(_: dict = Depends(_admin)):
    return get_supabase().table("roles").select("*").order("id").execute().data


@router.post("/roles", status_code=201)
def crear_rol(body: RolIn, _: dict = Depends(_admin)):
    return get_supabase().table("roles").insert(body.model_dump()).execute().data[0]


@router.put("/roles/{rol_id}")
def modificar_rol(rol_id: int, body: RolIn, _: dict = Depends(_admin)):
    result = get_supabase().table("roles").update(body.model_dump()).eq("id", rol_id).execute()
    if not result.data:
        raise HTTPException(404, "Rol no encontrado")
    return result.data[0]


@router.delete("/roles/{rol_id}")
def eliminar_rol(rol_id: int, _: dict = Depends(_admin)):
    if rol_id in (1, 2):
        raise HTTPException(400, "Los roles base no pueden eliminarse")
    sb = get_supabase()
    if sb.table("usuarios").select("id").eq("rol_id", rol_id).limit(1).execute().data:
        raise HTTPException(409, "No se puede eliminar un rol asignado a usuarios")
    result = sb.table("roles").delete().eq("id", rol_id).execute()
    if not result.data:
        raise HTTPException(404, "Rol no encontrado")
    return {"ok": True}


@router.get("/usuarios")
def listar_usuarios(_: dict = Depends(_admin)):
    return get_supabase().table("usuarios").select(
        "id,nombre,email,rol_id,activo,created_at"
    ).order("id").execute().data


@router.put("/usuarios/{user_id}")
def gestionar_usuario(user_id: int, body: UsuarioAdminIn, session: dict = Depends(_admin)):
    if int(session["user_id"]) == user_id and not body.activo:
        raise HTTPException(400, "Un administrador no puede desactivarse a si mismo")
    sb = get_supabase()
    if not sb.table("roles").select("id").eq("id", body.rol_id).execute().data:
        raise HTTPException(404, "Rol no encontrado")
    result = sb.table("usuarios").update(body.model_dump()).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(404, "Usuario no encontrado")
    redis = get_redis()
    sessions = [
        key for key in redis.scan_iter("session:*")
        if redis.hget(key, "user_id") == str(user_id)
    ]
    if sessions:
        redis.delete(*sessions)
    return {
        "id": result.data[0]["id"],
        "nombre": result.data[0]["nombre"],
        "email": result.data[0]["email"],
        "rol_id": result.data[0]["rol_id"],
        "activo": result.data[0]["activo"],
    }
