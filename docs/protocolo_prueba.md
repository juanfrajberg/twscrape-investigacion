# Protocolo del piloto

## Pregunta

¿Puede `twscrape` recuperar de manera estable publicaciones y respuestas del período elegido con los
campos mínimos solicitados por el proyecto?

## Prueba inicial

1. Ejecutar primero `config/prueba_minima.json` para validar una búsqueda de 20 resultados.
2. Si funciona, usar las dos consultas de `config/experimento.ejemplo.json`.
3. Mantener la ventana del 19 de julio de 2026 al 20 de julio de 2026, interpretada en la zona
   horaria `America/Argentina/Buenos_Aires`.
4. Limitar cada consulta ampliada a 100 resultados.
5. Descargar hasta 25 respuestas de los 5 tuits con mayor `reply_count`.
6. Ejecutar el experimento una vez.
7. Guardar el resumen, la hora de inicio y la hora de finalización.
8. Ejecutarlo nuevamente con `--force` para medir estabilidad y duplicados.

## Métricas

| Dimensión | Medida |
|---|---|
| Acceso histórico | Fecha mínima y máxima y cantidad descartada fuera del período |
| Volumen | Resultados obtenidos y IDs únicos por consulta |
| Estabilidad | Diferencia de IDs entre dos ejecuciones iguales |
| Duplicación | Capturas repetidas detectadas |
| Completitud de campos | Porcentaje no nulo de texto, autor, fecha, métricas y relaciones |
| Conversaciones | Respuestas únicas descargadas y vínculos padre-hijo válidos |
| Rendimiento | Duración total y tuits por minuto |
| Límites | Esperas, rate limits, cuentas bloqueadas y otros errores |
| Requisitos | Tipo de cuenta, cookies, verificaciones y necesidad de proxy |

## Interpretación

La cantidad obtenida no equivale a la cantidad total existente en X. Sin una fuente de referencia no
se puede afirmar que la búsqueda es completa. Sí se puede evaluar:

- si alcanza el límite solicitado;
- si la paginación se detiene antes de tiempo;
- si repetir la consulta devuelve los mismos IDs;
- si hay variaciones importantes entre ejecuciones;
- si las fechas y campos coinciden con una inspección manual de una muestra.

## Criterio preliminar de éxito

El piloto se considera técnicamente útil si:

- completa ambas consultas sin perder el progreso;
- guarda 90% o más de los campos mínimos aplicables;
- identifica correctamente respuestas y citas en una muestra manual;
- una segunda ejecución no duplica registros en SQLite;
- documenta cualquier rate limit o bloqueo de forma visible.

## Registro para el informe

Anotar después de cada ejecución:

```text
Fecha y hora:
Computadora / sistema operativo:
Versión de Python:
Versión de twscrape:
Cuenta nueva o existente:
Consultas:
Ventana temporal:
Duración:
Resultados obtenidos:
IDs únicos:
Respuestas:
Duplicados:
Errores o esperas:
Observaciones manuales:
```
