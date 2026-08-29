# Etiquetado, ubicación y automatización

## Objetivo

Construir etiquetas que permitan responder las preguntas del proyecto sin confundir tema,
hostilidad, anonimato y automatización.

## Dos etiquetas para el contenido

Cada publicación de la muestra manual recibe:

### Narrativa

- fútbol, arbitraje o trampa;
- racismo;
- Israel o Palestina;
- Malvinas;
- nazismo;
- economía o hambre;
- antiargentinismo explícito;
- otra.

Una publicación puede tener más de una narrativa.

### Postura

- hostilidad contra Argentina;
- defensa de Argentina;
- autocrítica argentina;
- neutral;
- ambigua.

La presencia de una palabra del diccionario no determina la postura.

## Muestra manual

La muestra debería estratificarse por:

- día normal, partido y final;
- idioma;
- capa principal y temática;
- nivel de interacción;
- narrativa preliminar.

Dos personas deberían etiquetar una parte común para medir acuerdo. Los desacuerdos se revisan y se
usan para mejorar el manual antes de automatizar.

Para generar una muestra reproducible de las capas principal y temática:

~~~bash
x-research export-annotation-sample \
  --database data/mundial_2026.sqlite3 \
  --output data/exports/muestra_etiquetado.csv \
  --per-layer 100
~~~

Las columnas narratives, stance, identity, automation y notes quedan vacías para completar.

## Identidad de cuentas

- **Identificable:** el perfil ofrece señales públicas razonables de una persona u organización.
- **Seudónima:** utiliza una identidad o personaje no verificable públicamente.
- **Indeterminada:** no hay evidencia suficiente.

No se deben realizar intentos invasivos de identificación.

## Automatización

- **Compatible:** reúne varias señales consistentes con comportamiento automatizado.
- **No compatible:** el comportamiento observado es predominantemente humano.
- **Incierta:** los datos no alcanzan o las señales son contradictorias.

Las señales posibles son:

- edad de la cuenta;
- cantidad de publicaciones por unidad de tiempo;
- regularidad horaria;
- contenido repetido;
- enlaces o hashtags repetidos;
- proporción de seguidores y seguidos;
- respuestas repetidas a las mismas cuentas;
- coordinación temporal con otras cuentas.

La verificación paga, el anonimato, una cuenta nueva o una gran actividad no prueban automatización
por sí solos.

## Ubicación

Guardar la ubicación del perfil exactamente como aparece y crear después una columna normalizada.
Toda tabla debe distinguir:

- ubicación autodeclarada;
- ubicación adjunta a una publicación;
- inferencia lingüística;
- ubicación desconocida.

No combinar estas fuentes en una sola columna llamada “país real”.

## Limitaciones que deben acompañar el análisis

1. X puede entregar resultados incompletos o cambiantes.
2. twscrape depende de interfaces no oficiales.
3. Los retuits nativos pueden no aparecer como publicaciones separadas.
4. Las métricas de interacción cambian con el tiempo.
5. Los hilos seleccionados introducen un sesgo hacia conversaciones virales.
6. Los diccionarios temáticos no determinan postura.
7. La ubicación del perfil es opcional y falsificable.
8. Las señales de bot sólo permiten hablar de compatibilidad, no de certeza.
