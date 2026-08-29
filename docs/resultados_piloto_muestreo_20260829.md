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
- el tope inicial de 100 no permite decidir por sí solo el tamaño definitivo de las ventanas.

## Ampliación de la hora normal

Se repitió la primera franja con un límite de 1.000 mediante
`config/prueba_hora_normal_mundial_2026.json`.

| Medida | Resultado |
|---|---:|
| Período | 13 de junio, 12:00–13:00 ART |
| Publicaciones únicas | 120 |
| Autores únicos | 117 |
| Límite | 1.000 |
| Saturada | No |
| Duplicados | 0 |
| Fuera de ventana descartados | 9 |
| Textos, autores, fechas o métricas faltantes | 0 |
| Perfiles con ubicación declarada | 73 |
| Relaciones de respuesta | 36 |
| Relaciones de cita | 10 |

La primera prueba había mostrado solamente que existían al menos 100 resultados. La ampliación
midió 120 y no se saturó: para esta consulta y esta hora normal no es necesario subdividir por
debajo de una hora. Esto no se extrapola automáticamente a partidos ni a la final, que deben
calibrarse por separado.

## Ampliación del partido y la final

Se probaron dos horas efectivas de juego, de acuerdo con los horarios locales publicados por FIFA:

- Argentina–Suiza: 11 de julio, 22:00–23:00 ART;
- final Argentina–España: 19 de julio, 16:00–17:00 ART.

Configuraciones reproducibles:

- `config/prueba_hora_partido_argentina_mundial_2026.json`;
- `config/prueba_hora_final_mundial_2026.json`.

| Medida | Argentina–Suiza | Final Argentina–España |
|---|---:|---:|
| Publicaciones guardadas | 1.000 | 987 |
| Autores únicos | 917 | 952 |
| Límite solicitado | 1.000 | 1.000 |
| Resultado completo respecto del total de X | No | No |
| Duplicados en el trabajo completo | 2 | No calculable tras la pausa |
| Fuera de ventana descartados | 18 | No calculable tras la pausa |
| Campos mínimos faltantes | 0 | 0 |
| Perfiles con ubicación declarada | 597 | 626 |
| Relaciones de respuesta | 161 | 146 |
| Relaciones de cita | 40 | 50 |

Argentina–Suiza alcanzó el límite de 1.000 y quedó formalmente marcada como saturada. Durante la
final se guardaron 987 resultados antes de que X aplicara una pausa temporal a la única cuenta
disponible. Aunque quedaron 13 resultados para alcanzar el límite solicitado, 987 tampoco debe
interpretarse como el total existente: la hora es demasiado amplia para una búsqueda completa.

Los ensayos muestran una diferencia de al menos ocho veces entre la hora normal y las horas de
partido. La campaña debe comenzar directamente con ventanas de 10–15 minutos en partidos y final,
mantener ventanas mayores fuera de los picos y conservar el refinamiento automático como control.

Fuentes de los horarios: [Argentina–Suiza en FIFA](https://www.fifa.com/es/tournaments/mens/worldcup/canadamexicousa2026/articles/goles-videos-argentina-suiza-mundial-2026-resumen-highlights)
y [final España–Argentina en FIFA](https://www.fifa.com/es/tournaments/mens/worldcup/canadamexicousa2026/articles/videos-goles-espana-argentina-copa-mundial-resumen-highlights).

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
