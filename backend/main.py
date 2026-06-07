import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.actividad import router as actividad_router
from routes.auth import router as auth_router
from routes.rankings import router as rankings_router
from routes.universo import router as universo_router


app = FastAPI(title="Harry Potter Polyglot API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Auth - Supabase + Redis"])
app.include_router(universo_router, prefix="/universo", tags=["Universo HP - MongoDB"])
app.include_router(actividad_router, prefix="/actividad", tags=["Actividad - Cassandra"])
app.include_router(rankings_router, prefix="/rankings", tags=["Rankings - Redis"])


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


frontend = Path(__file__).parent.parent / "frontend"
if frontend.exists():
    app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")
