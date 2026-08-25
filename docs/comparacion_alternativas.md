# Comparación de alternativas para recolectar datos de X

Evaluación actualizada el 24 de agosto de 2026. Se comparan las tres opciones propuestas para el
proyecto. Los precios pueden cambiar y deben verificarse antes de una descarga paga.

| Criterio | Twikit | twscrape | TwitterAPI.io |
|---|---|---|---|
| Tipo | Librería FOSS no oficial | Librería FOSS no oficial | Servicio comercial no oficial |
| Costo de software | USD 0 | USD 0 | USD 0,15 por 1.000 tuits retornados |
| Autenticación | Cuenta, login/cookies | Cuenta y cookies; pool en SQLite | Clave de API |
| Búsqueda | Sí | Sí | Sí |
| Respuestas | API disponible; prueba local pendiente | Implementado y probado sin conexión; prueba real bloqueada por un cambio de X | Endpoints disponibles según el servicio |
| Varias cuentas/proxies | Implementación propia | Soporte incorporado | No requiere cuentas propias de X |
| Rate limits | Deben gestionarse | Rotación y estados incorporados | El proveedor administra la infraestructura |
| Reanudación/deduplicación | Debe construirse | Implementada por el proyecto sobre SQLite | Debe construirse en el cliente |
| Riesgo de bloqueo de cuenta | Sí | Sí | Trasladado principalmente al proveedor |
| Estado en este proyecto | Evaluación técnica, sin piloto real reproducible | Piloto real completado | No probado por restricción presupuestaria |

Fuentes de características y precio:

- [Twikit](https://github.com/d60/twikit)
- [twscrape](https://github.com/vladkens/twscrape)
- [TwitterAPI.io: precios](https://twitterapi.io/pricing)

## Conclusión

La opción recomendada para continuar el piloto sin presupuesto es `twscrape`, porque ya produjo
datos reales, permite conservar sesiones, admite varias cuentas/proxies y su salida fue integrada
con trabajos, deduplicación, auditoría y exportación.

`Twikit` sigue siendo una alternativa gratuita válida para una prueba independiente, pero antes de
comparar resultados necesita un piloto reproducible con versiones fijadas, autenticación verificada
y las mismas consultas/fechas.

`TwitterAPI.io` es el plan alternativo si la estabilidad o el volumen vuelven demasiado costosa la
operación con cuentas. Su costo es bajo para una base académica pequeña, pero depende de un tercero y
requiere presupuesto.
