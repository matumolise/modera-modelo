# Export Android F12 → preparador → histórico: candidato revisable

Base: `61e31ceaaa7a81c775d143415a00a3fd9bf55721`, rama publicada
`analytics-integration-handoff-candidate`. Cambios preparados en una rama nueva
`f12-export-integration-candidate`. Sin merge, publicación ni despliegue en esta
ejecución. Las tres ramas entregadas se conservan.

## Fuentes realmente contrastadas

Se leyeron `DiagnosticUsageEventsCollector.kt`, `DiagnosticExport.kt`,
`UsageEventTypeNameMapper.kt`, `MainActivity.kt`, manifiesto, Gradle y prueba
instrumental existentes; el auditor `tools/f12/audit_usage_events_export.py`,
el puente/preparador, contratos y pruebas Python de la base publicada.
Los archivos usados se verificaron contra los blobs Git de ese commit.
No se recibió un export nuevo de un teléfono físico para este trabajo. Las
fixtures nuevas son ficticias y fieles a las claves/tipos del productor;
no se presentan como capturas ni como evidencia de ejecución Kotlin.

| Formato | Existe en la base | Versión comprobada | Uso |
|---|---|---|---|
| `summary_<UUIDsinGuiones>.json` | Sí, exportador Kotlin | Sin campo de versión; 9 claves exactas | Una consulta, estados y conteo |
| `events_<UUIDsinGuiones>.jsonl` | Sí, exportador Kotlin | `schemaVersion=raw-usage-event-v1`, 14 claves | Todas las filas de esa consulta |
| Proyección `raw_events`/`summaries` snake_case | Sí, preparador Python | `schema_version=1` de preparación; 9 campos por fila | Entrada interna del puente |
| CSV de ese exportador | No | No comprobada | No admitir ni fabricar un supuesto CSV |
| Representación diaria | Sí | `daily_use_duration_minutes_v2` | Única entrada admitida al histórico |
| Agregado v3 | Otro antecedente del proyecto | Fuera de esta conexión | No enviado ni incorporado a C1 |

La UI actual exporta solamente la última hora y no exporta resultados con error.
Por eso el harness añadido consulta intervalos explícitos y exporta también los
errores usando el mismo collector/exportador. No se cambió la UI ni el esquema
del exportador. No se agregó captura en segundo plano ni sincronización Android.

## Contrato exacto del par

El resumen contiene `collectorRunId`, `requestedBeginEpochMs`,
`requestedEndEpochMs`, `collectedAtEpochMs`, `usageAccessAvailable`,
`queryReturnedNull`, `eventCount`, `errorCode`, `errorMessage`.

Cada evento contiene `schemaVersion`, `collectorRunId`, `queryBeginEpochMs`,
`queryEndEpochMs`, `collectedAtEpochMs`, `eventTimeEpochMs`, `eventTypeCode`,
`eventTypeName`, `packageName`, `className`, `androidApiLevel`, `manufacturer`,
`model`, `queryOrdinal`.

UTF-8 sin BOM, JSON estricto y JSONL con una fila por evento, incluyendo los tipos
que no se usan para duración. Un archivo JSONL de cero bytes es válido cuando
`eventCount=0`. No se ignoran líneas vacías intermedias. El salto final emitido
por `appendLine` es válido. Los nullable están presentes con `null`, no omitidos.
No se convierten números fraccionarios, strings o booleanos en enteros.

El UUID v4 identifica una consulta, no un teléfono/persona. Los nombres físicos
de archivo no se usan como autoridad de asociación: se validan sus contenidos.
La lectura no reordena el export. Exige orden `(eventTimeEpochMs, queryOrdinal)`
y que los ordinales sean una permutación exacta de `0..eventCount-1`; el collector
enumera primero y ordena después, por lo que ordinales no crecientes entre
timestamps distintos son válidos.

Se exige igualdad del run, límites y `collectedAtEpochMs` en cada fila y resumen;
todos los timestamps pertenecen a `[begin,end)`. `collectedAtEpochMs` se toma al
comienzo de la consulta en Kotlin: no es un timestamp de finalización. Debe ser
posterior o igual al límite consultado, y no posterior a `computed_at` del backend.
No hay tolerancia inventada de reloj; ante discrepancia revisar/reconsultar.

| errorCode | Usage Access | Query null | Filas | Preparación |
|---|---|---|---|---|
| `null` | true | false | Conteo exacto, puede ser cero | Reconstruir solo si hay estado previo y consultas continuas |
| `USAGE_ACCESS_NOT_GRANTED` | false | false | 0 | Evidencia fallida; sola produce MISSING |
| `QUERY_RETURNED_NULL` | true | true | 0 | Evidencia fallida; sola produce MISSING |
| `SECURITY_EXCEPTION` | true | false | 0 | Evidencia fallida; sola produce MISSING |
| `QUERY_RUNTIME_EXCEPTION` | true | false | 0 | Evidencia fallida; sola produce MISSING |

Se rechazan códigos/estados no emitidos por el collector revisado. Si cambia el
productor, revisar/versionar el adaptador, sin normalizar silenciosamente.
`exception.message` puede ser `null` o una cadena vacía: se corrigió el puente
para conservar ambos. Una consulta exitosa mantiene `errorMessage=null`.

También se corrigió una vía de truncamiento silencioso del collector: si
`hasNextEvent()` anuncia una fila y `getNextEvent()` no la entrega, se lanza un
error que entra en `QUERY_RUNTIME_EXCEPTION`, sin exportar filas parciales como
consulta exitosa. Este cambio Kotlin requiere compilación/prueba Android externa.
No permite certificar que Android haya retenido o emitido todos los eventos.

## Asociación y límites de lo inferible

El backend proporciona una **cabecera nueva de preparación**, no un campo
inventado dentro del export Android. Contiene los cinco campos superiores del
preparador anterior, sin `raw_events` ni `summaries`:

```json
{
  "schema_version": 1,
  "request_id": "fixture-2026-09-01",
  "series": {
    "profile_id": "profile-test",
    "device_id": "device-test",
    "assignment_id": "assignment-test",
    "time_zone": "America/Argentina/Buenos_Aires",
    "measurement_version": "capture-test-v1"
  },
  "local_date": "2026-09-01",
  "computed_at": "2026-09-02T03:02:00+00:00"
}
```

Los IDs y la asignación vienen del contexto autenticado del backend. No usar
`packageName`, fabricante/modelo, UUID de consulta o serial ADB como identidad
del sujeto. El export no contiene zona IANA, perfil, instalación estable,
asignación ni fecha local: esos datos no pueden recuperarse de sus filas.
La zona se declara explícitamente, con la base tzdata fijada del preparador.
Se rechazan medianoches ambiguas/inexistentes y días no cerrados; se soportan
días de 23/25 horas. Los límites se convierten individualmente a UTC.

Se rechaza combinar filas/consultas con `androidApiLevel`, fabricante o modelo
distintos. Es un control de inconsistencia, no verificación de identidad: dos
teléfonos iguales pueden tener los mismos metadatos. Un cambio legítimo de API
requiere revisar/segmentar el lote; no transferir estado ni inferir un aparato.
En consultas vacías esos metadatos no están presentes: la auditoría lo informa,
sin inventarlos.

Consulta exitosa no equivale a captura completa. El núcleo requiere estado de
pantalla anterior al inicio del día y unión de consultas exitosas continua desde
ese estado hasta el cierre. Un gap, falta de estado previo o evidencia de
startup/shutdown en el tramo necesario produce MISSING. Si otra consulta
exitosa cubre realmente el mismo tramo, puede aportar evidencia: una consulta
fallida no borra automáticamente una consulta exitosa independiente.
La cobertura cuantificada sigue `null`; nunca se declara 100%.

Se conservan consultas solapadas y eventos repetidos; no se suman sesiones por
consulta ni se deduplica el registro crudo. El núcleo interpreta estados de
pantalla repetidos sin sumar dos veces el mismo tramo. Estados opuestos al mismo
timestamp se rechazan. Incluir dos copias del mismo run se rechaza: seleccionar
una copia original, no crear un UUID para eludir el control.

La retención de eventos, revocaciones históricas de permiso y discontinuidades
no emitidas no pueden probarse por el conteo auto-reportado. Una discrepancia
manual conocida bloquea la aceptación física y el envío como dato apto; no
rellenar el tramo ni cambiar el export. El harness compara reconstrucciones,
no certifica fidelidad física ni la persona que usó el dispositivo.

## Comando y paquete de procedencia

Desde la raíz del nuevo worktree, con `requirements-integration-tools.txt`:

```powershell
$salida = Join-Path $env:USERPROFILE "Documents\modera_f12_export_synthetic"
.\.venv-historical\Scripts\python.exe tools/integration/build_historical_request_from_export.py `
  --binding tests/fixtures/f12_export/binding.synthetic.json `
  --run tests/fixtures/f12_export/observed/summary.json tests/fixtures/f12_export/observed/events.jsonl `
  --output-dir $salida
if ($LASTEXITCODE -ne 0) { throw "Falló la preparación; no enviar el payload." }
```

Repetir `--run SUMMARY EVENTS` por consulta del mismo origen/serie; no combinar
exportaciones por su cercanía temporal. La carpeta debe ser nueva y su padre
existir. Se valida todo antes de crearla. Ante error de escritura se elimina
solamente la carpeta creada por esa ejecución; nunca los originales ni un
destino preexistente. Límite de lote 32 MiB, cabecera 64 KiB, 100000 eventos y
10000 consultas, sin truncar el excedente.

Si el backend declara expresamente que para ese día cerrado no hay export,
usar `--no-export` en lugar de `--run`. Produce MISSING con listas vacías,
`originals: []` y `export_evidence_state: NO_EXPORT_DECLARED_BY_BACKEND`;
no fabrica un resumen de consulta ni archivos Android. Sin ninguna de esas
opciones el CLI falla. Un path ausente/corrupto enviado con `--run` también
falla: nunca activa automáticamente `--no-export`.

No cerrar un recibo MISSING solo porque una copia esté temporalmente demorada.
El backend debe decidir cuándo fija la evidencia de un día y distinguir captura
ausente de export pendiente. No se inventa un deadline. Si ya se procesó MISSING,
nueva evidencia para el mismo record no es un retry compatible: requiere una
política explícita de corrección/versionado, fuera de esta API inmutable.

Contenido:

- `binding.original.json`: bytes de la cabecera usada.
- `originals/<runUUID>/summary.json` y `events.jsonl`: bytes idénticos a la entrada.
- `preparation.json`: proyección snake_case completa para inspección.
- `request.json`: payload final para conservar y enviar a analytics.
- `lineage.json`: versiones y SHA-256 de ambos originales por run.
- `SHA256SUMS.txt`: huellas de todos esos archivos, sin auto-incluirse.

Los archivos se conservan privados fuera de Git; pueden contener paquetes,
clases y metadatos del aparato. La API recibe solamente `request.json`, no este
paquete ni las filas crudas. El adaptador es offline; no se instala como nuevo
endpoint ni se ejecuta automáticamente en Docker.

El fingerprint final vincula versión del adaptador de export, fingerprint de la
proyección/serie/puente/tzdata y huellas de los originales. Un cambio de
metadatos o incluso de bytes de serialización modifica la procedencia. El
orden de los pares no la cambia. Los SHA detectan alteración, no autentican la
identidad del dispositivo.

`preparation.json` es una vista intermedia: volver a pasarla por el CLI antiguo
produce otra procedencia. Para reproducir el payload final se deben usar la
cabecera y los originales con el adaptador nuevo, o conservar `request.json`.
Un registro ya procesado por la vía antigua no puede sustituirse por este
payload: mismo record ID y procedencia distinta devuelve 409. Para series de
prueba nuevas usar una asignación explícita nueva; para producción decidir una
transición documentada, sin inventar IDs para eludir conflictos.

## Envío y recuperación

Se conserva `/v1/historical/evaluate` y el perfil C1 explícito. El backend debe
guardar de forma durable el payload antes de su primera solicitud, ordenar los
días por serie y mantenerlo para reintentos. HTTP 200 con `processed` reconoce
un recibo, incluso si la evaluación se abstiene; no repetir hasta obtener CHANGE.
Reintento compatible recupera el resultado original tras reiniciar; conflicto
409 requiere revisar contenido, origen u orden. No recalcular el día a partir
de una nueva consulta como si fuera el mismo reintento.

La responsabilidad de guardar la cola/payload del backend de Juanma todavía no
se ejecutó aquí. La persistencia comprobada es la del servicio analytics.
El writer lease, perfil vinculado al repositorio y formato persistente no cambian.
No se modifican k/threshold/min_history, PMUM, ofertas, tarjetas ni v3.

## Evidencia y pendientes

La evidencia final y los conteos están en `F12_EXPORT_REVIEW_2026-10-12.md`.
Las fixtures y reportes simulados no prueban Kotlin. El runner Windows ahora
incluye los exports ficticios en seed/replay HTTP nativo y Docker, sin ejecutar
automáticamente el teléfono. La imagen nueva requiere reconstrucción.

Primero validar Windows/Docker en el worktree nuevo; después compilar el APK
diagnóstico y test APK, ejecutar el protocolo físico y revisar el origen con
Juanma. No se declara cierre físico, conexión backend real ni despliegue AWS.

Referencias primarias consultadas: [UsageEvents.Event](https://developer.android.com/reference/android/app/usage/UsageEvents.Event),
[UsageEvents](https://developer.android.com/reference/android/app/usage/UsageEvents),
[UsageStatsManager](https://developer.android.com/reference/android/app/usage/UsageStatsManager),
[instrumentación por línea de comandos](https://developer.android.com/studio/test/command-line),
[InstrumentationRegistry](https://developer.android.com/reference/androidx/test/platform/app/InstrumentationRegistry).
