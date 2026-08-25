# Esquema de datos

## `users`

Una fila por usuario. Se actualizan el nombre y el usuario visible cuando vuelve a aparecer.

## `tweets`

Una fila por ID de publicación. Incluye contenido, autor, métricas y referencias a respuesta, cita o
retuit. Las métricas se actualizan cuando el mismo ID vuelve a capturarse.

## `jobs`

Una fila por combinación de experimento, consulta y ventana temporal. Registra estado, intentos,
versión de `twscrape`, computadora, resultados, duplicados, advertencias y error final.

Estados posibles:

- `pending`: creado pero no iniciado;
- `running`: ejecución en curso;
- `completed`: finalizado;
- `failed`: interrumpido con error y apto para reintento.

## `captures`

Vincula un tuit con el trabajo que lo encontró. Distingue:

- `search`: resultado directo de la consulta;
- `reply`: respuesta descargada desde uno de los tuits seleccionados.

La restricción única impide duplicar la misma captura al repetir un trabajo.

## `relationships`

Aristas entre publicaciones:

- `reply`;
- `quote`;
- `retweet`.

Incluye, cuando están disponibles, los IDs y usuarios de origen y destino. Esta tabla se puede usar
posteriormente para construir un grafo.

## `job_events`

Advertencias y errores asociados con cada trabajo. Permite saber si una ejecución marcada como
completa tuvo problemas al descargar respuestas particulares.

