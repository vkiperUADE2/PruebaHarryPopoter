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

Los RF21-RF24 usan sesiones Redis con token unico, TTL de una hora y validacion
en cada operacion protegida. Las consultas publicas validan el token cuando se
envia uno.

Los RF25-RF28 registran actividad y busquedas en Astra DB, permiten filtrar por
fecha y generan rankings globales diarios y personales en Redis.

## Consistencia y escalabilidad

- Las referencias relacionadas se actualizan al cambiar nombres.
- Las eliminaciones limpian relaciones o se bloquean si romperian referencias.
- Los rankings usan pipelines atomicos de Redis.
- Los errores de auditoria/ranking se registran en logs.
- Las listas tienen `skip` y `limit`, con un maximo de 100 registros.
- MongoDB y PostgreSQL definen indices para las consultas frecuentes.
- MongoDB, Redis y Astra DB son servicios administrados escalables.

## Seguridad

Las credenciales se leen desde `.env`, que esta ignorado por Git. Los usuarios
nuevos siempre reciben rol de usuario; solo un administrador puede escribir
contenido, gestionar asociaciones, roles o estados de usuarios.
