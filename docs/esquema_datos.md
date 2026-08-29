# Esquema de datos

La base SQLite cumple dos funciones: almacenar el corpus normalizado y registrar el estado de la
descarga. Los datos crudos se conservan además en JSONL separados por trabajo.

## users

Una fila actual por usuario. Incluye:

- ID, nombre de usuario y nombre visible;
- biografía, ubicación autodeclarada y fecha de creación;
- seguidores, seguidos, publicaciones, favoritos, listas y medios;
- cuenta protegida, verificación tradicional y verificación paga;
- imagen de perfil;
- primera y última observación.

Los datos describen lo que X devolvió en el momento de captura. No prueban la identidad ni la
ubicación real de la persona.

## user_snapshots

Una observación por usuario y día. Permite estudiar cambios del perfil o de sus contadores sin
sobrescribir completamente el pasado.

## tweets

Una fila por ID de publicación. Incluye:

- ID, fecha, texto, idioma y URL;
- ID del autor;
- likes, retuits, respuestas, citas y visualizaciones;
- conversation_id;
- tuit y usuario respondido;
- tuit y usuario citado;
- tuit y usuario retuiteado;
- hashtags, cashtags, menciones y enlaces;
- tipo y URL de fotos, videos o GIF;
- etiqueta de cliente, contenido sensible y lugar adjunto;
- fecha de captura y proveedor.

Las métricas se actualizan cuando el mismo ID vuelve a observarse.

## jobs

Una fila por combinación de experimento, consulta y ventana temporal. Registra:

- familia de consulta;
- capa del corpus;
- límites temporales;
- consulta completa;
- computadora y versión de twscrape;
- intentos, resultados, duplicados y avisos;
- estado final;
- indicador de saturación.

Estados:

- pending: creado pero no iniciado;
- running: ejecución en curso;
- completed: finalizado;
- failed: finalizado con error y apto para reintento.

Saturated igual a 1 significa que la búsqueda alcanzó el máximo configurado. Esa ventana puede
estar truncada y debe subdividirse.

## captures

Vincula una publicación con cada trabajo que la encontró. Esto mantiene separada la publicación de
su procedencia y permite que el mismo ID pertenezca a varias consultas sin duplicar tweets.

Tipos:

- search: resultado directo o raíz de una conversación;
- reply: publicación encontrada dentro de una expansión de hilo.

Las capas se obtienen desde el trabajo:

- core: corpus principal para volumen y prevalencia;
- thematic: búsquedas orientadas a narrativas;
- thread: expansión de conversaciones.

## relationships

Aristas entre publicaciones:

- reply;
- quote;
- retweet.

Incluyen los IDs de publicación y usuario disponibles. Esta tabla permite construir grafos de
respuestas, citas y amplificación.

## job_events

Advertencias, información y errores asociados con cada trabajo. Conserva el motivo de descartes,
fallos de X y ventanas saturadas.

## JSONL crudo normalizado

Las campañas guardan un archivo por trabajo:

~~~text
data/raw/campaign/EXPERIMENTO/FAMILIA/JOB_ID.jsonl
~~~

Cada registro incluye experimento, trabajo, familia, capa, consulta completa, tipo de captura,
conversation_id raíz y todos los campos normalizados.

## CSV de conversaciones

El comando export-threads-csv crea una fila por publicación y ordena por:

1. conversation_id;
2. profundidad del hilo;
3. fecha;
4. ID.

Thread_depth igual a 0 representa la raíz disponible. Parent_in_dataset y root_in_dataset indican
si el padre y la raíz están presentes; un valor 0 evita interpretar un hilo parcial como completo.

## Parquet

El comando export-parquet produce:

~~~text
tweets/date=AAAA-MM-DD/part-00000.parquet
captures/layer=CAPA/family=FAMILIA/part-00000.parquet
users.parquet
user_snapshots.parquet
relationships.parquet
jobs.parquet
job_events.parquet
~~~

Tweets queda deduplicado por ID. Captures conserva la relación de muchos a muchos entre
publicaciones, consultas y capas.
