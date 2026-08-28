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

## Exportación de conversaciones

`x-research export-threads-csv` crea una tabla plana apta para análisis. Una fila representa una
publicación y todas las filas de la misma conversación comparten `conversation_id`.

El orden es:

1. `conversation_id`;
2. `thread_depth`;
3. fecha de publicación;
4. ID del tuit.

`thread_depth = 0` representa la raíz disponible, `1` una respuesta directa y los valores mayores
respuestas anidadas. `parent_in_dataset` y `root_in_dataset` indican si el padre y la raíz están
presentes en la base; esto evita interpretar como completo un hilo del que sólo se descargó una
parte.

El CSV incluye los campos solicitados para cada fila: ID, fecha, texto, autor, likes, retuits,
cantidad de respuestas, ID y usuario respondido e ID y usuario citado. `capture_kind` distingue
resultados encontrados por búsqueda de respuestas descargadas como contexto.

## `job_events`

Advertencias y errores asociados con cada trabajo. Permite saber si una ejecución marcada como
completa tuvo problemas al descargar respuestas particulares.
