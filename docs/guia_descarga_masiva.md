# Guía de descarga masiva

Esta guía explica el recorrido completo, desde una computadora nueva hasta la exportación final.
Los comandos se ejecutan desde la raíz del repositorio.

## 1. Instalación

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[dev,mass]"
~~~

Verificar sin usar X:

~~~bash
pytest
x-research validate-campaign
~~~

## 2. Cuenta de X

Agregar las cookies de una sesión autorizada:

~~~bash
twscrape --db data/accounts.db add_cookie cuenta_investigacion
~~~

Pegar auth_token y ct0 en una sola línea:

~~~text
auth_token=VALOR; ct0=VALOR
~~~

Comprobar el estado:

~~~bash
twscrape --db data/accounts.db accounts
~~~

No compartir data/accounts.db.

## 3. Inspeccionar el plan sin descargar

~~~bash
x-research plan-campaign \
  --campaign config/campania_mundial_2026.json \
  --output data/plans/campania_mundial_2026.json
~~~

El archivo generado enumera cada combinación de consulta y ventana horaria. Es reproducible:
la misma configuración genera el mismo plan y los mismos identificadores de trabajo.

## 4. Piloto representativo

~~~bash
x-research collect \
  --config config/piloto_muestreo_mundial_2026.json \
  --database data/piloto_muestreo.sqlite3 \
  --raw-jsonl data/raw/piloto_muestreo.jsonl
~~~

Revisar:

~~~bash
x-research summary --database data/piloto_muestreo.sqlite3
x-research audit --database data/piloto_muestreo.sqlite3
~~~

Un trabajo con “saturado = sí” alcanzó su límite. Su cantidad no debe interpretarse como el total
de publicaciones del intervalo.

## 5. Ensayo de la campaña

No se deben ejecutar simplemente los tres primeros trabajos del plan: podrían corresponder a la
misma fecha o familia de consultas. Se calibran deliberadamente tres escenarios: una hora normal,
una hora de partido de Argentina y una hora de la final.

La hora normal se puede reproducir con:

~~~bash
x-research collect \
  --config config/prueba_hora_normal_mundial_2026.json \
  --database data/prueba_hora_normal.sqlite3 \
  --raw-jsonl data/raw/prueba_hora_normal.jsonl
~~~

Esta prueba recuperó 120 publicaciones entre las 12:00 y las 13:00 del 13 de junio, sin alcanzar
el límite de 1.000. Por lo tanto, una ventana de una hora resultó suficiente en ese caso.

Después de calibrar los tres escenarios, continuar con todos:

~~~bash
x-research collect-campaign \
  --campaign config/campania_mundial_2026.json \
  --database data/mundial_2026.sqlite3 \
  --raw-dir data/raw/mundial_2026 \
  --auto-refine
~~~

La opción --auto-refine divide en dos las ventanas saturadas y vuelve a intentarlo. Repite el
proceso hasta llegar a diez minutos o hasta que la búsqueda deje de alcanzar el límite.

## 6. Reanudar

Si el proceso se interrumpe, ejecutar exactamente el mismo comando. El programa:

1. omite los trabajos completos;
2. vuelve a comenzar los trabajos interrumpidos;
3. conserva las capturas anteriores;
4. evita insertar el mismo ID dos veces.

No existe reanudación desde el cursor exacto de X. La unidad de recuperación es el trabajo temporal,
por eso las ventanas son deliberadamente pequeñas.

## 7. Revisar cobertura

~~~bash
x-research summary --database data/mundial_2026.sqlite3
x-research audit --database data/mundial_2026.sqlite3
~~~

Antes de analizar:

- no debe haber trabajos running si no hay una descarga activa;
- los trabajos failed deben revisarse y reintentarse;
- las ventanas saturadas deben refinarse;
- el corpus principal debe analizarse separado del temático y de los hilos.

Para generar manualmente un plan sólo con ventanas saturadas:

~~~bash
x-research refine-plan \
  --config data/plans/campania_mundial_2026.json \
  --database data/mundial_2026.sqlite3 \
  --output data/plans/campania_mundial_2026_refinada.json
~~~

## 8. Descargar conversaciones

~~~bash
x-research expand-threads \
  --database data/mundial_2026.sqlite3 \
  --raw-dir data/raw/mundial_2026 \
  --top 200 \
  --minimum-replies 20 \
  --limit-per-thread 1000 \
  --auto-refine
~~~

La selección se hace sobre tuits raíz encontrados en el corpus principal. Para restringirla a una
familia:

~~~bash
x-research expand-threads \
  --database data/mundial_2026.sqlite3 \
  --raw-dir data/raw/mundial_2026 \
  --query-family partidos_argentina \
  --top 50 \
  --auto-refine
~~~

## 9. Exportar

CSV de todos los tuits:

~~~bash
x-research export-csv \
  --database data/mundial_2026.sqlite3 \
  --output data/exports/tweets.csv
~~~

CSV ordenado por conversación:

~~~bash
x-research export-threads-csv \
  --database data/mundial_2026.sqlite3 \
  --output data/exports/hilos.csv
~~~

Parquet para análisis masivo:

~~~bash
x-research export-parquet \
  --database data/mundial_2026.sqlite3 \
  --output data/parquet/mundial_2026_export_01
~~~

La carpeta de destino de Parquet debe estar vacía o no existir.

## 10. Repartir entre computadoras

Todos los nodos deben usar:

- la misma versión del repositorio;
- la misma configuración;
- el mismo valor de --shard-count;
- un --shard-index diferente, desde 0.

Ejemplo para seis nodos:

~~~bash
x-research collect-campaign \
  --database data/nodo_2.sqlite3 \
  --raw-dir data/raw/nodo_2 \
  --shard-count 6 \
  --shard-index 2 \
  --auto-refine
~~~

Unión final:

~~~bash
x-research merge-db \
  data/nodo_0.sqlite3 data/nodo_1.sqlite3 data/nodo_2.sqlite3 \
  data/nodo_3.sqlite3 data/nodo_4.sqlite3 data/nodo_5.sqlite3 \
  --database data/mundial_2026.sqlite3
~~~

## 11. Archivos que se comparten

Se pueden compartir:

- código;
- configuraciones;
- documentación;
- estadísticas agregadas;
- el hash del commit utilizado.

No se publican:

- cookies;
- accounts.db;
- bases SQLite;
- JSONL crudos;
- CSV o Parquet con usuarios y textos.
