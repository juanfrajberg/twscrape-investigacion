# Recolección de X con twscrape

Repositorio independiente para probar `twscrape` como alternativa de recolección de
publicaciones públicas de X en el proyecto académico sobre conversaciones vinculadas con
Argentina durante el Mundial 2026.

El objetivo inmediato no es descargar una base masiva. Es ejecutar un piloto pequeño,
reproducible y medible que permita responder:

- si la búsqueda histórica funciona para las fechas elegidas;
- cuántos resultados únicos aparecen;
- qué campos se recuperan;
- si se pueden descargar respuestas;
- qué errores, bloqueos y tiempos aparecen;
- si una ejecución interrumpida puede repetirse sin duplicar la base.

## Estado

- Implementación del MVP: completa.
- Pruebas automáticas sin conexión a X: incluidas.
- Prueba real con una cuenta de X: completada el 24 de agosto de 2026.
- Resultado mínimo: 20 tuits únicos, sin avisos ni campos mínimos faltantes.

Una prueba sin conexión verifica el código y el esquema, pero no demuestra que X permita
descargar un período concreto. Esa conclusión sólo puede surgir del piloto real.

## Qué guarda

Para cada publicación se registran:

- ID, fecha, texto, idioma y URL;
- ID, usuario y nombre visible del autor;
- likes, retuits, respuestas, citas y visualizaciones;
- ID de conversación;
- ID y usuario del tuit respondido;
- ID y usuario del tuit citado;
- ID y usuario del tuit retuiteado;
- hashtags;
- consulta y trabajo mediante los cuales fue encontrada.

Las respuestas descargadas son publicaciones completas: conservan su texto, autor y vínculo con
el tuit padre.

## Estructura

```text
config/                         configuración del piloto
data/raw/                       registros JSONL (no se suben a Git)
data/exports/                   exportaciones CSV (no se suben a Git)
docs/                           protocolo y esquema
src/x_research/                 código fuente
tests/                          pruebas sin conexión
```

## 1. Preparar Python

Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[dev]"
```

La dependencia principal está fijada en `twscrape==0.20.0` para poder reproducir los resultados.

## 2. Validar el experimento sin conectarse a X

```bash
x-research validate-config
pytest
```

La configuración inicial está en `config/prueba_minima.json`: una consulta, un máximo de 20
resultados y sin descarga de respuestas. Las fechas se interpretan en la zona horaria indicada
por `timezone` (Buenos Aires de forma predeterminada). El programa las convierte a límites de
hora exactos y descarta cualquier resultado que X entregue fuera del período. Por ejemplo, desde
`2026-07-19` hasta `2026-07-20` incluye únicamente el 19 de julio en Argentina.

## 3. Agregar una sesión de X mediante cookies

`twscrape` necesita una cuenta autorizada. La opción recomendada por el proyecto es reutilizar
una sesión del navegador mediante las cookies `auth_token` y `ct0`.

```bash
twscrape --db data/accounts.db add_cookie cuenta_investigacion
```

El comando pedirá las cookies sin mostrarlas en pantalla. El formato es:

```text
auth_token=VALOR; ct0=VALOR
```

Después se puede comprobar el estado local de la cuenta:

```bash
twscrape --db data/accounts.db accounts
```

`data/accounts.db` contiene la sesión y está excluido de Git. Nunca debe compartirse, enviarse por
WhatsApp ni subirse al repositorio. Es preferible usar una cuenta aprobada para la investigación y
no una cuenta personal principal. `twscrape` usa una interfaz no oficial de X y existe riesgo de
bloqueo. El recolector desactiva por defecto la telemetría opcional de `twscrape`.

## 4. Ejecutar la prueba mínima

La primera ejecución busca sólo 20 publicaciones y no descarga respuestas:

```bash
x-research collect
```

Si esa prueba termina correctamente, ejecutar el piloto ampliado. Éste contiene dos consultas de
100 publicaciones y descarga hasta 25 respuestas de los 5 tuits con más respuestas:

```bash
x-research collect --config config/experimento.ejemplo.json
```

Resultados locales:

- `data/research.sqlite3`: base normalizada y estado de los trabajos;
- `data/raw/captures.jsonl`: registros capturados, uno por línea.

Los trabajos completados se omiten en la siguiente ejecución. Si un trabajo falla, puede volver a
ejecutarse: la búsqueda comienza nuevamente, pero SQLite evita insertar capturas duplicadas. No es
todavía una reanudación desde el cursor exacto de la última página.

Para repetir también trabajos completos:

```bash
x-research collect --force
```

## 5. Revisar y exportar

```bash
x-research summary
x-research audit
x-research export-csv
```

`audit` produce un resumen JSON con volumen, autores, fechas mínima y máxima en horario argentino,
campos faltantes, tipos de relación, capturas y estado de los trabajos. El CSV queda en
`data/exports/tweets.csv`. Los datos no se versionan automáticamente porque pueden contener
identificadores y nombres de usuarios.

Para unir bases recolectadas en computadoras diferentes:

```bash
x-research merge-db nodo-a.sqlite3 nodo-b.sqlite3 --database data/research.sqlite3
```

La unión conserva los trabajos y relaciones de cada nodo y evita duplicar publicaciones por ID.

## Cómo repartir una prueba entre computadoras

Cada integrante puede copiar la configuración y asignarse una combinación diferente de consulta y
fecha. Por ejemplo:

```text
computadora A → Argentina, 19 de julio
computadora B → "Argentina campeón", 19 de julio
computadora C → Argentina, 20 de julio
```

Cada combinación genera un identificador determinístico. Al terminar, `merge-db` permite combinar
las bases locales en una base común sin duplicar publicaciones.

## Alcance actual

Este repositorio prueba únicamente `twscrape`. No incluye TwitterAPI.io ni genera costos. Su salida
está normalizada para poder compararla posteriormente con una prueba de Twikit.

Ver también:

- `docs/protocolo_prueba.md`
- `docs/esquema_datos.md`
- `docs/resultados_prueba_minima.md`
- `docs/comparacion_alternativas.md`
- `docs/entregable_profesor.md`
