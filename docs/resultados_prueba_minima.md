# Resultado de la prueba mínima

## Resumen

- Fecha de ejecución: 24 de agosto de 2026.
- Herramienta: `twscrape 0.20.0`.
- Entorno: Python 3.13.2 en macOS.
- Consulta: `"Argentina campeón" lang:es`.
- Ventana: 19 de julio de 2026, de 00:00 a 24:00 en
  `America/Argentina/Buenos_Aires`.
- Límite solicitado: 20 publicaciones.
- Resultado: 20 obtenidas y 20 IDs únicos.
- Duración de la descarga: aproximadamente 1,6 segundos.
- Avisos o errores: 0.
- Resultados descartados por estar fuera del período: 0.

## Calidad de los datos

- Autores únicos: 19.
- Fecha local mínima: 19 de julio de 2026, 01:31:46.
- Fecha local máxima: 19 de julio de 2026, 23:59:01.
- Registros sin texto, autor o fecha: 0.
- Registros sin métricas de likes, retuits o respuestas: 0.
- Publicaciones que son respuestas: 6.
- Publicaciones que citan otro tuit: 4.
- Retuits detectados: 0.

La prueba mínima no descargó las respuestas de las conversaciones porque esa opción está
desactivada deliberadamente en su configuración. El piloto ampliado sí permite hacerlo.

## Reanudación y duplicados

Una segunda ejecución con la misma configuración reconoció que el trabajo ya estaba completo y lo
omitió. SQLite mantiene IDs únicos y evita insertar dos veces una misma captura. Para repetir un
trabajo terminado de manera intencional se puede usar `--force`.

## Hallazgo sobre las fechas

Una primera prueba con los operadores de fecha simples de X devolvió publicaciones del 20 de julio
en horario argentino. Se conservó localmente como diagnóstico y no se mezcló con el resultado
válido. El recolector ahora convierte las fechas a límites horarios Unix exactos y además verifica
localmente la fecha de cada publicación antes de guardarla.

## Interpretación

Este resultado confirma que la cuenta y las cookies permiten ejecutar una búsqueda histórica breve,
que los campos mínimos se guardan y que la ejecución puede repetirse sin duplicar datos. No permite
afirmar que se recuperaron todas las publicaciones existentes para la consulta: para evaluar la
completitud y la estabilidad hay que repetir y ampliar el piloto.

Las cookies y las bases descargadas están excluidas de Git y no deben publicarse.

## Prueba posterior de estabilidad y respuestas

Más tarde el mismo 24 de agosto se intentó repetir la búsqueda con descarga de hasta 20 respuestas.
X había cambiado la forma de servir sus scripts y `twscrape 0.20.0` informó
`XClIdParseError: X web scripts not found`, tanto con el backend HTTP normal como con el backend de
huella de navegador. No se obtuvieron publicaciones en esos intentos.

Este resultado no invalida la descarga exitosa anterior, pero demuestra que la alternativa gratuita
es sensible a cambios de X y puede dejar de funcionar entre ejecuciones. El recolector fue corregido
para que una consulta que espera resultados nunca quede marcada como completa si recibe cero: ahora
se registra como fallida, conserva el estado y puede reintentarse.
