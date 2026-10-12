# Entrega candidata de integración: backend, F12, C1 y condiciones

Base publicada: `26654b64c88a8034d8dc5f86d724c0af299bc546`.
Rama candidata de entrega: `analytics-integration-handoff-candidate`.
Preparada mediante parche sobre la base publicada, en un worktree separado.
Las ramas `analytics-api-candidate` y `analytics-historical-candidate` se conservan.
Esta entrega no hace merge, no despliega AWS y no activa alertas o intervenciones.

## Auditoría de lo disponible

| Parte | Implementado | Evidencia | Lo que no está cerrado |
|---|---|---|---|
| PMUM experimental | Endpoint independiente; modelo externo, hash y manifiesto; sin uso en actividades | Artefacto real probado por Matías en la entrega original | Uso con familias y validación externa; artefacto real no se probó en esta ampliación |
| Histórico | Representación v2, perfil C1 explícito, recibos originales y estado persistentes; exclusión entre escritores | Base 26654b6: Windows y Docker PASS según consola y resumen compartidos | Configuración de producto, medición física y conexión con backend |
| F12 | Adaptadores raw → observación → v2 existentes; puente offline añadido | Casos fabricados que recorren preparación y API | Paridad con el collector real y asignación de dispositivo en el backend |
| Actividades | Selector original 0..3, filtros explícitos, resolución candidata del formulario | Pruebas nuevas y misma huella de selección de referencia | Mapeo funcional por actividad y revisión profesional |
| Ofertas y tarjetas | Antecedentes y propuestas documentadas | Lectura de código y documentos del proyecto | Entrega visual, política aprobada, persistencia de flujos y recomendaciones aprobadas |

Se verificó el commit publicado y los bytes de 114 archivos utilizados contra
sus SHA de blob Git. Es un snapshot acotado, no un clon completo. La búsqueda del
chat anterior devolvió un error; no se afirma haber leído todos los mensajes de
Juanma. La solicitud de opciones del formulario se conserva tal como aparece en
el contexto visible. `JUANMA_INTEGRATION_HANDOFF_DRAFT.md` es un antecedente del
servicio local PMUM y no es la configuración actual de autenticación/despliegue.

## Dueños y frontera de confianza

| Componente | Responsabilidad |
|---|---|
| Android | Capturar eventos y evidencia de consultas, preservar originales; no declarar quién miró la pantalla por SCREEN_INTERACTIVE |
| Backend autenticado | Autorizar adulto/perfil; vincular instalación/dispositivo y asignación; fijar zona y versión de medición; conservar el payload antes de enviarlo; ordenar por serie |
| Preparador Python | Validar una proyección del registro F12, reconstruir con los adaptadores publicados y producir el payload; sin red ni persistencia del histórico |
| Analytics | Validar el contrato v2 y el perfil C1; procesar una vez, persistir representación/recibo/estado y recuperar el resultado original |
| Producto/profesional | Resolver condiciones y adaptaciones, parámetros de uso real, comunicabilidad e intervención |

El token de analytics autoriza al backend como servicio; no verifica por sí mismo
la titularidad de `subject_id`. La asociación debe venir del contexto autenticado
del backend, nunca de un identificador arbitrario enviado por Android.

## Identidad propuesta para series nuevas

El preparador requiere cinco campos de serie: `profile_id`, `device_id`,
`assignment_id`, `time_zone` y `measurement_version`. Todos salvo la zona usan
identificadores opacos ASCII compatibles con el contrato; no nombres del niño.
Los IDs deben ser globalmente únicos dentro del despliegue o incorporar un
namespace de cuenta/tenant asignado por el backend. Contadores locales como
"perfil 1/dispositivo 1" repetidos entre cuentas no aíslan series.

`subject_id` se deriva con SHA-256 del objeto de vinculación, versión del puente y
versión de tzdata. Representa una serie de medición asociada a un perfil y aparato,
no acredita uso exclusivo del niño. El backend conserva la tabla reversible de
asociación con sus IDs; el hash no es una garantía de anonimato.

Cambiar dispositivo, asignación, zona, semántica de medición, puente o base de zonas
inicia una serie distinta en este candidato. No mezclar teléfonos ni trasladar
estado CUSUM entre series. Reinstalar no debe generar IDs nuevos en cada consulta:
el backend decide cuándo la instalación sigue representando el mismo aparato y
cuándo cambia la asignación. Esta propuesta no migra series existentes: si ya hay
históricos asociados a `subject_id` anterior, revisar una transición explícita.

En teléfono compartido se puede auditar una serie del dispositivo; no comunicar
sus minutos como tiempo atribuible al niño. La tarjeta adulta queda fuera de esta
entrega. Falta acordar con Juanma la clave de asignación y si ese dato existe.

## Preparación de un día local

El archivo de entrada tiene exactamente:

```json
{
  "schema_version": 1,
  "request_id": "preparation-example-01",
  "series": {
    "profile_id": "profile-test",
    "device_id": "device-test",
    "assignment_id": "assignment-test",
    "time_zone": "America/Argentina/Buenos_Aires",
    "measurement_version": "capture-test-v1"
  },
  "local_date": "2026-09-01",
  "computed_at": "2026-09-02T03:02:00+00:00",
  "raw_events": [],
  "summaries": []
}
```

Las listas vacías en este ejemplo producen `MISSING`, no cero observado.
Un caso fabricado con evidencia completa está en
`tests/fixtures/integration/f12_preparation_synthetic.json`; su payload está en
`f12_request_synthetic.json`. No son datos reales de niños.

Cada fila de `raw_events` usa los nueve campos del contrato
`RawAndroidUsageEvent`: `schema_version`, `collector_run_id`,
`query_begin_epoch_ms`, `query_end_epoch_ms`, `collected_at_epoch_ms`,
`event_time_epoch_ms`, `event_type_code`, `event_type_name`, `query_ordinal`.
Los resúmenes usan los nueve campos de `AndroidCollectorRunSummary`:
`collector_run_id`, `requested_begin_epoch_ms`, `requested_end_epoch_ms`,
`collected_at_epoch_ms`, `usage_access_available`, `query_returned_null`,
`event_count`, `error_code`, `error_message`.

Es una proyección snake_case preparada desde el export diagnóstico. No es un
parser del JSON/CSV completo Android ni modifica el registro crudo: conservar los
originales con campos extra (package/class/etc.) por separado. La proyección
conserva todos los tipos de evento necesarios para verificar `event_count`;
no filtrar primero solo SCREEN_INTERACTIVE/NON_INTERACTIVE. El preparador no
verifica criptográficamente que todos los registros pertenezcan al dispositivo
declarado; lo hace el vínculo de origen que debe controlar el backend.

Se requieren tipos exactos, counts y asociaciones de queries consistentes; bool
no vale entero. Una inconsistencia se rechaza como preparación inválida. Una
consulta fallida sin datos o captura insuficiente produce `MISSING`; no se imputa.
Códigos Android 15/16 corresponden a SCREEN_INTERACTIVE/NON_INTERACTIVE, y 26/27 a
DEVICE_SHUTDOWN/STARTUP. Se rechaza desacuerdo entre código y nombre reconocido.

El día es `[medianoche local, medianoche local siguiente)`. Se convierten ambos
límites a UTC antes de reconstruir; no se impone una duración de 24 horas. Una
medianoche ambigua o inexistente falla explícitamente hasta definir esa política.
Solo se preparan días cerrados según `computed_at`; el reloj del backend debe ser
fiable. Zona o datos IANA ausentes no se sustituyen por UTC ni por la zona del PC.

El paquete tzdata se fija en `requirements-integration-tools.txt`; se usa su base
de datos directamente, sin alterar TZPATH global. La dependencia solo corresponde
al preparador y sus pruebas, no al servidor actual. Se incorpora su versión a la
identidad de serie. Al actualizarla, evaluar si corresponde cambiar la serie.

El núcleo exige consultas exitosas con cobertura continua hasta el estado previo
que permite fijar el límite inicial. Esto no garantiza exhaustividad absoluta de
Android. `coverage.value` permanece `null`, con la base publicada
`daily_capture_completeness_not_quantified`; no se inventa un porcentaje.

Si se observa startup/shutdown dentro de la evidencia necesaria, el puente marca
`MISSING` con `DEVICE_LIFECYCLE_REVIEW_REQUIRED`: el núcleo v2 no demuestra
continuidad a través de un reinicio. No reconstruye arbitrariamente ese tramo.

## Comando offline

```powershell
.\.venv-historical\Scripts\python.exe -m pip install -r requirements-integration-tools.txt
.\.venv-historical\Scripts\python.exe tools/integration/build_historical_request.py `
  --input tests/fixtures/integration/f12_preparation_synthetic.json `
  --output "$env:USERPROFILE\Documents\modera_f12_request_synthetic.json"
```

No envía solicitudes. El archivo de salida debe ser nuevo; no sobrescribe un
payload anterior. Para uso real, conservarlo en la persistencia del backend, no
usar carpetas personales como infraestructura. El preparador no se expone como
endpoint ni se ejecuta automáticamente en la imagen de analytics. Si el backend
no usa Python, acordar un job de preparación o implementar un adaptador equivalente
verificado con los mismos fixtures; no duplicar fórmulas sin prueba de paridad.

## Envío, orden y reintentos

`POST /v1/historical/evaluate` conserva el contrato:

```json
{
  "request_id": "transport-example-01",
  "representation": "objeto completo producido por el preparador; ver fixture JSON"
}
```

El ejemplo anterior solo indica la envoltura: `representation` debe ser un
objeto, no esa cadena. El fixture contiene la solicitud completa ejecutable.
No enviar `series`, raw, resúmenes, PMUM ni v3 al endpoint existente.

Protocolo propuesto de outbox, cuyo dueño es el backend:

1. Preparar, autorizar asociación y guardar el payload completo e inmutable,
   `representation_record_id`, clave de serie, intervalo y configuración esperada.
2. Enviar en orden creciente por intervalo dentro de cada serie, serializando
   también los envíos de productores distintos. El bloqueo de analytics protege
   el archivo, pero no ordena la llegada de varios días por el backend.
3. HTTP 200 `processed`: guardar el `result` íntegro (incluye IDs/fechas originales),
   estado de replay y configuración. `ABSTAIN` también es un procesamiento
   persistido y reconocido, no un error para reintentar hasta obtener CHANGE.
4. Timeout, desconexión o 503: la entrega puede haberse comprometido; conservar
   como pendiente y reintentar el MISMO payload/ID. No recalcular el día con un
   export nuevo. La política de backoff/cantidad de reintentos es del backend.
5. `409 representation_conflict`: cuarentena/revisión, nunca generar otro ID para
   el mismo día con el fin de eludir el conflicto. La API no corrige historia.
   `409 historical_order_conflict`: revisar el orden y períodos solapados.
6. 400/401/413/415: corregir contrato, credencial o transporte; no reintentar sin
   cambios como si fuera un fallo transitorio. Registrar motivo sin datos sensibles.

La representación recibe un ID estable por serie e intervalo; la huella de la
procedencia identifica la evidencia completa. Evidencia corregida del mismo día
conserva el ID, cambia la huella y produce 409 si ya fue procesada. El único campo
ignorado para compatibilidad por el núcleo es `computed_at` de la representación.
Reintentar con otro `request_id` de transporte no cambia los IDs/fechas del resultado.

Este documento especifica la outbox; no implementa la base de datos de Juanma,
no garantiza entrega exactamente una vez en todo el sistema ni registra ofertas.

## C1 y configuración

No se cambian k, threshold, min_history, análisis, emisor ni almacenamiento.
El servicio exige un perfil completo y lo vincula al repositorio. El fixture
`smoke-only-not-calibrated` sirve solo para pruebas. El ejemplo de perfil con
números null sigue siendo intencionalmente no ejecutable.

La única referencia admitida es `all_prior_usable_records_v1`: las observaciones
previas aptas, sin el día actual. Cero observado puede entrar; MISSING y
NOT_APPLICABLE no aportan valor. El núcleo no aplica un umbral de coverage ni una
lista de flags como política de calidad: la preparación debe marcar faltante
cuando no puede acreditar la observación. Unknown coverage no se convierte en 1.

Cambiar configuración exige otro repositorio o una migración explícita. No
cambiar el perfil montado esperando hot reload. No resetear ni rearmar el CUSUM
para hacer coincidir una tarjeta semanal; ningún CHANGE equivale a riesgo,
diagnóstico, notificación o recomendación aprobada.

## Formulario y selector

Contrato añadido, autenticado con el mismo token y sujeto a los mismos límites:

```json
{
  "request_id": "form-example-01",
  "considerations_state": "known",
  "conditions": ["mobility_both", "visual"]
}
```

Se envía a `POST /v1/activities/eligibility`. En este caso devuelve estado unknown,
`functional_mapping_required` y temas de seguimiento. No devuelve `eligibility`.
Para unknown se omite conditions. Para Ninguna se usa exclusivamente `["none"]`,
que devuelve known y `{}`. Una lista vacía con estado known es inválida.

El backend arma DESPUÉS el cuerpo de `/v1/activities/select` con request_id,
context, intereses/recientes opcionales y el estado consolidado. No copiar la
respuesta completa del resolver al selector: mapping_version y followups no son
campos de ese contrato. Si el estado consolidado es unknown, omitir eligibility.
Si es known, combinar los filtros explícitos adicionales aplicables.

Ninguna informa únicamente sobre las consideraciones declaradas: no acredita
materiales, apoyo disponible o seguridad de las actividades restantes. El backend
no debe convertir ese resultado en known si conoce otra restricción aún sin resolver.
La matriz `CONDITIONS_MAPPING_2026-10-12.md` detalla las 18 actividades y la propuesta
para cerrar el formulario. El selector original y catálogo se conservan.

## Dependencias de ofertas y tarjetas, sin activación

Las bibliotecas de intervención existentes registran generación y respuestas
vinculadas cuando se usa el flujo nuevo. Una oferta registrada no prueba entrega
visual; elegir no prueba realizar. El endpoint de selección no crea offer_id.

El documento de ofertas automáticas propone límites compartidos y cooldown fijo
sin PMUM, separación entre diurno/descanso y medición en tiempo real en Android.
Sus cifras son candidatas, no defaults aprobados de esta entrega. La evaluación
histórica diaria no determina una intervención inmediata.

El documento de tarjeta adulta distingue Análisis, candidata y alerta publicada;
propone series comparables y comparaciones 7 contra 7. No es la referencia C1
actual. Sus reglas y recomendaciones requieren aprobación y datos suficientes.
Ni esos cálculos ni push, cooldown, política diurna o tarjeta se añaden aquí.

## Comprobaciones completadas

Preparacion Linux: 258 casos de tests/ y 15 de la raiz aprobados, ademas de HTTP real con preparacion F12 y recuperacion.

Windows/Python 3.10, 2026-10-12: 258 casos en 24.232 segundos; 257 aprobados y una omision prevista de POSIX. Otros 15 casos en 0.263 segundos y seis scripts heredados aprobados.

Tambien aprobaron HTTP Windows y recuperacion tras terminar/reiniciar el proceso, Compose, construccion Docker, persistencia y recuperacion tras reiniciar el contenedor, UID/GID 10001 y healthcheck healthy.

Evidencia local: `C:\Users\matum\Documents\modera_historical_smoke_20261012-014242-ed644114`.

Imagen probada: `sha256:e60739f92ac855cff05bf2e6e98b942a483c76a33f160390dfb734f5de7b85e4`.

Manifiesto de archivos probados: `6e190d97a3886d7eb706fa45aeb796028462ebffdac303fbb28b9006f8eecff5`.

Los archivos se probaron sin commit sobre la base 26654b6. Antes del cierre se verificaron sus huellas; despues solo se actualizo documentacion. Datos ficticios y perfil no calibrado; PMUM deshabilitado. Backend, Android fisico y AWS siguen pendientes.

## Pendientes priorizados y decisión recomendada

| Prioridad | Pendiente | Responsable | Propuesta y dependencia |
|---|---|---|---|
| Completado | Validacion local Windows/Docker | Matias | PASS con datos ficticios; evidencia registrada |
| P0 | Vinculación perfil/dispositivo/asignación | Juanma + Matías | Una serie por asignación/medición; confirmar IDs del backend; teléfono compartido sigue siendo dato del aparato |
| P0 | Formulario de condiciones | Equipo + revisión profesional | Mantener incertidumbre y cerrar tareas/adaptaciones concretas; no mapear diagnósticos a categorías |
| P0 para uso real | Parámetros C1 y referencia de producto | Equipo con evidencia metodológica | Mantener deshabilitado para uso real hasta justificar perfil; no adoptar fixture ni v3 |
| P1 | Preparación/outbox en backend | Juanma + Matías | Acordar job Python o adaptador equivalente; guardado previo y orden por serie |
| P1 | Paridad Android físico | Matías + Juanma | Comparar misma evidencia y día con permisos, gaps, reinicio y zona; no sumar TV/manual al v2 |
| P1 | Integración de red/persistencia y operación | Juanma | Compose real, un writer por volumen; observabilidad, backup y prueba de recuperación; AWS sigue pendiente |
| Posterior | Ofertas automáticas y tarjeta adulta | Equipo + profesional | Decidir políticas y versiones; no conectarlas automáticamente al resultado técnico |

Preguntas agrupadas para resolver con Juanma: IDs y asignaciones disponibles;
stack/lugar del job de preparación; contrato de export real; y si acepta un MVP
con declaración general y abstención hasta cerrar filtros funcionales, o prefiere
un formulario de restricciones prácticas sobre tareas revisadas. Son propuestas,
no respuestas ya acordadas con él. La calibración de C1 no se delega a Juanma como
si fuera solamente una elección de configuración de infraestructura.

## Fuentes consultadas

- Código y documentos del repositorio fijados en 26654b6: F12, cierre F14/F15,
  recibos y alcance F16, instrumento profesional y guías de integración.
- politica_ofertas_automaticas_2026-10-10.md y
  recomendaciones_tarjeta_adulto_2026-10-10.md, contenidos recuperados el 12/10.
  Se usan para dependencias y estado de propuestas; no se revalidan aquí todas
  sus afirmaciones bibliográficas ni se adoptan sus cifras.
- Android, UsageEvents.Event: https://developer.android.com/reference/android/app/usage/UsageEvents.Event
- Python 3.10, zoneinfo: https://docs.python.org/3.10/library/zoneinfo.html

Las notas clínicas permanecen como preguntas de revisión. Este trabajo no aporta
un dictamen profesional ni atribuye seguridad clínica al catálogo.
