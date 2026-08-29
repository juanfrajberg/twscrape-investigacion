# Investigación de conversación sobre Argentina en X

Este repositorio permite recolectar publicaciones públicas de X con twscrape, registrar el
avance de una descarga grande, retomarla, repartirla entre computadoras y reconstruir hilos mediante
conversation_id.

El caso preparado es la conversación mundial y multilingüe sobre Argentina durante el Mundial
2026, desde el **9 de junio hasta el 21 de julio inclusive**. El corpus principal y las búsquedas
temáticas se guardan como capas diferentes para no distorsionar los análisis.

## Empezar en cinco pasos

### 1. Preparar el proyecto

~~~bash
git clone https://github.com/juanfrajberg/twscrape-investigacion.git
cd twscrape-investigacion
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[dev,mass]"
~~~

En Windows, la activación del entorno es:

~~~powershell
.venv\Scripts\activate
~~~

### 2. Comprobar el código sin conectarse a X

~~~bash
pytest
x-research validate-campaign
~~~

La validación debe informar 2.160 trabajos: 1.278 del corpus principal y 882 temáticos.

### 3. Agregar una sesión de X

~~~bash
twscrape --db data/accounts.db add_cookie cuenta_investigacion
~~~

Cuando lo pida, pegar las dos cookies juntas en una sola línea:

~~~text
auth_token=VALOR; ct0=VALOR
~~~

Luego comprobar la cuenta:

~~~bash
twscrape --db data/accounts.db accounts
~~~

El archivo data/accounts.db contiene credenciales y nunca se sube a Git.

### 4. Ejecutar primero el piloto

~~~bash
x-research collect \
  --config config/piloto_muestreo_mundial_2026.json \
  --database data/piloto_muestreo.sqlite3 \
  --raw-jsonl data/raw/piloto_muestreo.jsonl
~~~

El piloto toma tres franjas: un día normal, un partido de Argentina y la final.

~~~bash
x-research summary --database data/piloto_muestreo.sqlite3
x-research audit --database data/piloto_muestreo.sqlite3
~~~

### 5. Probar tres trabajos de la campaña completa

~~~bash
x-research collect-campaign \
  --campaign config/campania_mundial_2026.json \
  --database data/mundial_2026.sqlite3 \
  --raw-dir data/raw/mundial_2026 \
  --max-jobs 3
~~~

Si esos trabajos terminan bien, la campaña completa se ejecuta quitando --max-jobs 3 y
agregando --auto-refine:

~~~bash
x-research collect-campaign \
  --campaign config/campania_mundial_2026.json \
  --database data/mundial_2026.sqlite3 \
  --raw-dir data/raw/mundial_2026 \
  --auto-refine
~~~

Se puede interrumpir y volver a ejecutar el mismo comando. Los trabajos completos se omiten y los
interrumpidos se repiten sin duplicar publicaciones.

## Qué resuelve

- divide 43 días y diez familias de consultas en trabajos pequeños;
- usa ventanas de una hora en partidos y de 15 minutos alrededor de la final;
- marca una ventana como saturada cuando alcanza el máximo configurado;
- subdivide ventanas saturadas hasta diez minutos con --auto-refine;
- conserva la consulta, capa, período y computadora que encontró cada publicación;
- evita duplicados por ID;
- guarda perfiles y observaciones históricas de las cuentas;
- separa corpus principal, búsquedas temáticas e hilos;
- permite repartir el plan entre varias computadoras;
- exporta CSV para revisión y Parquet para análisis masivo.

## Descargar hilos

Después de reunir el corpus principal:

~~~bash
x-research expand-threads \
  --database data/mundial_2026.sqlite3 \
  --raw-dir data/raw/mundial_2026 \
  --top 200 \
  --minimum-replies 20 \
  --auto-refine
~~~

Este comando selecciona las 200 publicaciones raíz más respondidas de la capa principal y busca
su conversación completa mediante conversation_id. Los hilos que alcanzan el límite también se
subdividen por tiempo.

## Exportar

Para una revisión manejable:

~~~bash
x-research export-threads-csv \
  --database data/mundial_2026.sqlite3 \
  --output data/exports/hilos.csv
~~~

Para análisis de millones de registros:

~~~bash
x-research export-parquet \
  --database data/mundial_2026.sqlite3 \
  --output data/parquet/mundial_2026_export_01
~~~

La exportación Parquet crea publicaciones particionadas por fecha y capturas particionadas por capa
y familia de consulta.

Para preparar una muestra manual de contenidos y cuentas:

~~~bash
x-research export-annotation-sample \
  --database data/mundial_2026.sqlite3 \
  --output data/exports/muestra_etiquetado.csv \
  --per-layer 100
~~~

## Varias computadoras

Con cuatro nodos, cada persona usa un índice distinto:

~~~bash
x-research collect-campaign \
  --database data/nodo_0.sqlite3 \
  --raw-dir data/raw/nodo_0 \
  --shard-count 4 \
  --shard-index 0 \
  --auto-refine
~~~

Los otros nodos usan índices 1, 2 y 3. Al finalizar:

~~~bash
x-research merge-db \
  data/nodo_0.sqlite3 data/nodo_1.sqlite3 \
  data/nodo_2.sqlite3 data/nodo_3.sqlite3 \
  --database data/mundial_2026.sqlite3
~~~

## Documentación

- [Guía detallada de descarga masiva](docs/guia_descarga_masiva.md)
- [Protocolo de investigación del Mundial 2026](docs/protocolo_mundial_2026.md)
- [Etiquetado, ubicación y automatización](docs/etiquetado_y_limitaciones.md)
- [Esquema de datos](docs/esquema_datos.md)
- [Resultados del piloto de hilos](docs/resultados_piloto_hilos.md)
- [Resultados del piloto de muestreo temporal](docs/resultados_piloto_muestreo_20260829.md)
- [Evaluación general de twscrape](docs/informe_twscrape.md)

## Seguridad y alcance

twscrape usa interfaces no oficiales de X. Puede sufrir cambios, límites o bloqueos. Conviene
emplear cuentas autorizadas para la investigación y no una cuenta personal principal.

Las bases, cookies, textos, usuarios e identificadores reales están excluidos de Git. El repositorio
público contiene código, configuraciones, metodología y resultados agregados; no el corpus.
