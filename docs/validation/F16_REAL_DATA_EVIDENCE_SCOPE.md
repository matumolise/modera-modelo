# F16 — Alcance de la evidencia real y sensibilidad del Dataset A

Estado: auditoría técnica, 1 de octubre de 2026. No sustituye el contrato de
integración ni acredita validación clínica o predictiva. Base de código:
`f16-catalog-decision` (`09fe91d`).

## Afirmaciones permitidas

| Evidencia | Permite | No permite |
| --- | --- | --- |
| Dataset A sintético | Reproducir el pipeline y estudiar su sensibilidad a supuestos. | Afirmar representatividad poblacional o precisión PMU en niños reales. |
| Encuesta de E50 (§3.1, pp. 30–32) | Describir respuestas parentales sobre titularidad, frecuencia y tiempo estimado del celular en la muestra. | Convertir categorías de frecuencia en probabilidad diaria de cero o atribuir logs de un dispositivo compartido. |
| NSCH 2024, ítem SCREENTIME | Contraste descriptivo en niños de EE. UU. de 6–11 años, según adulto, sobre varias pantallas un día hábil habitual sin trabajo escolar. | Calibrar minutos del teléfono argentino con porcentajes que miden otra variable. |
| F12, experimento Android en emulador | Distinguir eventos de pantalla, desbloqueo y foreground en ese entorno. | Generalizar el resultado a teléfonos físicos u obtener sesiones productivas sin una regla adicional. |
| Pruebas guionadas en teléfonos adultos, **pendientes** | Si se realizan, evaluar captura y reconstrucción técnica en los casos y dispositivos probados. | Inferir uso infantil, eficacia de alertas o precisión PMU. |
| zEbra, 10–14 años | Una vez leído el archivo, explorar uso diario de Instagram, TikTok y YouTube. | Probar el fenómeno implementado `DAILY_USE_DURATION`, que mide pantalla interactiva total del dispositivo. |
| ABCD EARS, piloto 11–12 | Candidato restringido de cuatro semanas con registros pasivos. | Declarar acceso, N de registros cruzables con PMUM-SF ni cobertura de las 11 entradas sin examinar los datos. |

**Corrección de informes anteriores:** zEbra no valida el analizador histórico
implementado. Tampoco hay prueba de que una consulta de una hora en adultos
construya diez de las once features semanales: sesión, apertura, categorías y
ratios aún carecen de reconstrucción productiva validada.

## Titularidad y frecuencia en E50

E50 comunica 101 respuestas: 58 con celular propio, 30 compartido y 13 sin
celular. En los 88 con acceso, las frecuencias comunicadas son 45 todos los
días, 23 casi todos, 16 algunos días y 4 nunca o casi nunca. No se dispone
aquí de tabla individual que cruce titularidad y frecuencia. El escenario Base
del simulador presupone dispositivo personal y produce uso positivo en los
siete días; no representa automáticamente a los 101 casos. Los 13 sin celular
no constituyen siete días observados de cero uso de Android.

## Reproducción de minutos diarios

Ejecutar `python tools/validation/audit_daily_use_sensitivity.py`. El script
reconstruye 9.800 días (1.400 niños × 7) con la misma realización que el CSV
final y exige que las medias por niño concuerden con ese CSV (diferencia máxima
observada: `8.53e-14` minutos). No modifica el repositorio.

En los 6.000 días hábiles simulados de 6–11 años, Base v1 produce 1,25 % de
días con menos de 60 minutos y 58,02 % entre 120 y menos de 240. Su media
diaria, incluyendo fines de semana y 12 años, es 175,80 minutos. El valor
configurado de 155 minutos es una **mediana basal condicional**, no esta media
observada ni una estimación poblacional argentina.

| Escenario ilustrativo | Días hábiles 6–11 con menos de 60 min | Días hábiles 6–11 con 120–<240 min | Media de todos los días |
| --- | ---: | ---: | ---: |
| Base | 1,25 % | 58,02 % | 175,80 min |
| Probabilidad simulada de cero 0,05 | 6,23 % | 55,23 % | 166,88 min |
| Probabilidad simulada de cero 0,15 | 15,47 % | 49,80 % | 150,38 min |
| Variación lognormal adicional de 0,25 | 2,97 % | 50,98 % | 175,24 min |
| Cero 0,05 + variación 0,25 | 7,88 % | 48,48 % | 166,29 min |

La semilla independiente de sensibilidad es `20261001`; 0,05, 0,15 y 0,25
son supuestos elegidos para explorar dependencia, **no** estimaciones desde
niños. El multiplicador de dispersión es `exp(0,25 × Z − 0,25²/2)` y se aplica
únicamente a minutos diarios; la máscara de ceros se genera una vez y se
comparte entre escenarios. No se regeneran sesiones, apps, ratios ni el
desenlace sintético: estos escenarios no forman datasets aptos para entrenar.

NSCH 2024 informa para 6–11 años 10,8 % «menos de una hora», 18,3 % «una
hora», 31,6 % «dos horas», 19,3 % «tres horas» y 19,9 % «cuatro horas o más».
**Sus respuestas enteras de una, dos y tres horas son categorías de la
encuesta**, no intervalos continuos `1–<2`, `2–<3` y `3–<4` del script. No
calcular distancias numéricas ni ajustar parámetros equiparando esas celdas.
La diferencia entre teléfono y todas las pantallas, trabajo escolar,
informante, país, día típico y día generado impide llamarlo validación.

## Decisión metodológica y riesgo para la entrega

El Dataset A conserva su condición sintética aunque se le adjunten márgenes
de encuestas. Un conjunto enriquecido útil **para validar el predictor PMU**
requeriría filas reales, derivaciones trazables y un desenlace apropiado
medido en las mismas personas. No se ha obtenido tal conjunto para entrenar
y validar el predictor PMU de Moderá.
El trabajo documenta plausibilidad parcial y validación técnica de otros
componentes, pero **no cumple todavía** una exigencia de rendimiento de la
IA principal sobre datos reales. No usar CUSUM o la heurística de actividades
como sustitutos nominales de un modelo entrenado y evaluado.

ABCD no es dependencia de la próxima entrega: NBDC exige certificación de
uso, afiliación institucional elegible, firmante autorizado y FWA activa. La
documentación describe `participant_id` / `session_id`, piloto EARS en el
segundo año y preguntas parentales ampliadas desde ese año, pero no establece
el N con logs, PMUM-SF y coincidencia temporal simultánea.

## Referencias de consulta

- E50, §3.1, pp. 30–32 (artefacto histórico interno).
- CAHMI/HRSA, *NSCH 2024, indicador 6.10*, consulta 1/10/2026:
  https://www.childhealthdata.org/browse/survey/results?g=1250&q=12603&r=1
- WADE y col., *Passive Sensing of Preteens’ Smartphone Use*, 2021,
  DOI: 10.2196/29426: https://pmc.ncbi.nlm.nih.gov/articles/PMC8561413/
- ABCD Study, *Novel Technologies*, versión 7.0:
  https://docs.abcdstudy.org/v/7_0_0/documentation/non_imaging/nt.html
- NBDC, *Data Access Process*, consulta 1/10/2026:
  https://www.nbdc-datahub.org/data-access-process
- IRMER y SCHMIEDEK, estudio zEbra, 2023, DOI: 10.1038/s44271-023-00013-0:
  https://www.nature.com/articles/s44271-023-00013-0
