# Comparación de alternativas para recolectar datos de X

Evaluación actualizada el 24 de agosto de 2026. Se comparan las tres opciones propuestas para el
proyecto y la API oficial de X como referencia adicional. Los precios pueden cambiar y deben
verificarse antes de una descarga paga.

| Criterio | Twikit | twscrape | TwitterAPI.io | API oficial de X |
|---|---|---|---|---|
| Tipo | Librería FOSS no oficial | Librería FOSS no oficial | Servicio comercial no oficial | API de la plataforma |
| Costo base de lectura | USD 0* | USD 0* | USD 0,15 por 1.000 tuits | USD 5 por 1.000 publicaciones |
| Autenticación | Cuenta, login/cookies | Cuenta y cookies; pool en SQLite | Clave del servicio | Cuenta de desarrollador y clave de X |
| Búsqueda | Sí | Sí | Sí | Sí, según endpoint y acceso |
| Respuestas | Funciones disponibles; no probado aquí | Integrado; prueba en vivo pendiente de repetir | Endpoints administrados | Endpoints oficiales según acceso |
| Varias cuentas/proxies | Debe organizarse en el cliente | Soporte incorporado | No requiere cuentas propias de X | No trabaja con cuentas de scraping |
| Rate limits | Deben gestionarse | Rotación y estados incorporados | El proveedor administra la infraestructura | Definidos por la API oficial |
| Reanudación/deduplicación | Debe construirse | Implementada por este proyecto | Debe construirse en el cliente | Debe construirse en el cliente |
| Riesgo principal | Cambios internos de X y bloqueo | Cambios internos de X y bloqueo | Dependencia de un tercero | Costo de lectura mayor |
| Estado en este repositorio | No probado | Prueba real de 20; falta ampliar el piloto | No probado por falta de presupuesto | No probado |

\* No incluye cuentas, proxies, infraestructura ni tiempo de mantenimiento.

Fuentes de características y precio:

- [Twikit](https://github.com/d60/twikit)
- [twscrape](https://github.com/vladkens/twscrape)
- [TwitterAPI.io: precios](https://twitterapi.io/pricing)
- [API oficial de X: precios](https://docs.x.com/x-api/getting-started/pricing)

## Conclusión

La opción recomendada para continuar el piloto sin presupuesto es `twscrape`, porque ya produjo
datos reales, permite conservar sesiones, admite varias cuentas/proxies y su salida fue integrada
con trabajos, deduplicación, auditoría y exportación.

`Twikit` sigue siendo una alternativa gratuita válida para una prueba independiente. Para comparar
resultados hacen falta versiones fijadas, autenticación verificada y exactamente las mismas
consultas y fechas. Este repositorio no afirma resultados prácticos de una herramienta que no
ejecutó.

`TwitterAPI.io` es el plan alternativo si la estabilidad o el volumen vuelven demasiado costosa la
operación con cuentas. Su costo es bajo para una base académica pequeña, pero depende de un tercero y
requiere presupuesto. La API oficial es la referencia con mayor respaldo de la plataforma, pero su
precio publicado de USD 0,005 por lectura equivale a USD 5.000 por un millón de publicaciones.

El desarrollo completo, las mediciones, los costos y la recomendación están en
[`informe_twscrape.md`](informe_twscrape.md).
