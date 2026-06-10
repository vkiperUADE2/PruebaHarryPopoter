import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from bson import ObjectId
from passlib.context import CryptContext
from db.supabase_client import get_supabase
from db.mongo_client import get_mongo
from db.redis_client import get_redis
from db.cassandra_client import get_cassandra

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_supabase():
    print("\n[Supabase] Insertando roles y usuarios...")
    sb = get_supabase()

    sb.table("roles").upsert([
        {"id": 1, "nombre": "USUARIO",        "descripcion": "Usuario estándar"},
        {"id": 2, "nombre": "ADMINISTRADOR",   "descripcion": "Acceso total"},
    ]).execute()

    usuarios = [
        {"nombre": "Admin Hogwarts",  "email": "admin@hogwarts.com",    "password": "admin123",    "rol_id": 2},
        {"nombre": "Harry Potter",    "email": "harry@hogwarts.com",    "password": "expecto123",  "rol_id": 1},
        {"nombre": "Hermione Granger","email": "hermione@hogwarts.com", "password": "alohomora1",  "rol_id": 1},
    ]
    for u in usuarios:
        existing = sb.table("usuarios").select("id").eq("email", u["email"]).execute()
        if not existing.data:
            sb.table("usuarios").insert({
                "nombre":        u["nombre"],
                "email":         u["email"],
                "password_hash": pwd.hash(u["password"]),
                "rol_id":        u["rol_id"],
                "activo":        True,
            }).execute()
            print(f"  + usuario: {u['email']}")
        else:
            print(f"  ~ ya existe: {u['email']}")
    print("[Supabase] OK")


def seed_mongo():
    print("\n[MongoDB] Insertando colecciones...")
    db = get_mongo()
    db.personajes.create_index("nombre")
    db.casas.create_index("nombre")
    db.hechizos.create_index("nombre")
    db.eventos.create_index("nombre")
    db.peliculas_libros.create_index("titulo")
    db.objetos_magicos.create_index("nombre")

    for col in ["casas","hechizos","peliculas_libros","objetos_magicos","eventos","personajes"]:
        db[col].delete_many({})

    casas_ids = db.casas.insert_many([
        {"nombre":"Gryffindor","fundador":"Godric Gryffindor","mascota":"León",
         "valores":["valentía","coraje","caballerosidad","determinación"]},
        {"nombre":"Slytherin","fundador":"Salazar Slytherin","mascota":"Serpiente",
         "valores":["ambición","astucia","liderazgo","ingenio"]},
        {"nombre":"Ravenclaw","fundador":"Rowena Ravenclaw","mascota":"Águila",
         "valores":["inteligencia","sabiduría","creatividad","aprendizaje"]},
        {"nombre":"Hufflepuff","fundador":"Helga Hufflepuff","mascota":"Tejón",
         "valores":["lealtad","paciencia","trabajo duro","justicia"]},
    ]).inserted_ids

    casa_map = {
        "Gryffindor": casas_ids[0],
        "Slytherin":  casas_ids[1],
        "Ravenclaw":  casas_ids[2],
        "Hufflepuff": casas_ids[3],
    }
    print(f"  + {len(casas_ids)} casas")

    hechizos_ids = db.hechizos.insert_many([
        {"nombre":"Expelliarmus",      "descripcion":"Hechizo desarmador",        "efecto":"Desarma al oponente"},
        {"nombre":"Wingardium Leviosa","descripcion":"Hechizo de levitación",     "efecto":"Hace flotar objetos"},
        {"nombre":"Expecto Patronum",  "descripcion":"Hechizo del patronus",       "efecto":"Conjura un patronus protector"},
        {"nombre":"Avada Kedavra",     "descripcion":"Maldición asesina",          "efecto":"Muerte instantánea"},
        {"nombre":"Lumos",             "descripcion":"Hechizo de luz",             "efecto":"Ilumina la varita"},
        {"nombre":"Accio",             "descripcion":"Hechizo invocador",          "efecto":"Atrae objetos hacia el lanzador"},
        {"nombre":"Alohomora",         "descripcion":"Hechizo de apertura",        "efecto":"Abre cerraduras"},
        {"nombre":"Stupefy",           "descripcion":"Hechizo paralizador",        "efecto":"Aturde al objetivo"},
        {"nombre":"Crucio",            "descripcion":"Maldición imperdonable",     "efecto":"Tortura a la víctima"},
        {"nombre":"Imperio",           "descripcion":"Maldición de control",       "efecto":"Controla la voluntad del objetivo"},
    ]).inserted_ids
    print(f"  + {len(hechizos_ids)} hechizos")

    peliculas_ids = db.peliculas_libros.insert_many([
        {"titulo":"Harry Potter y la Piedra Filosofal",        "tipo":"libro",    "anio_lanzamiento":1997,"descripcion":"El inicio de la aventura mágica de Harry."},
        {"titulo":"Harry Potter y la Piedra Filosofal",        "tipo":"pelicula", "anio_lanzamiento":2001,"descripcion":"Adaptación cinematográfica del primer libro."},
        {"titulo":"Harry Potter y la Cámara Secreta",          "tipo":"libro",    "anio_lanzamiento":1998,"descripcion":"Harry descubre un misterio oscuro en Hogwarts."},
        {"titulo":"Harry Potter y la Cámara Secreta",          "tipo":"pelicula", "anio_lanzamiento":2002,"descripcion":"Adaptación del segundo libro."},
        {"titulo":"Harry Potter y el Prisionero de Azkaban",   "tipo":"libro",    "anio_lanzamiento":1999,"descripcion":"Un prisionero escapa de Azkaban."},
        {"titulo":"Harry Potter y el Prisionero de Azkaban",   "tipo":"pelicula", "anio_lanzamiento":2004,"descripcion":"Adaptación del tercer libro."},
        {"titulo":"Harry Potter y el Cáliz de Fuego",          "tipo":"libro",    "anio_lanzamiento":2000,"descripcion":"El Torneo de los Tres Magos pone en peligro a Harry."},
        {"titulo":"Harry Potter y el Cáliz de Fuego",          "tipo":"pelicula", "anio_lanzamiento":2005,"descripcion":"Adaptación del cuarto libro."},
        {"titulo":"Harry Potter y la Orden del Fénix",         "tipo":"libro",    "anio_lanzamiento":2003,"descripcion":"Voldemort regresa y Harry forma el Ejército de Dumbledore."},
        {"titulo":"Harry Potter y el Misterio del Príncipe",   "tipo":"libro",    "anio_lanzamiento":2005,"descripcion":"Dumbledore revela el pasado de Voldemort."},
        {"titulo":"Harry Potter y las Reliquias de la Muerte", "tipo":"libro",    "anio_lanzamiento":2007,"descripcion":"La batalla final contra Voldemort."},
        {"titulo":"Harry Potter y las Reliquias de la Muerte Parte 1","tipo":"pelicula","anio_lanzamiento":2010,"descripcion":"Primera parte de la adaptación final."},
        {"titulo":"Harry Potter y las Reliquias de la Muerte Parte 2","tipo":"pelicula","anio_lanzamiento":2011,"descripcion":"La batalla definitiva de Hogwarts."},
    ]).inserted_ids
    db.peliculas_libros.update_many({}, {"$set": {"personajes": [], "eventos": []}})
    print(f"  + {len(peliculas_ids)} películas/libros")

    db.objetos_magicos.insert_many([
        {"nombre":"Varita del Saúco",           "descripcion":"La varita más poderosa del mundo mágico.","tipo":"artefacto"},
        {"nombre":"Piedra de la Resurrección",  "descripcion":"Una de las Reliquias de la Muerte.","tipo":"reliquia"},
        {"nombre":"Capa de Invisibilidad",      "descripcion":"Capa que oculta completamente a su portador.","tipo":"reliquia"},
        {"nombre":"Mapa del Merodeador",        "descripcion":"Muestra todos los pasadizos y personas en Hogwarts.","tipo":"mapa"},
        {"nombre":"Remembrall",                 "descripcion":"Esfera que avisa cuando se olvidó algo.","tipo":"objeto"},
        {"nombre":"Snitch Dorada",              "descripcion":"Pelota veloz usada en el Quidditch.","tipo":"deporte"},
        {"nombre":"Caldero de Hufflepuff",      "descripcion":"Uno de los Horrocruxes de Voldemort.","tipo":"horrocrux"},
        {"nombre":"Diario de Tom Riddle",       "descripcion":"Horrocrux que controlaba a Ginny Weasley.","tipo":"horrocrux"},
    ])
    print("  + 8 objetos mágicos")

    eventos_result = db.eventos.insert_many([
        {"nombre":"Batalla de Hogwarts",
         "fecha":datetime(1998,5,2),
         "descripcion":"Batalla final entre las fuerzas de Voldemort y los defensores de Hogwarts.",
         "participantes":[],"peliculas_libros":[]},
        {"nombre":"Torneo de los Tres Magos",
         "fecha":datetime(1994,9,1),
         "descripcion":"Competencia mágica internacional celebrada en Hogwarts.",
         "participantes":[],"peliculas_libros":[]},
        {"nombre":"Primera Caída de Voldemort",
         "fecha":datetime(1981,10,31),
         "descripcion":"Voldemort intenta matar a Harry de bebé y pierde sus poderes.",
         "participantes":[],"peliculas_libros":[]},
        {"nombre":"Fundación de Hogwarts",
         "fecha":datetime(993,9,1),
         "descripcion":"Los cuatro grandes magos fundan la escuela de magia.",
         "participantes":[],"peliculas_libros":[]},
        {"nombre":"Batalla del Departamento de Misterios",
         "fecha":datetime(1996,6,18),
         "descripcion":"El Ejército de Dumbledore se enfrenta a los mortífagos.",
         "participantes":[],"peliculas_libros":[]},
    ])
    eventos_ids = eventos_result.inserted_ids
    print(f"  + {len(eventos_ids)} eventos")

    personajes = [
        {
            "nombre":"Harry Potter",
            "fecha_nacimiento":datetime(1980,7,31),
            "rol":"Protagonista",
            "alineacion":"Bien",
            "casa":{"id":str(casa_map["Gryffindor"]),"nombre":"Gryffindor"},
            "peliculas_libros":[{"id":str(i),"titulo":"HP"} for i in peliculas_ids[:4]],
            "hechizos":[
                {"hechizo_id":str(hechizos_ids[0]),"nombre":"Expelliarmus"},
                {"hechizo_id":str(hechizos_ids[2]),"nombre":"Expecto Patronum"},
            ],
            "eventos":[
                {"evento_id":str(eventos_ids[0]),"nombre":"Batalla de Hogwarts","rol_en_evento":"Protagonista"},
            ],
        },
        {
            "nombre":"Hermione Granger",
            "fecha_nacimiento":datetime(1979,9,19),
            "rol":"Amiga",
            "alineacion":"Bien",
            "casa":{"id":str(casa_map["Gryffindor"]),"nombre":"Gryffindor"},
            "peliculas_libros":[],
            "hechizos":[
                {"hechizo_id":str(hechizos_ids[6]),"nombre":"Alohomora"},
                {"hechizo_id":str(hechizos_ids[1]),"nombre":"Wingardium Leviosa"},
            ],
            "eventos":[],
        },
        {
            "nombre":"Ron Weasley",
            "fecha_nacimiento":datetime(1980,3,1),
            "rol":"Amigo",
            "alineacion":"Bien",
            "casa":{"id":str(casa_map["Gryffindor"]),"nombre":"Gryffindor"},
            "peliculas_libros":[],
            "hechizos":[{"hechizo_id":str(hechizos_ids[1]),"nombre":"Wingardium Leviosa"}],
            "eventos":[],
        },
        {
            "nombre":"Albus Dumbledore",
            "fecha_nacimiento":datetime(1881,7,1),
            "rol":"Director",
            "alineacion":"Bien",
            "casa":{"id":str(casa_map["Gryffindor"]),"nombre":"Gryffindor"},
            "peliculas_libros":[],
            "hechizos":[],
            "eventos":[{"evento_id":str(eventos_ids[0]),"nombre":"Batalla de Hogwarts","rol_en_evento":"Mentor"}],
        },
        {
            "nombre":"Severus Snape",
            "fecha_nacimiento":datetime(1960,1,9),
            "rol":"Profesor",
            "alineacion":"Ambiguo",
            "casa":{"id":str(casa_map["Slytherin"]),"nombre":"Slytherin"},
            "peliculas_libros":[],
            "hechizos":[{"hechizo_id":str(hechizos_ids[0]),"nombre":"Expelliarmus"}],
            "eventos":[],
        },
        {
            "nombre":"Draco Malfoy",
            "fecha_nacimiento":datetime(1980,6,5),
            "rol":"Antagonista",
            "alineacion":"Mal",
            "casa":{"id":str(casa_map["Slytherin"]),"nombre":"Slytherin"},
            "peliculas_libros":[],
            "hechizos":[{"hechizo_id":str(hechizos_ids[7]),"nombre":"Stupefy"}],
            "eventos":[],
        },
        {
            "nombre":"Lord Voldemort",
            "fecha_nacimiento":datetime(1926,12,31),
            "rol":"Villano Principal",
            "alineacion":"Mal",
            "casa":{"id":str(casa_map["Slytherin"]),"nombre":"Slytherin"},
            "peliculas_libros":[],
            "hechizos":[
                {"hechizo_id":str(hechizos_ids[3]),"nombre":"Avada Kedavra"},
                {"hechizo_id":str(hechizos_ids[8]),"nombre":"Crucio"},
                {"hechizo_id":str(hechizos_ids[9]),"nombre":"Imperio"},
            ],
            "eventos":[
                {"evento_id":str(eventos_ids[2]),"nombre":"Primera Caída de Voldemort","rol_en_evento":"Antagonista"},
                {"evento_id":str(eventos_ids[0]),"nombre":"Batalla de Hogwarts","rol_en_evento":"Antagonista"},
            ],
        },
        {
            "nombre":"Luna Lovegood",
            "fecha_nacimiento":datetime(1980,2,13),
            "rol":"Amiga",
            "alineacion":"Bien",
            "casa":{"id":str(casa_map["Ravenclaw"]),"nombre":"Ravenclaw"},
            "peliculas_libros":[],
            "hechizos":[{"hechizo_id":str(hechizos_ids[7]),"nombre":"Stupefy"}],
            "eventos":[],
        },
        {
            "nombre":"Nymphadora Tonks",
            "fecha_nacimiento":datetime(1973,1,1),
            "rol":"Auror",
            "alineacion":"Bien",
            "casa":{"id":str(casa_map["Hufflepuff"]),"nombre":"Hufflepuff"},
            "peliculas_libros":[],
            "hechizos":[],
            "eventos":[{"evento_id":str(eventos_ids[0]),"nombre":"Batalla de Hogwarts","rol_en_evento":"Combatiente"}],
        },
        {
            "nombre":"Cedric Diggory",
            "fecha_nacimiento":datetime(1977,9,1),
            "rol":"Campeón",
            "alineacion":"Bien",
            "casa":{"id":str(casa_map["Hufflepuff"]),"nombre":"Hufflepuff"},
            "peliculas_libros":[],
            "hechizos":[{"hechizo_id":str(hechizos_ids[0]),"nombre":"Expelliarmus"}],
            "eventos":[{"evento_id":str(eventos_ids[1]),"nombre":"Torneo de los Tres Magos","rol_en_evento":"Campeón de Hufflepuff"}],
        },
    ]
    personajes_ids = db.personajes.insert_many(personajes).inserted_ids

    for personaje_id, personaje in zip(personajes_ids, personajes):
        for evento in personaje["eventos"]:
            db.eventos.update_one(
                {"_id": ObjectId(evento["evento_id"])},
                {"$addToSet": {"participantes": {
                    "personaje_id": str(personaje_id),
                    "nombre": personaje["nombre"],
                    "rol_en_evento": evento["rol_en_evento"],
                }}},
            )
        for obra in personaje["peliculas_libros"]:
            pelicula = db.peliculas_libros.find_one({"_id": ObjectId(obra["id"])})
            if pelicula:
                db.personajes.update_one(
                    {"_id": personaje_id, "peliculas_libros.id": obra["id"]},
                    {"$set": {"peliculas_libros.$.titulo": pelicula["titulo"]}},
                )
                db.peliculas_libros.update_one(
                    {"_id": pelicula["_id"]},
                    {"$addToSet": {"personajes": {"id": str(personaje_id), "nombre": personaje["nombre"]}}},
                )

    for pelicula_id in peliculas_ids[6:8]:
        pelicula = db.peliculas_libros.find_one({"_id": pelicula_id})
        db.peliculas_libros.update_one(
            {"_id": pelicula_id},
            {"$addToSet": {"eventos": {"id": str(eventos_ids[1]), "nombre": "Torneo de los Tres Magos"}}},
        )
        db.eventos.update_one(
            {"_id": eventos_ids[1]},
            {"$addToSet": {"peliculas_libros": {
                "id": str(pelicula_id), "titulo": pelicula["titulo"], "tipo": pelicula["tipo"],
            }}},
        )
    print(f"  + {len(personajes)} personajes")
    print("[MongoDB] OK")


def seed_cassandra():
    print("\n[Cassandra] Inicializando keyspace y tablas...")
    try:
        get_cassandra()
        print("[Cassandra] OK — keyspace y tablas creados")
    except Exception as e:
        print(f"[Cassandra] ERROR: {e}")


def seed_redis():
    print("\n[Redis] Probando conexión...")
    try:
        r = get_redis()
        r.ping()
        print("[Redis] OK")
    except Exception as e:
        print(f"[Redis] ERROR: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("  SEED — Harry Potter Polyglot DB")
    print("=" * 50)

    try:
        seed_supabase()
    except Exception as e:
        print(f"[Supabase] ERROR: {e}")

    try:
        seed_mongo()
    except Exception as e:
        print(f"[MongoDB] ERROR: {e}")

    seed_cassandra()
    seed_redis()

    print("\n" + "=" * 50)
    print("  Seed completado")
    print("=" * 50)
