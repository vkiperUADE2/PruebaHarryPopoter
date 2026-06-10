# Harry Potter — Sistema de Bases de Datos Poliglotas

**Materia:** Ingeniería de Datos II — UADE  
**Grupo 5**

| Legajo | Integrante |
|---|---|
| 1109642 | Souto Luciana Belén |
| 1200742 | Kiper Valentín |
| 1153632 | Alvarez Kraus Gabriel |
| 1172868 | Agustín Viñas |

**Entrega:** 10 de junio de 2026

---

## ¿Qué hace este sistema?

Una plataforma web que permite explorar el universo de Harry Potter (personajes, casas, hechizos, eventos, películas y objetos mágicos), implementada con **4 bases de datos distintas**, cada una elegida por sus fortalezas:

| Base de datos | Tipo | ¿Para qué se usa? |
|---|---|---|
| **Supabase (PostgreSQL)** | Relacional | Usuarios y roles — requiere consistencia ACID e integridad referencial |
| **Redis** | Clave-Valor en memoria | Sesiones de usuario (TTL 1 hora) + Rankings en tiempo real |
| **MongoDB Atlas** | Documentos | Todo el universo HP — esquema flexible con subdocumentos embebidos |
| **Cassandra (Astra DB)** | Columnas anchas | Auditoría — logs de actividad y búsquedas de los usuarios |

---

## Estructura del proyecto

```
TPO-Grupo05-HP-V2/
│
├── backend/
│   ├── main.py                  ← Servidor FastAPI (punto de entrada)
│   ├── db/
│   │   ├── supabase_client.py   ← Conexión a Supabase
│   │   ├── redis_client.py      ← Conexión a Redis
│   │   ├── mongo_client.py      ← Conexión a MongoDB Atlas
│   │   └── cassandra_client.py  ← Conexión a Astra DB (Cassandra)
│   ├── routes/
│   │   ├── auth.py              ← Login, registro, logout, sesión
│   │   ├── universo.py          ← CRUD del universo HP (MongoDB)
│   │   ├── actividad.py         ← Historial de actividad (Cassandra)
│   │   └── rankings.py          ← Rankings de contenido (Redis)
│   └── seed/
│       └── seed_all.py          ← Carga inicial de datos en las 4 DBs
│
├── frontend/
│   ├── index.html               ← Interfaz web principal
│   ├── css/style.css            ← Estilos
│   └── js/app.js                ← Lógica del frontend
│
├── migrations/
│   └── 001_init.sql             ← Script SQL para crear tablas en Supabase
│
└── requirements.txt             ← Dependencias Python
```

---

## Requisitos previos

- Python 3.10 o superior
- Acceso a internet (las 4 bases de datos son en la nube)

---

## Paso a paso para inicializar

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Crear las tablas en Supabase

1. Ingresar a [supabase.com](https://supabase.com) con la cuenta del proyecto
2. Ir a **SQL Editor** → **New query**
3. Copiar y pegar el contenido del archivo `migrations/001_init.sql`
4. Hacer clic en **Run**

Esto crea las tablas `roles` y `usuarios`, y desactiva el RLS para permitir operaciones desde el backend.

### 3. Poblar las bases de datos (seed)

Desde la carpeta `backend/`:

```bash
cd backend
python seed/seed_all.py
```

Deberías ver:
```
[Supabase] Insertando roles y usuarios... OK
[MongoDB]  Insertando colecciones...     OK  (4 casas, 10 hechizos, 10 personajes...)
[Cassandra] Inicializando...             OK
[Redis]    Probando conexión...          OK
```

### 4. Iniciar el servidor

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

### 5. Abrir la aplicación

- **Frontend:** http://localhost:8000
- **Documentación de la API:** http://localhost:8000/docs

---

## Usuarios de prueba

| Email | Contraseña | Rol |
|---|---|---|
| harry@hogwarts.com | expecto123 | USUARIO |
| hermione@hogwarts.com | alohomora1 | USUARIO |
| admin@hogwarts.com | admin123 | ADMINISTRADOR |

---

## Endpoints principales

### Autenticación (Supabase + Redis)
| Método | URL | Descripción |
|---|---|---|
| POST | `/auth/register` | Registra un nuevo usuario |
| POST | `/auth/login` | Inicia sesión, devuelve token |
| POST | `/auth/logout` | Cierra sesión |
| GET | `/auth/me` | Devuelve datos del usuario logueado |
| GET | `/auth/usuarios` | Lista todos los usuarios (solo admin) RF3 |
| PUT | `/auth/usuarios/{id}/rol` | Cambia el rol de un usuario (solo admin) RF3 |

### Universo HP (MongoDB)
| Método | URL | Descripción |
|---|---|---|
| GET | `/universo/personajes` | Lista todos los personajes |
| GET | `/universo/personajes/buscar?q=harry` | Busca personajes por nombre |
| GET | `/universo/personajes/{id}` | Detalle de un personaje |
| POST | `/universo/personajes` | Crea un personaje (admin) RF20 |
| PUT | `/universo/personajes/{id}` | Modifica un personaje (admin) RF20 |
| DELETE | `/universo/personajes/{id}` | Elimina un personaje (admin) RF20 |
| POST | `/universo/personajes/{id}/eventos` | Asocia personaje con evento (admin) RF17 |
| DELETE | `/universo/personajes/{id}/eventos/{eid}` | Desasocia del evento (admin) RF17 |
| POST | `/universo/personajes/{id}/peliculas` | Asocia personaje con película (admin) RF18 |
| DELETE | `/universo/personajes/{id}/peliculas/{pid}` | Desasocia de la película (admin) RF18 |
| GET | `/universo/casas` | Lista las casas de Hogwarts |
| GET | `/universo/casas/buscar?q=gryffindor` | Busca casas por nombre o fundador RF19 |
| POST | `/universo/casas` | Crea una casa (admin) RF20 |
| PUT | `/universo/casas/{id}` | Modifica una casa (admin) RF20 |
| DELETE | `/universo/casas/{id}` | Elimina una casa (admin) RF20 |
| GET | `/universo/hechizos` | Lista los hechizos |
| GET | `/universo/hechizos/buscar?q=expecto` | Busca hechizos por nombre o efecto |
| POST | `/universo/hechizos` | Crea un hechizo (admin) RF20 |
| PUT | `/universo/hechizos/{id}` | Modifica un hechizo (admin) RF20 |
| DELETE | `/universo/hechizos/{id}` | Elimina un hechizo (admin) RF20 |
| GET | `/universo/eventos` | Lista los eventos históricos |
| GET | `/universo/eventos/buscar?q=batalla` | Busca eventos por nombre o descripción RF19 |
| POST | `/universo/eventos` | Crea un evento (admin) RF20 |
| PUT | `/universo/eventos/{id}` | Modifica un evento (admin) RF20 |
| DELETE | `/universo/eventos/{id}` | Elimina un evento (admin) RF20 |
| GET | `/universo/peliculas` | Lista películas y libros |
| GET | `/universo/peliculas/buscar?q=piedra` | Busca películas por título o descripción RF19 |
| POST | `/universo/peliculas` | Crea una película (admin) RF20 |
| PUT | `/universo/peliculas/{id}` | Modifica una película (admin) RF20 |
| DELETE | `/universo/peliculas/{id}` | Elimina una película (admin) RF20 |
| GET | `/universo/objetos` | Lista los objetos mágicos |
| GET | `/universo/objetos/buscar?q=varita` | Busca objetos por nombre, descripción o tipo RF19 |
| POST | `/universo/objetos` | Crea un objeto (admin) RF20 |
| PUT | `/universo/objetos/{id}` | Modifica un objeto (admin) RF20 |
| DELETE | `/universo/objetos/{id}` | Elimina un objeto (admin) RF20 |

### Actividad (Cassandra / Astra DB)
| Método | URL | Descripción |
|---|---|---|
| GET | `/actividad/usuario/{id}` | Historial completo del usuario (RF25) |
| GET | `/actividad/usuario/{id}/fecha/2026-06-10` | Actividad filtrada por fecha (RF26) |
| GET | `/actividad/busquedas/{id}` | Historial de búsquedas (RF28) |

### Rankings (Redis)
| Método | URL | Descripción |
|---|---|---|
| GET | `/rankings/global?fecha=2026-06-10` | Top 10 contenidos más visitados del día (RF27) |
| GET | `/rankings/usuario/{id}` | Top 10 del usuario |

---

## Cómo funcionan las sesiones

1. El usuario hace login → el backend verifica en **Supabase** y genera un token
2. El token se guarda en **Redis** como `session:{token}` con expiración de 1 hora
3. Cada petición incluye el header `X-Session-Token: <token>`
4. El backend valida el token leyendo **Redis** directamente (sin consultar Supabase)
5. Al logout, el token se elimina de Redis inmediatamente

## Cómo funciona el tracking de actividad

Cada vez que un usuario logueado visita un detalle (personaje, hechizo, etc.):
1. Se incrementa el contador en **Redis** (`ZINCRBY`) → para los rankings
2. Se inserta un registro en **Cassandra** → para el historial de actividad

Estas dos operaciones se ejecutan en **segundo plano** (BackgroundTasks de FastAPI) para no demorar la respuesta al usuario.
