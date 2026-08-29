# Protocolo de investigación: Mundial 2026

## Pregunta general

Analizar cómo surgieron, circularon y se amplificaron contenidos hostiles o negativos sobre
Argentina en X durante el Mundial 2026, sin asumir de antemano que la conversación fue coordinada.

## Preguntas

1. ¿En qué cuentas y ubicaciones autodeclaradas aparecen primero los contenidos?
2. ¿Cuándo se producen los picos de actividad?
3. ¿Qué temas, narrativas y posturas predominan?
4. ¿Qué cuentas obtienen mayor amplificación?
5. ¿Qué proporción corresponde a cuentas identificables, seudónimas o indeterminadas?
6. ¿Qué cuentas presentan señales compatibles con automatización?
7. ¿La estructura temporal y de red es compatible con coordinación?

## Período

- Inicio local: 9 de junio de 2026, 00:00.
- Final exclusivo: 22 de julio de 2026, 00:00.
- Zona: America/Argentina/Buenos_Aires.
- Cobertura: 43 días, incluidos dos días antes y dos días completos después del torneo.

## Diseño de recolección

### Capa principal

Consultas amplias sobre Argentina, la selección, sus figuras y sus partidos. Esta capa se utiliza
para medir volumen, picos y prevalencias.

### Capa temática

Consultas orientadas a arbitraje, racismo, Israel/Palestina, Malvinas, nazismo, economía y
antiargentinismo explícito. Sirven para aumentar la recuperación de casos menos frecuentes.

No se incorporan automáticamente al denominador del corpus principal.

### Capa de hilos

Expansión por conversation_id de conversaciones seleccionadas por volumen de respuestas. Sirve
para estudiar redes, actores y circulación. Tampoco se usa para estimar prevalencia general.

## Partición temporal

- Ventanas generales del corpus principal: seis horas.
- Consultas temáticas: un día.
- Días de partidos de Argentina: una hora para el corpus principal.
- Final completa: una hora para todas las consultas.
- Desde cuatro horas antes hasta catorce horas después del comienzo de la final: 15 minutos.
- Mínimo de refinamiento automático: diez minutos.

Las fechas de Argentina utilizadas son 16, 22 y 27 de junio; 3, 7, 11, 15 y 19 de julio.

## Saturación y cobertura

Una ventana queda marcada como saturada si devuelve exactamente el límite solicitado. No se
considera completa hasta que:

- una subdivisión devuelve menos que su límite; o
- llega al intervalo mínimo y la limitación queda documentada.

La cobertura se evalúa con:

- cantidad por consulta y ventana;
- duplicación entre consultas;
- ventanas saturadas;
- trabajos fallidos;
- campos faltantes;
- comparación entre días normales, partidos y final.

twscrape no permite afirmar que el corpus sea un censo exhaustivo de X. Los resultados deben
describirse como el corpus recuperado por estas consultas, fechas, cuentas y versión del software.

## Unidad de análisis

La unidad primaria es la publicación. Cada ID aparece una sola vez en la tabla de tuits, pero puede
tener múltiples capturas que indican las consultas y capas que lo encontraron.

Las tablas derivadas son:

- publicaciones;
- cuentas e instantáneas históricas del perfil;
- capturas y procedencia;
- relaciones de respuesta, cita y retuit;
- trabajos y eventos;
- conversaciones.

## Análisis temporal

El volumen se calculará primero con la capa principal, en intervalos de 10 o 30 minutos según el
evento. Los hilos ampliados se excluyen de estas series porque sobrerrepresentan conversaciones
virales.

## Narrativas y postura

La detección temática y la postura son problemas diferentes. Una mención a racismo puede ser una
acusación, una defensa, una autocrítica o una referencia neutral.

Se utilizará una muestra manual estratificada para evaluar cualquier clasificador automático. Las
categorías están en config/taxonomia_narrativas.json.

## Ubicación

Se conserva:

- ubicación declarada del perfil;
- país o lugar adjunto a la publicación, cuando exista;
- idioma;
- marcadores lingüísticos que puedan estudiarse posteriormente.

La ubicación declarada no se presenta como ubicación real. Debe informarse su tasa de ausencia y no
inferir geografía precisa cuando no exista evidencia.

## Identidad y automatización

Se clasifican como ejes separados:

- identidad: identificable, seudónima o indeterminada;
- automatización: compatible, no compatible o incierta.

Las señales de automatización pueden incluir edad de la cuenta, intensidad y regularidad temporal,
repetición textual, proporción seguidores/seguidos, interacciones repetidas, reciprocidad y
concentración de enlaces. Ninguna señal aislada determina que una cuenta sea un bot.

## Coordinación

La hipótesis se evalúa mediante varios indicadores:

- creación de cuentas alrededor del evento;
- concentración de publicaciones por cuenta;
- repetición de textos o enlaces en ventanas estrechas;
- pares de cuentas que interactúan repetidamente;
- reciprocidad, transitividad y densidad del grafo;
- concentración de narrativas en comunidades;
- persistencia de los mismos actores entre partidos.

Un resultado negativo se informa con el mismo nivel de detalle que uno positivo.

## Protección de datos

El corpus contiene identificadores y textos públicos, pero sigue siendo información personal. Las
bases permanecen fuera del repositorio público. Los informes públicos deben minimizar nombres de
usuarios salvo que sean indispensables, justificar su inclusión y preferir métricas agregadas.

## Referencias de diseño

- Informe especial compartido con el equipo:
  https://drive.google.com/file/d/1vX-oJjbmBHGStwlq0UkE_4F4MBzdWd83/view
- Hilo de Ad Hoc:
  https://x.com/AdHocOK/status/2079692300762910955
- Calendario oficial de FIFA:
  https://www.fifa.com/es/tournaments/mens/worldcup/canadamexicousa2026/articles/calendario-fixture-mundial-2026-partidos-fechas
