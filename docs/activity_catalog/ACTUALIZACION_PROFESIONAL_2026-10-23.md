# Incorporación de la revisión profesional de actividades

Base comprobada: `1445056ad13728fba5aaabec6a61aa9bbd1730c3`, disponible en el
repositorio de Moderá. Rama nueva: `activity-catalog-professional-review-candidate`.
Se conservan las ramas y los archivos de evidencia anteriores. Esta entrega no
publica, fusiona ramas ni despliega.

## Cambios

Se incorporan las correcciones recibidas de Cecilia el 22/10 mediante Word y PDF.
Se utiliza el PDF como referencia visual y se conservan los párrafos y colores
del Word en `evidence/2026-10-23/professional_source_transcription.json`.
Los originales se identifican por nombre y SHA-256 en el manifiesto de revisión.
Los textos originales negros son antecedentes, no una segunda consigna que deba
mostrarse al niño. Las correcciones profesionales se normalizan en tildes, voseo,
puntuación y frases incompletas; las decisiones adicionales quedan registradas.

El catálogo pasa de 18 a 16 actividades. Los materiales obligatorios y opcionales
se distinguen y las consignas incluyen ejemplos para empezar. Se conserva la
posibilidad de no elegir. No se implementa audio guiado ni reproducción de música.

| Propuestas del documento | Decisión |
| --- | --- |
| 4 y 7: personaje e historia | Se integran en `creative_character_story_01`. |
| 14 y 16: conversación e historia acompañada | Se integran en `social_conversation_story_01`, con otra persona requerida. |
| 6 y 18: dibujo | Una familia editorial, dos variantes técnicas: `creative_favorite_01` para pausa y `quiet_draw_01` para descanso. Los contextos de selección no se superponen. |
| 10, 11 y 12: juegos | Se conservan separadas. La agrupación era opcional y las tareas y materiales son distintos. |
| 20: mímica | Se incorpora como variante explicada dentro de `social_play_01`. No agrega otra actividad al catálogo. |
| 19: figura de papel | No se incorpora automáticamente: barco/sombrero presuponen una técnica cuyo paso a paso no estaba incluido. Se mantiene la construcción con bloques/cajas. |
| 21: ritmo | Continúa excluida. La devolución no la reincorpora ni aclara la objeción anterior. |
| Baile | Se incorpora la invitación y los ejemplos sin exigir ser el mejor. El ajuste de título es editorial, no una conclusión de eficacia. |
| Dibujo | Se conserva papel y lápices. No se añade la variante opcional de pintura con otros materiales. |

La secuencia de movimientos admite música opcional desde el celular. Por eso
`may_require_device_interaction` pasa a `true` también en esa actividad. Baile
conserva su indicador. El filtro existente puede excluir ambas si se pide no
ofrecer propuestas con posible interacción con el dispositivo. Esto no significa
que música o celular sean obligatorios para realizarlas.

## Identidad y filtros

Los cuatro IDs que se fusionan se retiran de nuevas selecciones, sin sustituirlos
en registros anteriores. Siguen aceptados al leer y responder a ofertas antiguas.
Los dos IDs retirados en la entrega anterior también se conservan.

| Nuevo ID | Predecesores retirados |
| --- | --- |
| `creative_character_story_01` | `creative_character_01`, `creative_story_01` |
| `social_conversation_story_01` | `social_talk_01`, `social_story_01` |

Si un filtro explícito excluye cualquiera de los predecesores, también excluye
la propuesta fusionada. Esto se aplica al construir `ActivityEligibility`, de
modo uniforme en selección directa, HTTP y reconciliación del coordinador.
Versión de esa compatibilidad: `explicit-exclusions-merged-activities-v1`.
No se deducen restricciones a partir de un diagnóstico o de texto libre.

No son alias: una elección antigua de historia no se convierte en una selección
de la actividad nueva ni le transfiere contadores de preferencia. Los datos y
los recibos anteriores mantienen ID, contenido, versión y fechas originales.
Una oferta pendiente con IDs retirados no se sustituye ni vuelve a presentarse
mediante una evaluación nueva; conserva la supresión y reconciliación existentes.
El replay de una petición ya comprometida recupera su recibo original.

`/v1/activities/eligibility` conserva su contrato. Una consideración distinta de
`none` sigue devolviendo `unknown` y seguimiento. La revisión profesional de
consignas no implementa el mapeo de `activities_to_avoid`, fechas o notas del
backend. Tampoco acredita disponibilidad de materiales, compañía o acceso a UI.

El algoritmo, los pesos y la huella del selector permanecen iguales. Cambian
el catálogo, su huella y la compatibilidad de exclusiones explícitas por fusión.
La selección de nuevas actividades puede cambiar por el contenido, los IDs y la
semilla ligada a la huella. No se ajustó el ranking para obtener resultados mejores.
No cambian PMUM, C1, ventanas adultas, reglas del coordinador ni límites HTTP.

## Qué debe actualizar la integración

1. Reconstruir únicamente la imagen de Analytics desde esta versión, con el mismo
   volumen y secreto del despliegue. Hacer antes un respaldo consistente y conservar
   la imagen anterior. No borrar bases, marcas de inicialización ni volúmenes.
2. Conservar la configuración actual de AWS. Esta actualización no pide habilitar
   PMUM o C1. No reemplazar el Compose real por la plantilla local: esa plantilla
   habilita C1 exclusivamente para comprobaciones SMOKE_ONLY.
3. Consumir los 16 títulos y descripciones de la API. Si existen listas o cachés
   fijas en backend/Android, actualizar sus entradas para nuevas ofertas, conservando
   las selecciones e IDs históricos. Mantener saltos de línea y consignas completas.
4. Usar el texto inicial de `CHILD_ACTIVITY_INTRO_TEXT` o del manifiesto en el
   recorrido infantil. El texto común no es un campo nuevo de la API ni se muestra
   automáticamente por actualizar el contenedor. No repetirlo dentro de cada tarjeta.
5. Mantener separados selección, confirmación de entrega y realización. Esta
   entrega no agrega un evento que demuestre que el niño completó la actividad.

Los cuerpos HTTP y los campos de actividad se conservan. No hace falta una
migración de las bases de Analytics. La actualización de datos o listas propias
del backend debe respetar sus asociaciones e historial, sin reetiquetar registros.

## Comprobación en Windows

Después de importar el bundle en una carpeta nueva, desde esa carpeta:

```powershell
$professionalPython = 'C:\tesis_mensajes_adulto_v1\.venv\Scripts\python.exe'
& $professionalPython -X utf8 -m pytest -q tests/test_activity_professional_review.py tests/test_activity_catalog_revision.py tests/test_child_offer_api.py tests/test_child_offer_coordinator.py tests/test_analytics_api.py tests/test_integration_closure.py::ConditionsCombinationsTests test_child_choice_signals.py test_recommendations.py --junitxml=actividades_profesional_focal_windows.xml
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas focalizadas.' }

$professionalEvidence = Join-Path $PWD ('comprobacion_profesional_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
& $professionalPython -X utf8 tools/validation/verify_activity_professional_revision.py --output-dir "$professionalEvidence"
if ($LASTEXITCODE -ne 0) { throw 'Falló el cotejo del catálogo.' }

$professionalHttp = Join-Path $PWD ('ensayo_profesional_http_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
& $professionalPython -X utf8 tools/validation/verify_analytics_service_integration.py --output-dir "$professionalHttp"
if ($LASTEXITCODE -ne 0) { throw 'Falló el ensayo HTTP nativo.' }
```

El primer verificador exporta `report.json` y `catalogo_para_revisar.md`, con las
16 consignas recibidas por HTTP. El segundo inicia un proceso local independiente
con datos ficticios y comprueba persistencia y reintentos. No usa datos ni bases
del contenedor existente. Las carpetas de salida deben ser nuevas.

No es necesario repetir en Windows la regresión completa antes de este primer
cotejo focalizado. Si se ejecuta, usar el comando de la entrega anterior desde
este worktree, incluyendo `test_intervention_history_reader.py`, y guardar una
evidencia nueva. Revisar después `git status`: algunos tests heredados agregan
registros ficticios a `data/intervention_history.jsonl`; conservarlos antes de
restaurar solo ese archivo, si corresponde. No restaurar cambios ajenos.

## Alcance de la revisión profesional

Puede describirse que las actividades se sometieron a revisión profesional y
que se incorporaron correcciones de claridad, materiales, ejemplos y organización.
No se acredita aprobación clínica, adecuación individual a cualquier condición,
comprensión observada con niños o reducción demostrada del uso de pantallas.
Los ajustes editoriales y técnicos de esta entrega no se atribuyen literalmente
a Cecilia. No se requiere otra revisión completa para incorporar su devolución.
