# Tarea 2: cierre de trazabilidad PMUM HU v1

## Resultado y alcance

**Cerrado el cotejo técnico/documental recuperable de HU v1.** Se resuelven los
faltantes anteriores de localización/identidad de originales, registro del ajuste,
atribución fijo/anidado y recodificación del subgrupo. No se entrenó, predijo,
deserializó o sustituyó un modelo en este bloque. La carga del original está
acreditada por la ejecución Windows que Matías aportó, no por una carga Linux nueva.

Base exacta `0d2bdeee88ba2034da29073cf867fabc25708fb7`, importada y comprobada en
Windows por Matías; código del coordinador en `0d806c2`. Nueva rama
`pmum-provenance-closure-candidate`; anteriores conservadas. Referencias remotas
consultadas: HU en `e736500c36bdd5d8c066bd6e843b3ee39a69f108`, cierre PMUM/C1 en
`83fc635e4fadca9a0ecc17e0f23c637ea6a7a398`. La nueva base local no se presenta como
publicada. No se hicieron push, merge, despliegue o cambios de tesis.

No se transforma una función incompleta en una limitación para simular cierre:
el estimador, las cuatro entradas, abstenciones y contrato interno existentes
se conservan. El manifiesto original ya declaraba `NOT APPROVED; no app integration`.
Este cierre no convierte el candidato interno en un score clínico de producto.

## Cadena de procedencia recuperada

| Eslabón | Evidencia contrastada | Qué acredita |
|---|---|---|
| Fuente original | ZIP `21802447 (1).zip` recuperado de Library; hash registrado; SEM.dat/SEM.inp/SEM.sav y CFA.sav leídos | Identidad de bytes y correspondencia operacional; no nuevos metadatos/licencia del registro web |
| Cohorte y objetivo | Loader existente y SAV independientes; 2514 registros, 806 completos y 803 con código niño 1/2; tres código4 excluidos | Cuatro predictores y PMUMTotal/9 coinciden exactamente en los 803 |
| Ajuste original | Registro del usuario recuperado del chat del 07/10, 18:52:15 UTC: script `hu_pmum_candidate_v1.py train`, ZIP original y carpeta `Documents/modera_pmum_experimental`; creación 18:52:05.946441 UTC | Existencia de una ejecución original y sus argumentos/cohorte; no se fabrica un log íntegro a partir de ese resumen |
| Entorno y enlace al binario | Registro del usuario 07/10, 19:47:45 UTC, con hash de fuente/artefacto, Python 3.10.0, Windows build 26200, sklearn1.7.2/numpy2.2.6/scipy1.15.3/joblib1.5.3 | Huella contemporánea del artefacto y entorno reportado |
| Código conservado | Primer snapshot disponible d597ce7; función `train` AST idéntica a la actual y loader/transformadores textualmente idénticos | Coherencia del programa conservado; no prueba retrospectiva del snapshot exacto previo al ajuste |
| Original hoy | Matías localizó joblib/manifiesto en `C:\Users\matum\Documents\modera_pmum_experimental`; verificador PASS 14/10 | Mismo hash joblib; pipeline alpha1, categorías, 350 casos y dos edades fraccionarias; originales intactos |
| Manifiesto original | Texto completo aportado por Get-Content; reconstrucción UTF-8/CRLF coincide con su SHA-256 | Recuperación de los mismos bytes del manifiesto, no un manifiesto corregido o inventado |
| Evaluación histórica | Paquete revisado 12/10 y `PMUM_OOF_HIGH_REAUDIT.json` recuperados/verificados; índices reconstruidos sin ajustes | Separación de procedimientos, huellas de cohorte/pliegues y atribución del diagnóstico de error |

El verificador Windows del 14/10 registra rango de predicciones 1.489–3.605,
sin warnings de carga y `original_files_unchanged=true`, `new_model_trained=false`.
Su JSON en este repositorio es una **transcripción identificada del mensaje de
Matías**, no los bytes originales de ese reporte. El binario permanece en Windows;
no se afirma haber recibido ni inspeccionado aquí sus coeficientes individuales.

## Cronología exacta del código

Creación del manifiesto: `2026-10-07T18:52:05.946441+00:00`.
Autor de d597ce7: `2026-10-07T16:29:51-03:00` (19:29:51 UTC).
Committer: `2026-10-07T16:36:39-03:00` (19:36:39 UTC).
El snapshot se guardó después del ajuste. La comparación AST de `train` y de texto
del loader verifica que los cambios posteriores no alteraron esa ruta: soporte
de importación y guarda de edad en inferencia no constituyen otro entrenamiento.

No hay snapshot/hash contemporáneo **anterior** al ajuste ni log íntegro del fit
aportado. Esa precisión histórica permanece; no puede resolverse mediante una
decisión de ingeniería o entrenando otro binario. El cierre defendible es una
cadena corroborada por registros contemporáneos, fuente, manifiesto/hash y
verificación posterior, no una reproducción bit a bit del fit. El archivo exacto
que fortalecería ese último nivel sería una copia/huella del código previo al
07/10 18:52 UTC y su registro de ejecución. No se exige inventarlo para documentar
con precisión el candidato existente.

## Fijo y selección anidada: discrepancia resuelta

Datos del reporte histórico, 803 casos OOF; no recalculados en este bloque:

| Procedimiento | MAE | RMSE | R² | Error absoluto >1 punto |
|---|---:|---:|---:|---:|
| Media de train de cada pliegue | 0.7430 | 0.8914 | -0.0047 | 30.64 % |
| Mediana de train de cada pliegue | 0.7455 | 0.8971 | -0.0176 | 28.14 % |
| Ridge fijo alpha=1 | 0.6427 | 0.7839 | 0.2231 | **168/803 = 20.92 %** |
| Selección interna de alpha 1/10/100 | 0.6427 | 0.7826 | 0.2257 | **169/803 = 21.05 %** |

La diferencia que quedó abierta con Claude se cierra en el **reporte recuperado**:
`error_diagnostics.fixed_alpha_1.fraction_error_over_one_scale_point` es
0.20921544209215442; el de `nested_selection` es 0.21046077210460773. La aritmética
de los denominadores se verificó. No hay vectores OOF individuales en este JSON:
no se afirma una recalculación fila a fila desde las predicciones guardadas.

Se reconstruyeron los cinco pliegues externos, sus diez hashes y el orden de
cohorte: todos coinciden. Según los scores internos guardados, los alpha elegidos
son [1,1,1,10,1]. Sus scores tampoco se recalcularon. La selección interna es sin
clipping; evaluación externa usa clip1–5. Las variables, alpha fijo y diseño
provienen de exploración previa: esto sigue siendo evaluación interna exploratoria.

El modelo final usa alpha1 ajustado sobre los 803, no una mezcla de cinco modelos.
El texto libre del manifiesto menciona nested CV; sus bytes se conservan y este
addendum evita asignarle las métricas anidadas al único modelo fijo. El MAE igual
al redondear no vuelve equivalentes los procedimientos. El porcentaje >1 no es
exactitud clínica ni un umbral de riesgo. El entorno reportado de entrenamiento
Windows y reproducción 12/10 es sklearn1.7.2; referencias a sklearn1.8.0 en la
exploración anterior no deben trasladarse al ajuste final de Windows.

## Cuestionario y NoChildren

Se leyó el ZIP original, no sólo un documento anterior. Ambas variables de pantalla
conservan códigos nominalizados en one-hot: 1=<1h, 2=1–2h, 3=3–4h, 4=5–6h,
5=7h o más. No se imputan puntos medios, arreglan intervalos ni sustituyen por
minutos Android. Son estimaciones del adulto; los ítems PMUM nunca son features.

La pregunta de fin de semana conserva explícitamente últimos 30 días, promedio
del día y todos los dispositivos. La etiqueta weekday corta su introducción
antes de la pregunta literal. Los otros SAV no recuperan esa pregunta completa.
La consulta del registro Zenodo volvió a fallar; las búsquedas no aportaron una
fuente primaria que la complete. No se afirma equivalencia literal de instrumentos.

**Decisión de cierre del contrato interno:** conservar `weekday_category` y
`weekend_category` como respuestas categóricas explícitas del adulto, con el
formulario candidato ya identificado como adaptación propia. El texto weekday
propuesto sobre 30 días/todas las pantallas es una adaptación, no una traducción
verificada. Omitir alguna respuesta sigue causando abstención. La equivalencia,
comprensión y validación para familias pertenecen a la adaptación/integración
real diferida; no se presentan como probadas. No se sustituye por otro estimador
ni se promueve el formulario a aprobado para ocultar este punto.

Para NoChildren se recuperó algo adicional: `SEM.sav.GyerekekSzáma_3KAT` coincide
con la recodificación de `CFA.sav`; los IDs son únicos en ambos archivos y las
2514 filas se vinculan uno a uno. Comparaciones incluyen igualdad de faltantes.
El código1 equivale exactamente al valor1 de `CFA.sav.GyerekekSzáma` en todas las
filas y en la cohorte; el subgrupo contiene 300 casos.

La pregunta original de esa variable pide en la crianza de cuántos **menores de
18 años participa el informante en su propio hogar**, incluyendo hijos biológicos,
adoptados y de su pareja en familias ensambladas. Por tanto el subgrupo puede
describirse así; no como número total de hijos biológicos o garantía de un
informante por hogar. Se resuelve la recodificación operativa y su semántica;
los IDs individuales no prueban independencia de hogares/cuidadores.

## Matriz de cierre

| Frente | Estado | Evidencia / criterio restante |
|---|---|---|
| Fuente/cohorte/entradas/objetivo | Cerrado | Cotejo directo ZIP, loader y SAV, sin microdatos redistribuidos |
| Identidad de binario y manifiesto | Cerrado con ejecución Windows recibida | Hash original confirmado; manifiesto recuperado con hash idéntico |
| Registro de ajuste y programa conservado | Cerrado en nivel recuperable | Cronología y AST; snapshot prefit exacto no disponible, sin inventar reproducibilidad bit a bit |
| Métricas fijo/anidado y 20.92 % | Resuelto | JSON histórico original, claves separadas, hashes de particiones y aritmética |
| NoChildren | Resuelto | Vinculación SEM/CFA, pregunta original y equivalencia de código1 |
| Weekday literal | No recuperable con fuentes disponibles | No se afirma transcripción/equivalencia; adaptación propia explícita para candidato interno |
| Validación externa, clínica o argentina | No acreditada; fuera de este cierre | No convertida en diagnóstico/cortes ni en requisito ficticiamente cumplido |
| Score como disparador | Se conserva exclusión del contrato vigente | No decide C1, alertas adultas o frecuencia infantil |
| Catálogo y aplicación real | Diferidos por usuario | Cecilia e integración Juanma; no se ejecutaron ni atribuyeron aprobaciones |

La tarea 2 queda cerrada para describir honestamente el candidato técnico y su
procedencia. No necesita otro benchmark ni entrenamiento. No habilita mostrar
un diagnóstico a familias. Las afirmaciones anteriores que daban por ausentes
todos los originales quedan actualizadas por este cierre; las limitaciones de
generalización y del snapshot exacto siguen identificadas con su alcance.

## Verificación y archivos

`audit_pmum_provenance_v1.py`: PASS de lectura de fuente, hashes del paquete,
manifiesto y reporte, entradas/objetivo, cohorte, pliegues, elección según scores
guardados, recodificación y cotejo de funciones. Se repitió con `Pipeline.fit`,
`Ridge.fit` y `joblib.load` prohibidos: PASS. Dos controles negativos rechazaron
fuente alterada y manifiesto alterado. No hubo fit, predicciones o carga local.

Los JSON están en `evidence/pmum_2026-10-14/`: auditoría nueva, controles, reporte
histórico conservado byte a byte, manifiesto hash-idéntico y transcripción Windows.
Se agregan atributos Git para conservar los bytes originales, incluidos CRLF.
No se redistribuyen ZIP fuente, SAV/DAT, filas, IDs o joblib.

Sólo se añade una herramienta offline de comprobación y documentación/evidencia.
El código runtime es idéntico al candidato probado en Windows (450 aprobados,
uno omitido, 192 subtests), pero ese antecedente no se denomina prueba nueva de
esta herramienta. No se repitió la suite por estas adiciones documentales.
No se inició la redacción de tesis ni la tarea 3.
