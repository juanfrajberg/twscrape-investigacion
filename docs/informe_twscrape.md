# Prueba de twscrape para armar la base de X

Última actualización: 29 de agosto de 2026.

## Qué se probó

Este repositorio evalúa `twscrape` como alternativa gratuita para buscar y guardar publicaciones
públicas de X. No es solamente un ejemplo de la librería: alrededor de `twscrape` se armó un
programa para definir consultas y períodos, guardar los datos, auditar los resultados, retomar
trabajos y combinar bases producidas en distintas computadoras.

La prueba real usó:

- consulta: `"Argentina campeón" lang:es`;
- período: 19 de julio de 2026, de 00:00 a 24:00 en horario argentino;
- producto de búsqueda: `Latest`;
- límite: 20 publicaciones;
- versión: `twscrape 0.20.0`;
- una cuenta de X autenticada con cookies;
- una computadora, sin proxy.

La configuración exacta está en [`config/prueba_minima.json`](../config/prueba_minima.json).

## Respuesta corta

`twscrape` llegó a funcionar en una prueba pequeña: devolvió las 20 publicaciones solicitadas,
con 20 IDs únicos y todos los campos mínimos presentes. También se comprobó que el programa puede
reconocer un trabajo ya terminado y evitar duplicarlo.

La prueba demuestra que `twscrape` puede recuperar los datos pedidos y que la estructura construida
alrededor de la librería sirve para organizar la base. Un piloto posterior amplió la muestra a 100
resultados y descargó 50 respuestas completas. El 29 de agosto se ejecutó además un muestreo
temporal de 300 publicaciones: día normal, partido y final. Las tres franjas alcanzaron el límite,
por lo que el sistema las marcó para subdivisión.

La hora normal se repitió luego con un límite de 1.000: se recuperaron 120 publicaciones únicas,
117 autores y ningún campo mínimo faltante. La ventana no quedó saturada, de modo que una hora es
suficiente para esa consulta y ese momento. Los escenarios de partido y final deben calibrarse por
separado.

La campaña completa del Mundial quedó definida en 2.160 trabajos reanudables: 1.278 del corpus
principal y 882 temáticos. Incluye reparto entre nodos, refinamiento automático, expansión por
`conversation_id`, metadatos de cuenta y exportación Parquet.

## Resultados de la prueba real

| Medida | Resultado |
|---|---:|
| Publicaciones solicitadas | 20 |
| Publicaciones obtenidas | 20 |
| IDs únicos | 20 |
| Autores únicos | 19 |
| Texto, autor o fecha faltantes | 0 |
| Métricas de interacción faltantes | 0 |
| Publicaciones que eran respuestas | 6 |
| Publicaciones que citaban otro tuit | 4 |
| Resultados fuera del período | 0 |
| Errores durante esa ejecución | 0 |
| Duración aproximada | 1,6 segundos |
| Primera fecha local | 19/07/2026 01:31:46 |
| Última fecha local | 19/07/2026 23:59:01 |

Estos números se obtuvieron con la auditoría incluida en el repositorio. La base real y las cookies
no se publican porque contienen identificadores de usuarios y una sesión privada.

## Respuesta a los seis puntos de evaluación

### 1. ¿Permite acceder al período que nos interesa?

Sí, al menos para la ventana que se probó. La búsqueda recuperó publicaciones históricas del 19 de
julio de 2026.

Para controlar el período de manera consistente, el programa:

1. interpreta las fechas en `America/Argentina/Buenos_Aires`;
2. las convierte a segundos Unix con hora exacta;
3. agrega `since_time` y `until_time` a la consulta;
4. vuelve a controlar localmente la fecha antes de guardar cada publicación.

El muestreo posterior confirmó acceso histórico en un día normal, un partido y la final. La
campaña completa conserva la misma validación para todos los intervalos.

### 2. ¿Cuántos resultados recupera y qué tan completa es la búsqueda?

Para la prueba mínima recuperó 20 de los 20 resultados solicitados. El muestreo temporal posterior
recuperó 100 de 100 en cada una de sus tres franjas. Todos los IDs fueron distintos dentro de cada
trabajo. Alcanzar el límite demuestra capacidad de recuperación, pero no que se hayan obtenido
todos los tuits existentes.

X no informa cuántos resultados totales existen para una búsqueda y no contamos con una base de
referencia completa. Por eso hay dos conceptos distintos:

- **cumplimiento del límite:** 20/20, medido;
- **cobertura respecto del total existente en X:** desconocida.

Para comparar cobertura entre alternativas hay que ejecutar la misma consulta, ventana horaria y
límite con cada herramienta. Después se pueden medir:

- cantidad de IDs únicos de cada opción;
- IDs presentes en ambas;
- IDs encontrados solamente por una;
- estabilidad de los resultados al repetir la consulta;
- coincidencia manual de fechas, textos y relaciones en una muestra.

El protocolo para hacer esa comparación está en
[`docs/protocolo_prueba.md`](protocolo_prueba.md).

### 3. ¿Qué límites, bloqueos o problemas de estabilidad aparecen?

En la ejecución exitosa de 20 publicaciones no apareció un rate limit ni un bloqueo de cuenta.
La muestra es demasiado pequeña para concluir que esos problemas no aparecerán a mayor escala.

Aunque no aparecieron en la muestra mínima, en una descarga mayor hay que controlar estos riesgos:

- cambios de la interfaz interna de X que rompen la librería sin aviso;
- rate limits por cuenta y por tipo de operación;
- sesiones que vencen y obligan a renovar cookies;
- verificaciones o bloqueos de las cuentas;
- resultados variables entre ejecuciones;
- límites propios de algunos endpoints;
- tiempos mucho mayores al descargar respuestas y paginar grandes volúmenes.

`twscrape` administra estados y rotación cuando una operación queda limitada. Como usa una interfaz
no oficial, conviene fijar la versión, trabajar con particiones pequeñas y auditar cada ejecución.

### 4. ¿Qué cuentas, cookies, proxies o credenciales requiere?

Para la forma probada se necesita:

- una cuenta de X con una sesión activa;
- las cookies `auth_token` y `ct0` copiadas desde esa sesión;
- una base local de cuentas de `twscrape`;
- ningún token de la API oficial;
- ningún proxy para una prueba pequeña.

Las cookies se guardan en `data/accounts.db`, un archivo excluido de Git. No deben enviarse por
mensajería, subirse al repositorio ni incluirse en una base compartida.

`twscrape` admite varias cuentas y permite asignar un proxy a cada cuenta. Eso puede ayudar a
repartir rate limits, pero también agrega costo, complejidad y riesgo de bloqueo. Para el piloto se
recomienda usar una cuenta autorizada para la investigación y no una cuenta personal principal.

### 5. ¿Cuánto costarían bases de distintos tamaños?

Las librerías `twscrape` y Twikit son gratuitas: el software cuesta USD 0 por tuit. Ese número no
incluye el costo indirecto de cuentas, proxies, almacenamiento, tiempo de ejecución y mantenimiento
cuando X cambia.

TwitterAPI.io publica una tarifa de USD 0,15 cada 1.000 tuits retornados. La API oficial de X publica
USD 0,005 por publicación leída, es decir, USD 5 cada 1.000. Con los precios consultados el 24 de
agosto de 2026:

| Publicaciones descargadas | twscrape / Twikit | TwitterAPI.io | API oficial de X |
|---:|---:|---:|---:|
| 1.000 | USD 0* | USD 0,15 | USD 5 |
| 10.000 | USD 0* | USD 1,50 | USD 50 |
| 100.000 | USD 0* | USD 15 | USD 500 |
| 1.000.000 | USD 0* | USD 150 | USD 5.000 |

\* Sin contar cuentas, proxies, infraestructura ni horas de mantenimiento.

La cuenta supone una lectura cobrada por cada tuit, incluidas las respuestas descargadas. En
TwitterAPI.io los perfiles consultados por separado cuestan USD 0,18 cada 1.000. En la API oficial,
una lectura separada de usuario cuesta USD 0,01. No siempre hace falta hacer una consulta de perfil
por cada tuit: depende de los campos que devuelva el endpoint elegido.

TwitterAPI.io no se probó porque este piloto no tiene presupuesto. Su cálculo es una estimación a
partir del precio publicado, no una medición del servicio. La API oficial tampoco se probó.

Fuentes de precios:

- [TwitterAPI.io Pricing](https://twitterapi.io/pricing)
- [X API: pay-per-use](https://docs.x.com/x-api/getting-started/pricing)

Los precios pueden cambiar y deben confirmarse antes de comprar créditos.

### 6. ¿Qué tan fácil es repartir la descarga entre computadoras?

El proyecto asigna automáticamente una parte determinística del plan a cada computadora mediante
`--shard-count` y `--shard-index`. Cada nodo trabaja sobre combinaciones distintas de:

- consulta;
- fecha o franja horaria;
- límite de resultados.

Ejemplo con cuatro nodos:

```text
nodo 0 → --shard-count 4 --shard-index 0
nodo 1 → --shard-count 4 --shard-index 1
nodo 2 → --shard-count 4 --shard-index 2
nodo 3 → --shard-count 4 --shard-index 3
```

Cada combinación genera un identificador estable. La base registra el estado del trabajo, la
computadora, la cantidad obtenida, duplicados, avisos y errores. Luego las bases se unen con:

```bash
x-research merge-db nodo-a.sqlite3 nodo-b.sqlite3 --database data/research.sqlite3
```

La unión conserva una sola copia de cada tuit por ID y mantiene las capturas, relaciones y trabajos.
Para que la coordinación sea clara, no conviene asignar la misma partición a dos nodos salvo que se
quiera medir estabilidad deliberadamente.

La configuración acepta tanto días completos (`2026-07-19`) como horas locales
(`2026-07-19T06:00:00`). Hay un ejemplo listo en
[`config/franja_horaria.ejemplo.json`](../config/franja_horaria.ejemplo.json).

## ¿Se guardan todos los campos pedidos?

| Campo pedido | Cómo se guarda | Estado |
|---|---|---|
| ID y fecha | `tweet_id`, `created_at` | Probado en vivo |
| Texto | `text` | Probado en vivo |
| Usuario | ID, nombre de usuario y nombre visible | Probado en vivo |
| Likes | `like_count` | Probado en vivo |
| Retuits | `retweet_count` | Probado en vivo |
| Cantidad de respuestas | `reply_count` | Probado en vivo |
| Texto y usuario de las respuestas | Cada respuesta se guarda como un tuit completo | Probado en vivo con 50 respuestas |
| ID del tuit respondido | `reply_to_tweet_id` y relación `reply` | Probado en vivo para tuits encontrados por búsqueda |
| ID del tuit citado | `quoted_tweet_id` y relación `quote` | Probado en vivo |

Además se guardan idioma, URL, visualizaciones, cantidad de citas, conversación, hashtags,
menciones, enlaces, medios, lugar adjunto, metadatos del perfil, consulta de origen, capa y momento
de captura.

## ¿Cómo se retoman descargas y se evitan duplicados?

Cada consulta y período se registra como un trabajo con estado `running`, `completed` o `failed`.

- Si ya está completo, la ejecución siguiente lo omite.
- Si falló o quedó interrumpido, se puede ejecutar nuevamente.
- Los IDs únicos de SQLite evitan duplicar tuits.
- Una auditoría informa trabajos completos, fallidos y pendientes.
- Los eventos guardan los errores para poder diagnosticar cada nodo.

La reanudación actual vuelve a comenzar la partición fallida y conserva lo ya almacenado; todavía
no continúa desde el cursor exacto de la última página. Por eso conviene usar particiones pequeñas,
por ejemplo intervalos de una o seis horas, en lugar de asignar meses completos a un solo trabajo.

## Comparación de alternativas

| Criterio | Twikit | twscrape | TwitterAPI.io | API oficial de X |
|---|---|---|---|---|
| Costo directo | Gratuito | Gratuito | USD 0,15/1.000 tuits | USD 5/1.000 publicaciones |
| API key | No | No | Sí, propia del servicio | Sí, de X |
| Cuenta de X propia | Sí | Sí | No | Cuenta de desarrollador |
| Cookies | Sí | Sí | No | No para autenticación de aplicación |
| Búsqueda | Sí | Sí | Sí | Sí, según endpoint y acceso |
| Respuestas | La librería ofrece acceso | `tweet_replies`, integrado en este proyecto | Servicio administrado | Endpoints oficiales según acceso |
| Varias cuentas/proxies | Hay que organizarlo en el cliente | Pool y proxies incorporados | Lo administra el proveedor | No se trabaja con cuentas de scraping |
| Rate limits | Hay que gestionarlos | Rotación por cuenta y endpoint | Los gestiona el proveedor | Definidos por la API oficial |
| Riesgo principal | Cambios internos de X y bloqueos | Cambios internos de X y bloqueos | Costo y dependencia de un tercero | Costo bastante mayor |
| Prueba en este repositorio | No | Sí | No | No |

Twikit debe compararse con los mismos parámetros antes de decidir cuál de las dos alternativas
gratuitas tiene mejor cobertura. En este repositorio no se atribuyen resultados prácticos a Twikit
porque no se ejecutó aquí.

Más detalle: [`docs/comparacion_alternativas.md`](comparacion_alternativas.md).

## Estimación de tiempos

La única velocidad medida fue 20 publicaciones en aproximadamente 1,6 segundos, equivalente a
12,5 publicaciones por segundo en una búsqueda muy pequeña. Esa velocidad no se puede extrapolar de
manera directa: una descarga real tendrá paginación, pausas, rate limits, reintentos y respuestas.

Usando un margen de seguridad de 5 a 10 veces sobre la medición inicial:

| Tamaño | Tiempo orientativo con una cuenta |
|---:|---:|
| 1.000 | 1–15 minutos |
| 10.000 | 15 minutos–2,5 horas |
| 100.000 | 11–22 horas |
| 1.000.000 | 5–10 días |

Son rangos para planificar, no tiempos medidos. Descargar conversaciones completas puede aumentar
mucho el total.

Para obtener una estimación defendible hay que medir primero:

1. 1.000 tuits sin respuestas;
2. 1.000 tuits con un límite controlado de respuestas;
3. la misma prueba dos veces para calcular estabilidad y duplicación;
4. al menos dos cuentas o dos computadoras si se piensa distribuir.

## Recomendación concreta

1. **Usar la campaña preparada de forma gradual.** Comenzar con pocos trabajos, revisar saturación
   y recién después ejecutar los 2.160 trabajos con refinamiento automático.
2. **Mantener separadas las tres capas.** El corpus principal sirve para prevalencia y picos; las
   búsquedas temáticas y los hilos para recuperación de casos y redes.
3. **Comparar Twikit y `twscrape` con exactamente la misma consulta y período.** La opción gratuita
   recomendada debe ser la que muestre mayor estabilidad y superposición de IDs en varias
   repeticiones, no la que tenga más funciones en la documentación.
4. **Partir el trabajo por consulta y franjas cortas**, guardar una base por nodo y unirlas al final.
5. **Mantener TwitterAPI.io como plan alternativo si hay una fecha límite.** A los precios actuales,
   100.000 tuits costarían alrededor de USD 15 y un millón, USD 150, antes de consultas adicionales.
6. **No elegir la API oficial para una descarga grande salvo que se necesiten garantías o campos
   exclusivos.** Su costo publicado de lectura es unas 33 veces mayor que TwitterAPI.io.
7. **Acordar antes de la descarga qué datos personales se compartirán.** Las cookies nunca deben
   circular y conviene revisar las reglas éticas e institucionales para almacenar nombres de
   usuario, textos y relaciones.

## Estado de lo pedido

| Pedido | Estado |
|---|---|
| Comparación breve | Incluida, con cuatro alternativas |
| Una solución funcionando | Pilotos reales de 150 registros con hilos, 300 publicaciones temporales y una hora ampliada de 120 |
| Prueba por consulta y período | Realizada y documentada |
| Campos mínimos | Guardados y validados, incluidas 50 respuestas completas |
| Evaluación de acceso histórico | Confirmada en día normal, partido y final |
| Cantidad y completitud | 300/300 en el piloto inicial; la hora normal ampliada recuperó 120/1.000 y no se saturó |
| Límites y estabilidad | Saturación detectada y refinamiento temporal implementado |
| Cuentas, cookies y proxies | Documentados |
| Costos | Estimados para cuatro tamaños y dos opciones pagas |
| Tiempos | Medición pequeña y rangos de planificación incluidos |
| Distribución | Reparto automático por nodo, estados y unión de bases implementados |
| Reanudación | Por trabajo completo; no todavía desde cursor de página |
| Duplicados | Controlados por ID y por captura |
| Recomendación | Ejecutar la campaña gratuita por etapas y conservar un plan pago alternativo |
| Código e instrucciones | Publicados en este repositorio |

## Cómo reproducirlo

Las instrucciones completas están en el [`README`](../README.md). El recorrido básico es:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[dev,mass]"
x-research validate-campaign
pytest
x-research collect --config config/piloto_muestreo_mundial_2026.json
x-research summary
x-research audit
x-research plan-campaign
```

Fuentes técnicas principales:

- [twscrape](https://github.com/vladkens/twscrape)
- [Twikit](https://github.com/d60/twikit)
- [TwitterAPI.io](https://twitterapi.io/pricing)
- [API oficial de X](https://docs.x.com/x-api/getting-started/pricing)
