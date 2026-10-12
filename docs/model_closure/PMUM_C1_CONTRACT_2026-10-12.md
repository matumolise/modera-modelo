# Contrato conservado y comprobaciones nuevas

Base: 60c8764. Este documento complementa las guías de integración; no cambia schemas HTTP, versiones de modelos, parámetros o respuestas válidas.

Estado: contrato recuperado y revisado, incluido en el paquete final propuesto. El aplicador está preparado y ensayado en su núcleo Git; la validación Windows/Docker y HU original siguen pendientes de ejecución.

## PMUM HU v1

`POST /experimental/pmum-estimate`, con Bearer del servicio y JSON. Las seis entradas son obligatorias; no admite campos nuevos:

```json
{"age":9,"sex_code":1,"weekday_category":2,"weekend_category":3,"respondent":"parent_or_caregiver","reference_days":30}
```

Respuesta de referencia del original entregado: `estimated_pmum_sf_mean=2.6959`, `model_version=hu_pmum_sf_experimental_v1`, `experimental=true`, `use=internal_research_only`. La API devuelve HTTP 200 para estimación y abstención funcional; no devuelve un cero al abstenerse. Sin credencial: 401. Un fallo técnico del modelo es 503 y degrada su disponibilidad; no se disfraza como respuesta parental faltante.

| Campo | Dominio / evidencia | Límite |
|---|---|---|
| age | Número finito de 6 a 12 inclusive, incluidos decimales de la fuente | No redondear automáticamente 6.5/8.5 ni ampliar edades |
| sex_code | Entero 1=varón, 2=mujer, según código fuente del niño | 4=otra respuesta/no desea responder; null/4 se abstienen. No inferirlo ni trasladar el código del cuidador |
| weekday_category | Entero 1 a 5 de pregunta parental weekday | Nombre indica últimos 30 días; redacción completa truncada en SAV. No afirmar TV/total sin recuperar esa pregunta |
| weekend_category | Entero 1 a 5, día promedio de fin de semana en últimos 30 días | Etiqueta fuente especifica total y teléfono, tablet, computadora, consola y TV |
| respondent | parent_or_caregiver | No aceptar autorreporte infantil como equivalente |
| reference_days | Entero 30 | true y 30.0 no cumplen contrato |

Ambas categorías conservan: 1=<1 h, 2=1–2 h, 3=3–4 h, 4=5–6 h, 5=7 h o más. Los huecos no se rellenan con puntos medios ni se convierten en minutos Android. El preprocesamiento usa one-hot; no supone distancias numéricas entre categorías. La fuente pide elegir al hijo de 6–17 que más pantallas usa; la cohorte del candidato filtra 6–12. No es una muestra aleatoria de todos los niños del hogar.

Los nueve ítems PMUM pertenecen al objetivo del dataset; el endpoint de cuatro características no administra esos nueve ítems ni reconstruye una puntuación observada. El significado general de la escala no valida esta regresión.

Razones de abstención conservadas: `invalid_request`, `unexpected_field`, `missing_parent_answer`, `missing_required_field`, `respondent_mismatch`, `reference_period_mismatch`, `invalid_feature_value`. La precedencia permanece igual: por ejemplo, omitir una categoría parental produce missing_parent_answer; sex_code=null con otras respuestas presentes produce invalid_feature_value.

Una edad entera fuera de 6–12 se abstiene con `invalid_feature_value`, incluso si es demasiado grande para convertirse a float. Un número admitido por el parser JSON no implica que pertenezca al dominio del modelo. El cuerpo excesivo o un JSON no finito conservan sus errores de transporte; no se cambia esa precedencia.

### Artefacto y manifiesto

SHA registrado del joblib: `56c991f40e56d2241196dc6f9efc1c9027c079e98a1b67549f48b10292e371e0`. El servicio sigue verificando la huella confiable antes de deserializar y cargando los mismos bytes cotejados. Se exige manifiesto JSON estricto de hasta 64 KiB, con los once campos del original:
`model_version, source, source_sha256, created_utc, features, target, n_trained, sex_code_4_excluded, regularization, evaluation, deployment_status`.

Fuente `Zenodo 21802447 / SEM.dat`; target `PMUM-SF mean, 1 to 5`; n_trained=803; sex_code_4_excluded=3; fecha UTC; estado `NOT APPROVED; no app integration`. El artefacto debe concordar con fuente, versión, entradas, n=803, sex_codes=[1,2] y target=PMUMTotal/9. Los conteos/códigos no aceptan booleanos como enteros. Se preserva el texto histórico de evaluation; su frase “Nested cross-validation” describe selección exploratoria, cuya separación del Ridge fijo se documenta en el addendum, sin alterar el manifiesto original.

`regularization` y `evaluation` son descripciones históricas de texto libre. La guarda exige que existan y sean textos no vacíos acotados, pero no certifica su veracidad. La coherencia del ajuste se coteja con código/pipeline y evidencia independiente. El verificador offline comprueba alpha=1; `CachedPmum`, que utiliza ese verificador, comprueba además la referencia 2.6959 al cargar. El recorrido HTTP la confirma por separado. Ninguna de esas comprobaciones reproduce el entrenamiento ni valida externamente la estimación.

Arranque con PMUM habilitado e inconsistente: falla. Modelo deshabilitado: servicio puede ejecutar C1/actividades sin joblib HU. Ninguna salida PMUM determina C1, actividades, alertas o frecuencia.

## Histórico C1

Se conservan [contrato backend/F12](../integration/BACKEND_F12_C1_CONTRACT_2026-10-12.md), [API histórica](../integration/HISTORICAL_API_CANDIDATE_2026-10-11.md) y [cierre diario](../integration/DAILY_EVIDENCE_CLOSURE_2026-10-12.md).

Entrada: request_id + representación v2. La serie del preparador liga device/profile/assignment, zona y versión de medición; la API recibe su subject_id estable y verifica spec/fenómeno/unidad/intervalo. subject_id por sí solo no acredita vinculación familiar: esa asociación corresponde al backend, no leído aquí.

Intervalos aware y cerrados al preparar, duración no superior a su intervalo, orden cronológico por serie y sin solapamientos. El preparador debe respetar límites diarios locales (incluidos días 23/25 h) y convertirlos a instantes aware. No hay cambio de zona silencioso dentro de una identidad congelada.

Falta de export no acredita captura ausente; se conserva la distinción en el preflight. MISSING no equivale a cero. Las consultas vacías y sin evidencia suficiente no prueban duración nula ni cobertura completa. Calidad y cobertura quedan registradas; la política candidata todavía no impone un umbral de cobertura o exclusión de flags de producto.

Perfil obligatorio: configuration_id, scope, spec, reference_policy, analysis/emitter_version, k, threshold y min_history; el archivo ejemplo con null no habilita C1. El fixture smoke (k=.5, threshold=3, min_history=3) es ficticio, no una recomendación. La huella del perfil liga el repositorio; modificarlo impide cargar el historial con la configuración distinta.

La API candidata aplica todos los registros anteriores admisibles de la misma serie. Referencia: mediana y 1.4826*MAD. En cada dato elegible:
`z=(x-mediana)/escala`,
`G+=max(0,G+prev+z-k)`,
`G-=max(0,G-prev-z-k)`,
`score=max(G+,G-)`.
No se reinicia tras CHANGE. El emisor crea un evento técnico al cruce ascendente respecto del estadístico elegible previo; no implica alerta familiar ni actividad. MISSING/no aplicable o historia insuficiente se abstienen; el último valor admisible puede formar referencia aunque el detector se haya abstenido por inicio.

### Persistencia y reintentos

Un solo escritor de archivo por proceso/volumen, worker único y exclusión entre threads; reemplazo atómico de representación, resultado, estado y vínculo. No asumir que un archivo/lease equivale a un backend distribuido o a tolerancia a pérdidas de disco sin backups.

Mismo ID con payload compatible devuelve el recibo original (incluidos IDs/fechas) sin avanzar. Un conflicto devuelve 409; no se resuelve creando IDs para eludirlo. La evidencia tardía después de congelar/procesar no modifica el recibo: la política de corrección sigue pendiente, sin plazos inventados.

El adaptador valida ahora las ecuaciones del recibo contra su referencia guardada y su cadena de estado. Un recibo contradictorio no carga ni se reescribe. Health/live confirma proceso; health informa capacidades y el estado de integridad verificado, no calibración ni integridad criptográfica absoluta. Para mediana/MAD contra toda la historia usar auditoría offline:

```powershell
.\.venv-historical\Scripts\python.exe tools/validation/audit_c1_repository.py --repository RUTA_SNAPSHOT --config RUTA_PERFIL --output NUEVO_REPORTE.json
```

Copiar repositorio y perfil después de detener el escritor o tomar un snapshot consistente. La herramienta no crea locks ni cambia fuentes; compara bytes al terminar y exige salida nueva. Recalcular para cotejar es distinto de sobrescribir resultados o reanalizar un reintento. El perfil de producto requiere evidencia propia.
