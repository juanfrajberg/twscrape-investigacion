# Resultados del piloto de muestreo temporal

Fecha de ejecución: 29 de agosto de 2026.

## Objetivo

Comprobar la nueva estructura de campaña sobre tres situaciones:

1. una hora de un día sin partido de Argentina;
2. dos horas alrededor de Argentina–Suiza;
3. dos horas alrededor de la final Argentina–España.

La configuración reproducible es config/piloto_muestreo_mundial_2026.json.

## Resultado

| Franja | Recuperados | Saturada | Fuera de ventana |
|---|---:|---:|---:|
| Día normal, 13 de junio | 100 | Sí | 8 |
| Argentina–Suiza, 11 de julio | 100 | Sí | 2 |
| Final, 19 de julio | 100 | Sí | 8 |
| **Total** | **300** | **3 de 3** | **18** |

Los resultados fuera de ventana fueron descartados antes de guardarse.

## Calidad de datos

- 300 publicaciones únicas;
- 295 autores únicos;
- 0 textos faltantes;
- 0 autores faltantes;
- 0 fechas faltantes;
- 0 métricas básicas faltantes;
- 72 relaciones de respuesta;
- 25 relaciones de cita;
- 193 de 295 perfiles con ubicación autodeclarada;
- 295 perfiles con fecha de creación;
- 295 perfiles con cantidad de seguidores;
- 3 trabajos completos, 0 fallidos.

## Interpretación

Las tres franjas llegaron al máximo de 100. Por lo tanto, 100 no representa el volumen real de
ninguna de ellas. El piloto confirma que:

- la búsqueda histórica funciona en las tres situaciones;
- la validación temporal elimina resultados fuera de rango;
- los metadatos necesarios para ubicación y análisis de cuentas están disponibles;
- la campaña completa debe usar límites mayores y subdivisión automática;
- incluso un día sin partido puede requerir ventanas menores a una hora.

## Exportaciones verificadas

La misma base se exportó correctamente a Parquet:

- 300 publicaciones;
- 300 capturas con procedencia;
- 295 usuarios;
- 295 instantáneas de perfil;
- 97 relaciones;
- 3 trabajos y 6 eventos.

También se generó una muestra reproducible de diez publicaciones para comprobar el flujo de
etiquetado manual.

Las bases, textos e identificadores del piloto permanecen fuera de Git.

## Prueba adicional de conversation_id

Sobre una copia del piloto se seleccionó la raíz con mayor cantidad de respuestas y se ejecutó una
búsqueda histórica por conversation_id:

- 1 conversación seleccionada;
- límite de 20 resultados;
- 20 publicaciones nuevas recuperadas;
- 0 duplicados dentro del trabajo;
- 0 resultados fuera de fecha;
- 21 filas en el CSV final al sumar la raíz que ya estaba en el corpus;
- niveles de profundidad 0, 1 y 2 presentes.

La ventana volvió a quedar saturada, por lo que una expansión completa necesita el mismo
refinamiento temporal automático que el corpus principal.
