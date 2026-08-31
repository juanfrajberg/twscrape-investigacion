# Auditoría del corpus ampliado de búsquedas e hilos

## Resumen

La nueva entrega contiene 13.699 registros devueltos por el flujo de búsqueda y 6.666
conversaciones reconstruidas. Dentro de esas conversaciones hay 477.477 publicaciones únicas. La
unión deduplicada alcanza 482.341 publicaciones.

| Capa | Publicaciones únicas |
|---|---:|
| Devueltas por búsqueda | 13.699 |
| Presentes en conversaciones | 477.477 |
| Sólo contexto de hilos | 468.642 |
| Unión deduplicada | 482.341 |

El 97,2 % de la unión aparece únicamente por expansión de hilos. Por lo tanto, 477.477 no es la
cantidad de resultados de una consulta: es el tamaño de la capa conversacional reconstruida.

## Cobertura temporal

El período de investigación se definió como el 19/07/2026 de 00:00 a 24:00 en
`America/Argentina/Buenos_Aires`.

- 1.360 resultados devueltos por búsqueda pertenecen al 19/07 ART.
- 10.704 pertenecen al 21/07 ART.
- 48.234 tuits de conversaciones pertenecen al 19/07 ART.
- 429.243 tuits de conversaciones —89,9 %— quedan fuera del día investigado.
- El rango total observado comienza en 2013 y termina el 29/08/2026.

Los archivos acumulan ejecuciones o períodos diferentes. Como cada fila no conserva el identificador
de ejecución, la consulta ni la ventana que la produjo, no es posible atribuir los 13.699 resultados
a una única búsqueda del día de la final.

La mayor concentración de resultados devueltos por búsqueda aparece entre las 21:00 y las 23:59
del 21/07 ART. Además, una hora expresada como `02:00 UTC` corresponde a `23:00 ART` del día
anterior; todos los análisis horarios deben normalizar primero la zona.

## Relevancia textual y contexto

De las publicaciones presentes en conversaciones, 393.903 —82,5 %— no contienen una mención
literal de Argentina. Dentro del día de investigación:

- 1.242 de los 1.360 resultados de búsqueda mencionan Argentina;
- 118 fueron devueltos por la búsqueda aunque su texto no la menciona;
- 9.288 de los 48.234 tuits de conversaciones mencionan Argentina;
- 38.946 no la mencionan.

“Devuelto por búsqueda” no equivale necesariamente a “coincide literalmente con la consulta”. La
respuesta de X puede incluir raíces o módulos conversacionales relacionados. Por eso la auditoría
incorpora dos controles separados: `corpus_role` identifica la procedencia y
`mentions_argentina` identifica la coincidencia textual mínima. La pertinencia sustantiva requiere
una etapa posterior de clasificación.

## Integridad de hilos

- Las 6.666 conversaciones contienen su raíz y la ubican en primer lugar.
- Hay 456 respuestas, distribuidas entre 425 conversaciones, cuyo padre intermedio no está presente.
- La conversación más grande contiene 477 publicaciones y la mediana es 8.
- Las 100 conversaciones más grandes reúnen 7,9 % de la capa de hilos.

Las raíces no relacionadas no se eliminan: se conservan como contexto, pero quedan separadas del
corpus analítico principal.

## Comparación parcial con la descarga estratificada

El 31/08 se comparó el archivo ampliado con nuestra campaña de ventanas de 15 minutos usando la
consulta `Argentina`. En las primeras cinco horas completas del 19/07 ART se obtuvo:

| Hora ART | Archivo ampliado | Descarga por ventanas | IDs compartidos |
|---|---:|---:|---:|
| 00:00 | 7 | 2.304 | 7 |
| 01:00 | 2 | 1.660 | 1 |
| 02:00 | 5 | 1.603 | 5 |
| 03:00 | 0 | 1.655 | 0 |
| 04:00 | 0 | 1.921 | 0 |
| **Total** | **14** | **9.143** | **13** |

Ninguna de las 20 ventanas completas alcanzó el límite de 1.000 publicaciones. La diferencia no
puede interpretarse como actividad inexistente en la madrugada: muestra que una búsqueda diaria
con límite global dejó casi todas esas horas sin cubrir. La campaña por ventanas conserva el rango
de cada trabajo y permite medir esta pérdida en vez de ocultarla.

La comparación seguirá cambiando mientras avanza la descarga. Debe volver a ejecutarse al terminar
las 24 horas antes de publicar cifras definitivas.

## Salidas de la auditoría

El comando `audit-external-jsonl` genera, además del resumen y la unión completa:

- `search_returns.csv`: todos los registros devueltos por el flujo de búsqueda;
- `search_returns_research_day_art.csv`: sólo los devueltos dentro del 19/07 ART;
- `top_engagement_review.csv`: 500 publicaciones de mayor interacción con indicadores de
  procedencia, fecha y mención textual;
- `tweets_clean.csv` y `tweets_clean.parquet`: unión deduplicada completa;
- controles horarios, de concentración, raíces y padres ausentes.

Los datos no se publican en Git. El repositorio contiene únicamente código, metodología y métricas
agregadas.

## Uso recomendado

1. Usar `search_returns_research_day_art.csv` como punto de partida del corpus del día.
2. Clasificar su relevancia sin depender sólo de una palabra literal.
3. Usar `corpus_role=thread_context_only` para análisis conversacional, no para estimar volumen de
   búsqueda.
4. Completar la comparación con la campaña estratificada en ventanas de 15 minutos.
5. En futuras descargas, guardar consulta, ejecución, ventana y cuenta de origen por cada captura.
