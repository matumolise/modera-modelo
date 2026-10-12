# Moderá: cierre técnico y metodológico PMUM/C1

Fecha: 12 de octubre de 2026. Estado: candidato recuperado y revisado; evidencia técnica/metodológica consolidada hasta el alcance disponible, con HU original y Windows/Docker comprobados por Matías según resumen PASS, y decisiones de producto pendientes. Identificador: pmum-c1-model-closure-v1-reviewed-candidate. Ver FINAL_REVIEW_2026-10-12.md para la reauditoría y el paquete de entrega.

Consultar [auditoría de contratos del bloque 1](CONTRACT_AUDIT_BLOCK1_2026-10-12.md) y los bloques 2A/2B como antecedentes trazables. El inventario y las instrucciones del paquete identifican sus archivos finales. La validación posterior Windows/Docker se registra por separado en [el cierre vigente](WINDOWS_DOCKER_CLOSURE_2026-10-12.md), sin reasignar resultados a los bloques históricos.

## Resultado y límites

Se propone conservar HU v1 y el núcleo C1, con controles adicionales en sus adaptadores. Se reprodujo la evaluación PMUM sobre la fuente HU y el experimento histórico F12-C2; se probaron las correcciones, la persistencia y los reintentos en Linux. No se sustituyó ni guardó un modelo nuevo. No se modificaron parámetros C1, perfiles existentes ni resultados históricos.

La estabilización técnica no aprueba el uso con familias. PMUM conserva `experimental: true` y `internal_research_only`; C1 conserva su alcance técnico candidato. No hay validación externa argentina, calibración clínica o perfil C1 de producto. La revisión de Cecilia sigue pendiente y este bloque no amplía actividades, ofertas, tarjetas o comunicaciones adultas.

## Base y fuentes efectivamente comprobadas

Base publicada: `60c8764a2e2840503a598bf0c6605f1e2e1a6baf`, rama `integration-audit-closure-candidate`. Las cinco referencias publicadas se consultaron. La ejecución original dejó pmum-c1-model-closure-candidate local; los bloques posteriores usan pmum-c1-contract-audit-candidate. El aplicador del paquete comprueba esas cinco referencias y crea pmum-c1-closure-reviewed-candidate en un worktree nuevo; su núcleo se ensayó contra el árbol público íntegro y bajo autocrlf=true. No realiza commit/push/merge.

El entorno inicial tenía un snapshot parcial de 171 blobs verificados; su HEAD local no equivalía al público. Para ensayar la entrega se recuperaron los 204 blobs del árbol público de 275 entradas y se reconstruyeron árbol y objeto commit exactos de 60c8764. No se reconstruyó toda la historia pública. El parche procede de contenidos comprobados; el ensayo de aplicación utiliza la base exacta. El inventario distingue las dos procedencias.

Fuentes leídas:
- Archivo HU `21802447 (1).zip`, SHA-256 `f16adde7e9fae278de2fa5d25412533b98db91306b31e2ba637f09c05347e8f5`: SEM.dat, SEM.inp y metadatos SEM.sav.
- MEDIATICINO `Dataset_LongFormat.csv`, SHA-256 `cdfdb5b2d665efcfcc25da6337d2102877541201e7da55ff3f0e121b57f0b51e`.
- `base_principal_pmum_hu_de.md`, `auditoria_tecnica_modera_2026-10-07.md` e `invarianza_pmum_hu_de.md`, completos como antecedentes, sin convertir sus propuestas en aprobación.
- E50 PFI, PDF de 147 páginas, metadata de creación 22/08/2026, SHA-256 `861169714c20e285a99eb176eb0d2f6f868e9d9f5cd28abbc39dc4e8a9af9d6f`: páginas seleccionadas de alcance, requisitos, casos de uso y modelo. No se afirma que sea el último documento consolidado para el 15.
- Adenda F16.2: apartados de alcance y trazabilidad relevantes. Se conserva como propuesta; no se implementa la comunicación adulta.
- Publicación original PMUM de Domoff et al., copia de autora; documentación primaria NIST y scikit-learn, sólo como respaldo metodológico específico.

No se recuperó una aprobación literal y fechada de Santiago ni una respuesta nueva de Cecilia. No se afirma haber leído un chat inaccesible. El artefacto HU v1 entregado y su manifiesto original no estuvieron disponibles en este entorno: la verificación Windows previa relatada en consola es un antecedente, no una carga nueva del binario.

## Correcciones demostradas

| Hallazgo | Evidencia y corrección | Compatibilidad |
|---|---|---|
| El manifiesto aceptaba un objetivo diferente, aunque el binario declarara PMUMTotal/9 | Contraejemplo de la base; validación completa de fuente, escala, alcance, variables, conteos y fecha UTC antes de deserializar | Los once campos del manifiesto entregado permanecen válidos; no se altera el archivo |
| Conteos/códigos podían aprovechar igualdades bool/int y una predicción coercible no era necesariamente un escalar válido | Tipos explícitos, JSON estricto y tamaño limitado del manifiesto; predicción real finita de cardinalidad uno | HU v1 mantiene su estimador, categorías y respuesta |
| Recibos históricos con valor observado u outcome contradictorios podían cargarse | Contraejemplos; cotejo de ecuaciones, conteos, estado y cruce contra la referencia guardada | Misma configuración, IDs, fechas y formato persistente |
| La integridad estructural no demuestra que mediana/MAD provengan de la historia correcta | Auditoría offline de snapshot que reconstruye las referencias; prueba de falsificación coherente detectada offline | Sólo lectura; no sustituye ni reescribe ningún resultado |
| Edad JSON entera extrema causaba OverflowError/HTTP500 | Rango comprobado antes de conversión; HTTP200 con abstención, sin inferencia y conservando readiness | Mismo dominio 6–12 y mismas respuestas válidas |
| Aplicación bajo autocrlf=true convertía archivos y fallaba inventario de bytes | Conversión deshabilitada sólo para crear/aplicar en el nuevo destino; regresión Git | No cambia configuración, archivos o ramas originales |

Las pruebas incluyen manifest incompatible antes de joblib, campos ausentes/duplicados, fechas sin zona, tipos erróneos, escala de salida, historia observada adulterada, cruce contradictorio, conteos, configuración booleana, replay exacto y snapshot incorrecto. Los fixtures son ficticios y sus pruebas no acreditan el binario real.

La comprobación online de recibos aplica funciones puras con IDs/fechas originales para comparar. Nunca guarda ese objeto calculado ni avanza el estado por un reintento. No reconstruye mediana/MAD desde toda la historia en cada healthcheck: esa comprobación más costosa se ejecuta offline sobre un snapshot estable. Ninguno de esos controles es autenticación criptográfica de un archivo manipulado íntegramente.

## PMUM: conclusión metodológica

HU v1 utiliza edad, código de sexo y dos categorías parentales de tiempo de pantalla. El objetivo es PMUMTotal/9. La cohorte operativa tiene 803 casos; no se confunde con los 806 casos completos ni con la selección original de SEM.inp. Los códigos de niño son 1=varón, 2=mujer; 4=otra respuesta/no desea responder, excluido. No son una inferencia de identidad ni se imputa un código faltante.

El pipeline mantiene los transformadores dentro de cada partición; las respuestas PMUM no son entradas. La ausencia de fuga directa por esas rutas no demuestra ausencia de sesgo de selección, informante compartido o generalización.

| Procedimiento, 803 casos, OOF 5 pliegues | MAE | RMSE | R² |
|---|---:|---:|---:|
| Media del entrenamiento de cada pliegue | 0.7430 | 0.8914 | -0.0047 |
| Mediana del entrenamiento de cada pliegue | 0.7455 | 0.8971 | -0.0176 |
| Ridge fijo alpha=1 | 0.6427 | 0.7839 | 0.2231 |
| Selección interna alpha=1/10/100 | 0.6427 | 0.7826 | 0.2257 |

Los valores de MAE coinciden a cuatro decimales; los procedimientos son distintos. La selección interna eligió [1,1,1,10,1]. Las métricas anidadas describen una selección, no el único artefacto final alpha=1. El manifiesto original se conserva, acompañado por este addendum para evitar esa atribución.

El alpha fijo, las variables y el diseño se eligieron después de exploración previa; los pliegues son una comprobación interna de la misma cohorte, no un test externo nuevo. En el subgrupo operativo NoChildren=1 (n=300), el reporte recuperado registra MAE 0.6676 y R² 0.1568 para Ridge fijo. Se interpretaba como hogares con un hijo, pero la recodificación original requiere cotejo antes de asegurar esa equivalencia. En todos los casos, un 20.92% de los errores OOF fijos superó un punto de la escala; esto es un descriptivo de error, no un corte clínico. Tampoco la cercanía de medias por grupos de predicción acredita utilidad individual o grupal fuera de la cohorte. El bloque 2A confirmó fuente/cohorte/particiones, sin recalcular esas métricas.

No se reprodujo el entrenamiento final que produjo los bytes entregados ni se leyó su pipeline original aquí. El verificador offline exige la huella registrada, examina el pipeline y sus categorías, verifica 350 combinaciones enteras y dos edades fraccionarias, y conserva ambos originales. También comprueba indirectamente la referencia 2.6959 al construir `CachedPmum`; el recorrido HTTP la comprueba por separado. La nueva carga fue ejecutada por Matías y su resumen registra pmum_original_artifact=PASS y original_pmum_artifact_loaded=true, además de HTTP Windows/Docker PASS. El original y los logs detallados no se cargaron aquí. Ese recorrido confirma contrato y comportamiento numérico; no reemplaza validación externa ni demuestra por sí solo la procedencia de cada coeficiente.

## C1: conclusión metodológica

La API procesa duración diaria v2, con identidad ligada a la asignación de dispositivo/sujeto y versión de medición conforme al preparador. C1 compara un valor admisible con mediana y 1.4826*MAD de valores anteriores. La API candidata elige `all_prior_usable_records_v1`: admite también valores anteriores que generaron CHANGE. No se agregó una ventana o un reinicio nuevo.

MISSING y NOT_APPLICABLE se abstienen y no avanzan CUSUM; los valores admisibles durante el inicio pueden formar referencia. Cero observado es distinto de ausencia. Un MAD cero produce referencia no estimable; no se inventa un piso. Se toleran gaps sin imputarlos. El cruce es un evento técnico, no inicio, duración, causa o gravedad de un episodio.

La reauditoría final volvió a ejecutar F12-C2 completo y obtuvo un JSON idéntico al publicado y al recuperado. El bloque 2B recontó la fuente: 2.587 filas y 93 participantes, de los cuales 75 aportan 1.836 ventanas y 14.688 escenarios dependientes/reutilizados. Las perturbaciones duran tres registros observados: 285 ventanas tienen saltos de DayInStudy trasladados a fechas artificiales del runner. No se valida el calendario real Android. La referencia usa sólo fondo real previo, excluyendo perturbaciones de referencias posteriores, a diferencia de la adaptación de la API. La equivalencia del fenómeno de duración con reconstrucción interactiva Android no se presume. Los offsets cuentan registros, no días; las tasas excluyen excedencia preexistente y no son tasas del emisor. En el primer dato elegible puede haber cruce experimental pero NO_EMIT por estadístico anterior None. No se evalúa toda la API/captura ni se preservaron registros individuales de escenario en el JSON.

No hay etiquetas independientes de necesidad clínica/cambio real para sensibilidad, especificidad o falsa alarma. Las tasas de cruces de control no se presentan como FPR. El CSV contiene edades codificadas entre 0 y 17; no se interpreta 0 ni se atribuye a toda la muestra un rango 13–16 o 6–12. Las garantías clásicas CUSUM bajo referencia/distribución especificadas no se transfieren automáticamente a esta referencia robusta adaptativa.

Quedan por justificar para uso real: selección de historia, calidad/cobertura, madurez, k/h, conducta ante gaps y cambios de medición, frecuencia de cruces y condiciones de comunicación. La API ya obliga configuración explícita. El perfil SMOKE_ONLY sólo prueba funcionamiento y permanece separado de cualquier perfil de producto.

## Pruebas y estado

La ejecución recuperada registró 323 pruebas de tests/ y 15 de raíz; el bloque 1 registró 325. La reauditoría final ejecutó 332 casos de tests/ y 15 de raíz sobre la copia aplicada desde 60c8764, incluidos siete ensayos Git de aplicación; también ejecutó seis scripts heredados. Los casos focalizados y scripts no se suman a la suite. El baseline era 305. Ver evidence/technical_validation.json y logs del paquete para alcance, fuentes probadas y pendientes.

Se ejecutó HTTP nativo: export ficticio→preparador→v2→API, persistencia, terminación del proceso, reinicio y replay, conflicto 409, autenticación 401, abstenciones y coexistencia PMUM/C1 con predictor ficticio. El archivo histórico quedó byte a byte intacto en replay. La auditoría completa de sus referencias pasó; la carga de una copia adulterada falló sin reescribirla.

Windows/Docker del candidato nuevo fueron ejecutados por Matías: 332 casos (331 aprobados, uno omitido), 15 de raíz, seis scripts y etapas HTTP/Docker PASS, según consola y resumen aportados. La omisión es consistente con un caso exclusivo de POSIX en el código; el resumen no identifica su nombre. Ver el registro separado de procedencia y límites. Los 305 casos de la entrega 60c8764 (304 aprobados y una omisión), 15 de raíz, seis scripts y HTTP/Docker informados por Matías corresponden a esa base y no se reasignan al nuevo parche. La advertencia Starlette/httpx observada no fue un fallo de pruebas; no se cambian dependencias por esa deprecación.

## Cierres y pendientes indispensables

| Parte | Estado | Responsable y criterio |
|---|---|---|
| Contratos, guardas PMUM/C1 y herramientas de auditoría | Linux y recorrido Windows/Docker PASS | Cierre técnico según consola/resumen recibidos; no validación científica de producto |
| Fuente y evaluación PMUM/C2 | Probada en las condiciones declaradas | Evidencia reproducida en JSON, fuentes con SHA |
| Binario HU v1 en esta nueva versión | Verificador y HTTP Windows/Docker PASS | Original cargado en entorno de Matías; no reproducido su entrenamiento final |
| Entrenamiento final/validación externa PMUM | Pendiente de evidencia | Equipo: trazabilidad del ajuste original y evaluación independiente antes de ampliar uso; no es requisito para afirmar sólo candidato interno |
| Formulario parental para uso real | Pendiente de evidencia y decisión | Recuperar redacción completa weekday y revisión de adaptación; mantener pruebas ficticias mientras falte |
| C1 con perfil de producto | Pendiente de decisión y evidencia | Equipo y revisión metodológica: protocolo/objetivo y población, evaluación independiente, criterios de calidad y parámetros justificados |
| Documento final de tesis | Propuesta revisable | Matías y dirección: integrar texto contrastado con E50 y verificar versión consolidada |
| Conexión backend real | Pruebas informadas por Juanma; evidencia independiente pendiente | Backend/equipo: aportar resultados/código; la integración F12 y los acuerdos de cierre/identidad no quedan acreditados por ese mensaje |

No se reabre la persistencia, el writer lease, el replay o la configuración explícita ya cerrados; se les agregan guardas de integridad. El preflight existe. Juanma informa persistencia previa al HTTP, idempotencia, retry tras caída y conflictos del backend; no se acredita aquí su implementación ni el cierre diario F12 por no haber auditado su código o evidencia. La captura física y la revisión de catálogo se mantienen como pendientes anteriores, sin prioridad en este bloque.

Recomendación para el 15: presentar una versión interna estable con sus evidencias y restricciones, conservar HU v1 y las políticas C1 actuales y declarar los límites abiertos. No reemplazar esos límites por un perfil calibrado ficticio. El texto de tesis es una propuesta para aprobación académica; no se modifica automáticamente E50.

## Lecturas relacionadas

- [Contrato PMUM/C1](PMUM_C1_CONTRACT_2026-10-12.md)
- [Matriz de afirmaciones](METHOD_CLAIMS_MATRIX_2026-10-12.md)
- [Propuesta para tesis](THESIS_MODEL_TEXT_PROPOSAL_2026-10-12.md)
- [Fuentes y reproducción](SOURCES_AND_REPRODUCTION_2026-10-12.md)
