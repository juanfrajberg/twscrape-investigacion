# Entregable técnico: alternativas para recolectar publicaciones de X

Actualizado el 24 de agosto de 2026.

## 1. Resultado ejecutivo

Se implementó y publicó una solución reproducible basada en `twscrape`. La primera prueba real
recuperó 20 de 20 publicaciones históricas del 19 de julio de 2026, con 19 autores, sin campos
mínimos faltantes y sin resultados fuera del día argentino. La repetición inmediata fue reconocida
como trabajo ya completo y no duplicó datos.

Una prueba posterior destinada a descargar respuestas detectó una inestabilidad externa:
`twscrape` no pudo interpretar los scripts que X servía en ese momento (`XClIdParseError`). El
programa ahora detecta el resultado vacío, marca el trabajo como fallido y permite reintentarlo, en
lugar de informar un éxito falso.

## 2. Solución implementada

El repositorio incluye:

- consultas configurables por texto, fecha, zona horaria y límite;
- límites horarios exactos y validación local del período;
- normalización de publicaciones, usuarios, métricas y relaciones;
- descarga opcional y acotada de respuestas completas;
- salida RAW en JSONL y base normalizada en SQLite;
- identificadores determinísticos de trabajo y estados `running`, `completed` y `failed`;
- reintentos sin perder datos y deduplicación por ID;
- auditoría automática de volumen, fechas, campos y relaciones;
- exportación CSV;
- unión de bases recolectadas por distintas computadoras;
- nueve tests automáticos sin conexión a X.

## 3. Campos guardados

- ID y fecha de publicación;
- texto e idioma;
- ID, usuario y nombre visible del autor;
- likes, retuits, respuestas, citas y visualizaciones;
- ID de conversación;
- ID y usuario del tuit respondido;
- ID y usuario del tuit citado;
- ID y usuario del tuit retuiteado;
- hashtags, consulta, trabajo y tipo de captura;
- texto y usuario de las respuestas que se descarguen como contexto.

## 4. Comparación breve

| Alternativa | Ventaja principal | Limitación principal | Estado |
|---|---|---|---|
| Twikit | Gratuita, búsqueda sin API oficial | Autenticación, límites y reanudación deben resolverse en el cliente | Sin piloto real reproducible |
| twscrape | Pool de cuentas, cookies, proxies y rate limits incorporados | Puede romperse cuando X cambia su interfaz interna | Piloto real completado; inestabilidad posterior documentada |
| TwitterAPI.io | API simple, infraestructura administrada y costo bajo | Servicio pago y dependencia de un tercero | Evaluación de precio; no probado |

Detalles y fuentes: [`comparacion_alternativas.md`](comparacion_alternativas.md).

## 5. Resultados medidos

| Métrica | Prueba mínima exitosa |
|---|---:|
| Límite solicitado | 20 |
| Publicaciones obtenidas | 20 |
| IDs únicos | 20 |
| Autores únicos | 19 |
| Campos mínimos faltantes | 0 |
| Publicaciones que eran respuestas | 6 |
| Publicaciones que eran citas | 4 |
| Avisos | 0 |
| Duración de la búsqueda | aproximadamente 1,6 segundos |
| Fecha local mínima | 19/07/2026 01:31:46 |
| Fecha local máxima | 19/07/2026 23:59:01 |

La muestra demuestra acceso histórico y funcionamiento, pero no permite afirmar que la búsqueda sea
completa respecto de todo X.

## 6. Costos

`Twikit` y `twscrape` no cobran por publicación. El costo monetario directo del software es USD 0,
pero requieren cuentas propias y tiempo operativo; además existe riesgo de rate limits o bloqueo.

TwitterAPI.io publica un precio de USD 0,15 por 1.000 tuits retornados, sin gasto mínimo. Con esa
tarifa, y sin contar consultas adicionales de perfiles, la estimación es:

| Tamaño | Costo estimado |
|---:|---:|
| 1.000 tuits | USD 0,15 |
| 10.000 tuits | USD 1,50 |
| 100.000 tuits | USD 15,00 |
| 1.000.000 tuits | USD 150,00 |

Si se consultara por separado un perfil por cada tuit, el precio publicado de USD 0,18 por 1.000
perfiles elevaría el total teórico a USD 0,33 por cada 1.000 pares tuit-perfil. Las respuestas también
cuentan como tuits retornados. La página anuncia USD 0,10 de crédito inicial, que equivaldría a unos
666 tuits a la tarifa base. Los precios deben reconfirmarse antes de comprar créditos.

Fuente: [TwitterAPI.io Pricing](https://twitterapi.io/pricing).

## 7. Estimación de tiempos

La única medición exitosa fue de 20 publicaciones en aproximadamente 1,6 segundos: unos 12,5 tuits
por segundo en una página pequeña. Una extrapolación lineal optimista daría alrededor de 2,2 horas
para 100.000 tuits, pero no es una previsión confiable porque ignora paginación, rate limits, esperas,
caídas y respuestas.

Para planificación se recomienda aplicar un factor de seguridad de 5 a 10 sobre esa extrapolación:

| Tamaño | Escenario operativo orientativo con una cuenta |
|---:|---:|
| 1.000 | 1–15 minutos |
| 10.000 | 15 minutos–2,5 horas |
| 100.000 | 11–22 horas |
| 1.000.000 | 5–10 días |

Estos rangos son supuestos de planificación, no mediciones. La inestabilidad observada muestra que
el tiempo calendario puede estar dominado por pausas hasta que la librería se adapte a X. Antes de
una descarga masiva hace falta un piloto de al menos 1.000 publicaciones.

## 8. Distribución entre computadoras

Cada nodo puede recibir una combinación diferente de consulta, fecha y horario. El identificador de
trabajo evita confundir particiones, SQLite registra qué terminó y las restricciones únicas evitan
duplicados dentro de cada base.

Al finalizar, las bases pueden unirse con:

```bash
x-research merge-db nodo-a.sqlite3 nodo-b.sqlite3 --database data/research.sqlite3
```

La unión preserva trabajos, capturas y relaciones y guarda una sola copia de cada publicación por ID.
La reanudación actual vuelve a recorrer una consulta fallida y deduplica lo ya guardado; todavía no
retoma desde el cursor exacto de la última página.

## 9. Recomendación

1. Mantener `twscrape` como opción gratuita de piloto porque ya produjo una muestra válida y el
   proyecto agrega controles que la librería no trae por sí sola.
2. No iniciar todavía una descarga masiva: esperar o corregir el fallo actual de scripts de X y
   completar un piloto de 1.000 publicaciones con respuestas.
3. Usar particiones pequeñas, auditoría después de cada ejecución y copias separadas por nodo.
4. Si la inestabilidad persiste o el plazo es prioritario, usar TwitterAPI.io: 100.000 tuits tendrían
   un costo base aproximado de USD 15, sujeto a verificación.
5. Conservar Twikit como comparación independiente, usando exactamente consultas, fechas y métricas
   equivalentes antes de sacar conclusiones de cobertura.

## 10. Reproducción rápida

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[dev]"
x-research validate-config
pytest
x-research collect
x-research summary
x-research audit
x-research export-csv
```

Las cookies, bases y exportaciones están excluidas del repositorio y nunca deben compartirse.
