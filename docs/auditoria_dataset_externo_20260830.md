# Auditoría del conjunto externo de búsquedas e hilos

## Objetivo

Se auditaron dos archivos JSONL recibidos por separado: uno con resultados directos de búsqueda y
otro con conversaciones reconstruidas. La auditoría no modifica los originales. Genera una copia
deduplicada, métricas temporales, control de raíces y padres, tablas por conversación y una salida
Parquet opcional.

El día de investigación se interpreta como el **19 de julio de 2026 en horario argentino
(America/Argentina/Buenos_Aires)**. Esta definición evita confundir una hora UTC con la hora local.

## Resultado principal

| Indicador | Resultado |
|---|---:|
| Resultados directos únicos | 1.415 |
| Tuits únicos incorporados desde hilos | 112.934 |
| Unión deduplicada | 113.048 |
| Solapamiento entre búsqueda e hilos | 1.301 |
| Tuits presentes sólo por expansión de hilos | 111.633 |
| Conversaciones reconstruidas | 1.212 |

El 98,7 % de la unión deduplicada procede de la expansión de conversaciones. Por eso, el total de
113.048 publicaciones **no debe presentarse como cantidad de resultados recuperados por la
búsqueda**. Es un corpus conversacional: combina semillas halladas por búsqueda con publicaciones
relacionadas que pueden ser anteriores, posteriores o no contener las palabras consultadas.

## Cobertura temporal y temática

- Sólo 13 resultados directos pertenecen al 19/07 en horario argentino.
- 1.395 resultados directos pertenecen al 20/07 en horario argentino.
- De los tuits de hilos, 2.405 pertenecen al 19/07 y 110.529 quedan fuera de ese día.
- El rango completo observado va del 9/06/2025 al 29/08/2026 en UTC.
- 91.962 tuits de hilos —81,4 %— no mencionan `Argentina` en su texto.

Esto no invalida el corpus de conversaciones. Lo vuelve útil para estudiar respuestas, difusión y
estructura de hilos, pero inadecuado para estimar por sí solo cuántas publicaciones devolvió X en
cada hora de la final. El archivo de resultados directos tampoco conserva consulta, ventana ni
ejecución de origen, por lo que no permite reconstruir con certeza el muestreo original.

## Integridad de conversaciones

- Las 1.212 conversaciones contienen su publicación raíz.
- En las 1.212, la raíz aparece como primer registro.
- No hay raíces ausentes en los archivos recibidos.
- Hay 102 respuestas, repartidas entre 95 conversaciones, cuyo padre intermedio no está incluido.
- La conversación más grande contiene 477 publicaciones y la mediana es 14.
- Las 100 conversaciones más grandes reúnen el 32,2 % de los tuits de hilos.

La ausencia de un padre intermedio no se corrige inventando una raíz. Se marca explícitamente para
que los análisis de estructura puedan excluir o tratar aparte esos enlaces incompletos.

## Cómo reproducir la auditoría

Desde el entorno virtual del proyecto:

~~~bash
x-research audit-external-jsonl \
  --tweets /ruta/a/tweets.jsonl \
  --threads /ruta/a/threads.jsonl \
  --output data/exports/auditoria_dataset_externo \
  --target-date 2026-07-19
~~~

Se generan:

- `summary.json`: resumen completo de controles y métricas;
- `tweets_clean.csv`: unión deduplicada con procedencia y estados de raíz/padre;
- `tweets_clean.parquet`: la misma tabla en un formato eficiente, si PyArrow está instalado;
- `conversations_audit.csv`: control de cada conversación;
- `conversation_concentration.csv`: concentración acumulada por tamaño;
- `hourly_all_observed.csv`: actividad observada por hora en todo el rango;
- `hourly_research_day_art.csv`: las 24 horas del día de investigación;
- `missing_roots.csv`: conversaciones sin raíz, si existieran.

Los archivos de datos quedan excluidos de Git. El repositorio público conserva el código, la
metodología y resultados agregados, pero no textos, usuarios ni identificadores del corpus.

## Prueba comparable propuesta

La configuración `config/comparacion_final_24h_2026.json` repite las cuatro consultas conocidas
durante las 24 horas del 19/07 ART. Divide cada consulta en ventanas de 15 minutos: 384 trabajos en
total. Cada trabajo guarda consulta, rango, estado, saturación y equipo; puede reanudarse y se
deduplica por ID.

Esta prueba permite comparar correctamente:

1. resultados directos por hora y consulta;
2. proporción de ventanas que alcanzan el límite;
3. solapamiento exacto de IDs con las semillas externas;
4. estabilidad, pausas y tiempo de ejecución;
5. diferencia entre búsqueda directa y expansión posterior de hilos.

La campaña completa de 43 días debe comenzar después de esta calibración. Si las ventanas de 15
minutos se saturan, se subdividen a 5 minutos antes de extrapolar volumen y tiempo.
