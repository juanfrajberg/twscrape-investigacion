# Resultado del piloto de conversaciones

## Configuración

- Fecha de ejecución: 28 de agosto de 2026.
- Herramienta: `twscrape 0.20.1`.
- Consulta: `"Argentina campeón" lang:es`.
- Ventana de búsqueda: 19 de julio de 2026 en horario argentino.
- Resultados de búsqueda exigidos: 100 IDs únicos.
- Tuits elegidos para descargar respuestas: los 5 con mayor `reply_count`.
- Límite por tuit elegido: 10 respuestas únicas.

La configuración reproducible está en [`config/piloto_hilos.json`](../config/piloto_hilos.json).

## Resultado de la descarga

| Medida | Valor |
|---|---:|
| Resultados de búsqueda | 100 |
| Respuestas adicionales descargadas | 50 |
| Publicaciones únicas totales | 150 |
| Autores únicos | 133 |
| Conversaciones distintas | 95 |
| Tuits seleccionados para respuestas | 5 |
| Tuits seleccionados presentes en la base | 5 |
| Duplicados controlados | 1 |
| Resultados de búsqueda fuera del período | 1 |
| Avisos | 0 |
| Campos mínimos faltantes | 0 |
| Relaciones de respuesta | 81 |
| Relaciones de cita | 11 |

Las respuestas pueden publicarse después de la ventana usada para encontrar el tuit inicial. Se
guardan porque forman parte de la conversación, pero se distinguen con `capture_kind = reply` para
no confundirlas con los resultados directos de la búsqueda temporal.

## Resultado del CSV de hilos

El archivo agrupado contiene 150 filas de datos y 25 columnas:

- 69 publicaciones de nivel `0`;
- 80 publicaciones de nivel `1`;
- 1 respuesta anidada de nivel `2`;
- 100 filas encontradas por búsqueda;
- 50 filas descargadas como respuestas.

Cada conversación se identifica con `conversation_id`. Dentro de cada grupo se ordena primero la
raíz disponible, después las respuestas directas, luego las respuestas anidadas y finalmente la
fecha y el ID.

El CSV incluye ID, fecha, texto, autor, likes, retuits, cantidad de respuestas, ID y usuario
respondido, ID y usuario citado, nivel, clase de captura y dos indicadores que informan si el padre
y la raíz están presentes en la base.

Los datos no se publican en Git porque contienen textos, nombres de usuario e identificadores. El
código, la configuración, la estructura y estas métricas sí quedan versionados.
