from datetime import datetime

from pydantic import BaseModel, Field


class CasaRef(BaseModel):
    id: str
    nombre: str


class HechizoRef(BaseModel):
    hechizo_id: str
    nombre: str


class EventoRef(BaseModel):
    evento_id: str
    nombre: str
    rol_en_evento: str


class PeliculaRef(BaseModel):
    id: str
    titulo: str


class PersonajeIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    fecha_nacimiento: datetime
    casa: CasaRef
    rol: str = Field(min_length=1, max_length=80)
    alineacion: str = Field(min_length=1, max_length=40)
    peliculas_libros: list[PeliculaRef] = Field(default_factory=list)
    hechizos: list[HechizoRef] = Field(default_factory=list)
    eventos: list[EventoRef] = Field(default_factory=list)


class CasaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    fundador: str = Field(min_length=1, max_length=120)
    valores: list[str] = Field(min_length=1)
    mascota: str = Field(min_length=1, max_length=100)


class HechizoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str = Field(min_length=1, max_length=500)
    efecto: str = Field(min_length=1, max_length=500)


class EventoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    fecha: datetime
    descripcion: str = Field(min_length=1, max_length=1000)
    participantes: list[dict] = Field(default_factory=list)


class PeliculaIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    tipo: str = Field(pattern="^(pelicula|libro)$")
    anio_lanzamiento: int = Field(ge=1800, le=2200)
    descripcion: str = Field(min_length=1, max_length=1000)
    personajes: list[dict] = Field(default_factory=list)
    eventos: list[dict] = Field(default_factory=list)


class ObjetoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    descripcion: str = Field(min_length=1, max_length=1000)
    tipo: str = Field(min_length=1, max_length=80)


class AsociacionEventoIn(BaseModel):
    personaje_id: str
    evento_id: str
    rol_en_evento: str = Field(min_length=1, max_length=100)


class AsociacionPeliculaIn(BaseModel):
    personaje_id: str
    pelicula_id: str
