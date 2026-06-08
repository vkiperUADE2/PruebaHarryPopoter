# Cumplimiento de requisitos

## Descripcion

La aplicacion permite registrar usuarios, explorar y administrar el universo de
Harry Potter, buscar contenido, relacionar personajes con eventos y obras,
registrar actividad y generar rankings.

## Bases de datos

- Supabase/PostgreSQL: usuarios y roles con claves unicas y foraneas.
- MongoDB: personajes, casas, hechizos, eventos, peliculas/libros y objetos.
- Redis: sesiones con TTL y rankings atomicos.
- Cassandra/Astra DB: actividad y busquedas de usuarios.

## Requisitos funcionales

Los RF1-RF4 se implementan en `/auth`: registro, login, gestion de roles y
usuarios, integridad relacional y contrasenas hasheadas.

Los RF5-RF20 se implementan en `/universo`: CRUD validado para las seis
categorias, consultas paginadas, busqueda individual/global, asociaciones
bidireccionales y autorizacion exclusiva para administradores.

La interfaz ofrece buscadores, detalles y paginacion para las seis categorias.
La busqueda incluye campos relacionados como casa, rol, alineacion,
participantes, fundador, valores, personajes y eventos.

Los RF21-RF24 usan sesiones Redis con token unico, TTL de una hora y validacion
en cada operacion protegida. Las consultas publicas validan el token cuando se
envia uno.

Los RF25-RF28 registran actividad y busquedas en Astra DB, permiten filtrar por
fecha y generan rankings globales diarios y personales en Redis.

## Consistencia y escalabilidad

- Las referencias relacionadas se actualizan al cambiar nombres.
- Al crear o modificar personajes se valida que la casa y los hechizos existan,
  y se guardan sus nombres canonicos directamente desde MongoDB.
- Las eliminaciones limpian relaciones o se bloquean si romperian referencias.
- Las asociaciones bidireccionales compensan la primera escritura si falla la segunda.
- Peliculas/libros y eventos tambien pueden relacionarse entre si.
- Los rankings usan pipelines atomicos de Redis.
- Los rankings muestran nombre y categoria, no identificadores internos.
- Los errores de auditoria/ranking se registran en logs.
- Las listas tienen `skip` y `limit`, con un maximo de 100 registros.
- MongoDB y PostgreSQL definen indices para las consultas frecuentes.
- MongoDB, Redis y Astra DB son servicios administrados escalables.
- El frontend pagina los resultados y la API limita cada pagina a 100 registros.
- Los indices de MongoDB se verifican una sola vez por proceso.
- Las operaciones sincronicas de base de datos se ejecutan en el thread pool de
  FastAPI para no bloquear el servidor durante solicitudes concurrentes.
- Se incluye una auditoria automatizada de referencias y una prueba de carga
  concurrente reproducible.

## Verificacion

Ejecutar las pruebas de contrato con:

```bash
python -m unittest discover -s tests -v
```

Para reparar referencias inversas en datos existentes sin borrar colecciones:

```bash
python backend/seed/repair_relations.py
```

Para comprobar que no existan referencias rotas:

```bash
python backend/seed/audit_consistency.py
```

Para medir concurrencia y tasa de errores contra el servidor local:

```bash
python scripts/load_test.py --requests 100 --concurrency 10
```

La consistencia entre motores distintos es eventual: MongoDB conserva las
relaciones del dominio, mientras Redis y Cassandra reciben rankings y auditoria
en segundo plano. Si un servicio auxiliar falla, el error queda registrado sin
corromper la operacion principal.

## Seguridad

Las credenciales se leen desde `.env`, que esta ignorado por Git. Los usuarios
nuevos siempre reciben rol de usuario; solo un administrador puede escribir
contenido, gestionar asociaciones, roles o estados de usuarios.
