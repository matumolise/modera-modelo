# Bloque 2A: fuente, cohorte y particiones PMUM

Estado vigente: ver [cierre Windows/Docker y entrega](WINDOWS_DOCKER_CLOSURE_2026-10-12.md). Este informe conserva el alcance y los pendientes de su bloque original; los cierres posteriores no se atribuyen retrospectivamente a esa ejecución.

Fecha: 12/10/2026. Revisión acotada de lectura y comprobación numérica; no ajusta modelos en memoria, no crea artefactos ni sustituye HU v1. Continúa desde el checkpoint local b6e0b19 del bloque 1.

## Fuente leída y correspondencia

Se abrió directamente el ZIP proporcionado 21802447 (1).zip. Su SHA-256 es f16adde7e9fae278de2fa5d25412533b98db91306b31e2ba637f09c05347e8f5. Se leyeron SEM.inp, SEM.dat y los metadatos SEM.sav mediante pyreadstat 1.3.6; no se redistribuyen microdatos. Esta lectura no acredita autores/licencia/metadatos del registro Zenodo actual ni una nueva revisión del artículo científico.

SEM.inp declara 122 variables, formato fijo 122f8.2 y su filtro original filter=1/CGGender<=2/CHGender<=2. El código del candidato utiliza filter=1, edad 6–12, nueve ítems completos y código niño 1/2, sin restringir el código del cuidador de la misma forma. La diferencia es explícita y no se corrige automáticamente para imitar el análisis SEM original.

| Selección sobre SEM.dat | Conteo recontado |
|---|---:|
| Filas del archivo | 2514 |
| filter=1 y edad 6–12 | 810 |
| Nueve ítems enteros entre 1 y 5 | 806 |
| Excluidos por ítems incompletos/inválidos en ese intervalo | 4 |
| Completos con código niño 1/2 | 803 |
| Completos excluidos con código niño 4 | 3 |
| Subconjunto de 803 que además cumple CGGender<=2 | 800 |
| IDs de registro distintos en la cohorte operativa | 803 |
| Subgrupo definido por NoChildren=1 | 300 |

El total coincide con la suma de los nueve ítems en los 806 completos. Se compararon directamente las cuatro entradas del loader con SEM.dat y el objetivo con PMUMTotal/9: coincidencia exacta, sin Android, imputación de ítems o PMUM como predictor.

803 IDs distintos acreditan ausencia de duplicación por ese identificador en esta cohorte; no acreditan por sí solos independencia de hogares/cuidadores ni ausencia de duplicados semánticos. No se recuperó aquí un identificador de agrupamiento que permita verificar esa independencia. El subgrupo de 300 es operacionalmente NoChildren=1; el nombre de la variable SAV indica una recodificación en tres categorías y no tiene diccionario de valores visible. No se auditó su recodificación original, por lo que se explicita ese límite antes de afirmar su equivalencia exacta con hogares de un hijo.

## Codificación y formulario

La posición de columnas de SEM.dat se cotejó con los nombres/metadatos de SEM.sav. CHGender tiene códigos 1=Fiú, 2=Lány y 4=Nem kívánok válaszolni / Egyéb. El código 4 está declarado como missing de usuario. CGGender tiene su propio código 3 de respuesta no declarada/otra y no se debe confundir con el código del niño.

Las categorías de pantalla son 1=<1 h, 2=1–2 h, 3=3–4 h, 4=5–6 h y 5=7 h o más. El texto de la pregunta weekend explicita últimos 30 días y total de dispositivos. El label weekday sigue truncado; el nombre de la variable incluye 30N/Hétköznap, pero no reemplaza la pregunta literal completa. No se completa el formulario por analogía. La instrucción de selección de hijo menciona elegir al que más tiempo usa pantallas; el rango operativo 6–12 es un filtro posterior, no una validación argentina.

## Particiones y evaluación guardada

Se reconstruyeron los índices del orden de los 806 completos y del subconjunto 803. La huella del orden es be9a5e2e3f9f7e84f25dad6250a3fae4eadf09f05b8f7be63ab26cb2359dec06 y coincide con el JSON guardado pmum_fixed_vs_nested_with_median.json.

Se reconstruyó KFold(5, shuffle=True, seed=1027): tamaños externos 642/161 tres veces y 643/160 dos veces. Todas las huellas train/test coinciden con el reporte. No hay solapamiento de posiciones por pliegue; cada posición se evalúa exactamente una vez. Los cuatro pliegues internos usan sólo train externo, con seed=20261007+fold; sus validaciones cubren una vez cada fila del train externo y no acceden a test externo.

Se inspeccionó make_ridge: estandarización/imputación de edad y one-hot forman parte del Pipeline entregado a fit/cross_val_score. Esa ruta no ajusta transformaciones con el test externo. La selección de variables/diseño se exploró antes; no se presenta como selección íntegramente anidada ni como nuevo holdout independiente.

Se cotejó la elección de alpha con los scores internos guardados: [1,1,1,10,1]. Esto verifica coherencia del reporte y del algoritmo de elección, no vuelve a calcular sus scores. El artefacto se declara Ridge alpha=1: sus métricas no se equiparan automáticamente con las del procedimiento que elige alpha por pliegue.

Los MAE/RMSE/R² recuperados siguen siendo resultados de la reproducción anterior. No se recalcularon predicciones ni métricas en este bloque ligero; no se atribuye una segunda reproducción al cotejo de hashes y particiones. Se conserva también la diferencia entre selección interna sin clipping y evaluación externa con clipping 1–5.

## Evidencia y cierre

PMUM_SOURCE_PARTITIONS_BLOCK2.json conserva huellas de fuente/reporte, conteos, comprobaciones por pliegue y alcance; no conserva IDs individuales o filas. La lectura directa confirmó las afirmaciones anteriores de cohorte y selección, con las limitaciones descritas. No apareció un defecto que requiera cambiar el entrenamiento ni el modelo entregado.

Implementado: no hubo nuevos cambios de código. Comprobado: fuente/conteos/objetivo/cuatro entradas/metadata/índices y aislamiento de pliegues. Pendiente de evidencia: binario HU v1 y procedencia exacta de su ajuste; redacción weekday completa; agrupamiento por hogar/informante y recodificación del subgrupo. Pendiente de los próximos bloques: evaluación C2 y sus límites, cotejo de tesis y consolidación de entrega. La validez externa y la habilitación de producto continúan abiertas.
