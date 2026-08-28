# Resultado del piloto de 100 publicaciones

## Configuración

- Fecha de ejecución: 28 de agosto de 2026.
- Herramienta: `twscrape 0.20.1`.
- Consulta: `"Argentina campeón" lang:es`.
- Ventana: 19 de julio de 2026, de 00:00 a 24:00 en
  `America/Argentina/Buenos_Aires`.
- Objetivo: 100 IDs únicos.
- Descarga adicional de respuestas: desactivada para mantener el total en 100.

La configuración reproducible está en [`config/piloto_100.json`](../config/piloto_100.json).

## Resultado

| Medida | Valor |
|---|---:|
| Publicaciones únicas | 100 |
| Autores únicos | 84 |
| Duplicados detectados durante la paginación | 1 |
| Resultados descartados por estar fuera del período | 1 |
| Avisos | 0 |
| Texto, autor o fecha faltantes | 0 |
| Métricas de interacción faltantes | 0 |
| Publicaciones que eran respuestas | 31 |
| Publicaciones que citaban otro tuit | 10 |
| Duración aproximada de la descarga | 5 segundos |
| Primera fecha local | 19/07/2026 01:31:46 |
| Última fecha local | 19/07/2026 23:59:01 |

La primera ejecución del piloto recibió 100 elementos, pero uno repetía un ID y la base contenía
99 publicaciones únicas. A partir de ese hallazgo se corrigió el recolector: ahora los duplicados
no consumen el límite y la paginación continúa hasta reunir la cantidad solicitada de IDs únicos.
La corrección tiene una prueba automática específica.

## Interpretación

El piloto confirma que `twscrape 0.20.1` puede recuperar 100 publicaciones únicas para la consulta
y el período elegidos, guardando todos los campos mínimos evaluados. Las 31 respuestas de la tabla
son publicaciones que aparecieron directamente en la búsqueda. Este piloto no recorrió las
conversaciones para descargar respuestas adicionales. Esa validación se realizó después y está
documentada en [`resultados_piloto_hilos.md`](resultados_piloto_hilos.md).

El CSV contiene 100 filas de datos y 26 columnas. Los datos y las cookies permanecen fuera de Git
porque incluyen identificadores, textos y nombres de usuario.
