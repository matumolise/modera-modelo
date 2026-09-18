# F12-A.1 — Especificación del logger Android de diagnóstico

Estado: especificación de instrumento de validación. No es todavía implementación productiva ni contrato final de captura de Moderá.

## 1. Objetivo

Construir un logger Android mínimo que permita observar qué entrega realmente `UsageStatsManager.queryEvents(...)` durante secuencias controladas. Su finalidad es validar la semántica y la recuperabilidad de los eventos antes de definir sesiones, aperturas, desbloqueos, transiciones o métricas históricas.

Este componente NO debe:

- inferir `DEVICE_SESSION_COUNT`;
- inferir `APP_OPENING_COUNT`;
- transformar `ACTIVITY_RESUMED` en “apertura”;
- transformar `SCREEN_INTERACTIVE` en “desbloqueo”;
- emitir `BehavioralObservation`;
- ejecutar el detector histórico;
- producir alertas, recomendaciones o interpretaciones conductuales.

Primero se preservan los eventos crudos; las reglas de reconstrucción se diseñan después de F12-A.

## 2. Fuente técnica

Fuente primaria: `android.app.usage.UsageStatsManager.queryEvents(beginTime, endTime)`.

Reglas de consulta a preservar en el logger:

- `beginTime` es inclusivo.
- `endTime` es exclusivo.
- la consulta requiere Usage Access / `PACKAGE_USAGE_STATS`;
- los eventos detallados se conservan por el sistema solo durante “unos pocos días”;
- desde Android R, `queryEvents(...)` puede devolver `null` mientras el usuario del dispositivo no esté desbloqueado.

El logger debe registrar la ausencia de resultado o el fallo de acceso como resultado de captura; nunca convertirlos en “cero eventos observados”.

## 3. Eventos de interés inicial

El logger conserva cualquier tipo recibido, pero para F12-A.1 deben identificarse al menos:

- `ACTIVITY_RESUMED`
- `ACTIVITY_PAUSED`
- `ACTIVITY_STOPPED`
- `SCREEN_INTERACTIVE`
- `SCREEN_NON_INTERACTIVE`
- `KEYGUARD_SHOWN`
- `KEYGUARD_HIDDEN`
- `DEVICE_STARTUP`
- `DEVICE_SHUTDOWN`

Notas semánticas:

- `ACTIVITY_RESUMED` corresponde al `onResume()` de una Activity; una misma app puede producir múltiples eventos por cambios internos de Activity.
- `ACTIVITY_PAUSED` corresponde al `onPause()` de una Activity.
- `KEYGUARD_HIDDEN` normalmente acompaña el ocultamiento del keyguard, pero no debe renombrarse todavía como `UNLOCK`.
- `SCREEN_INTERACTIVE` indica pantalla en estado interactivo; no equivale por sí sola a sesión del dispositivo.
- `MOVE_TO_FOREGROUND` / `MOVE_TO_BACKGROUND` están deprecados desde API 29; el logger puede preservarlos si el sistema los devuelve, pero no normalizarlos silenciosamente a eventos modernos.
- `DEVICE_SHUTDOWN` no garantiza el timestamp exacto del apagado físico y puede dejar eventos abiertos sin cierre conocido.

## 4. Registro crudo v1

Cada evento exportado debe conservar, como mínimo:

```text
schemaVersion
collectorRunId
queryBeginEpochMs
queryEndEpochMs
collectedAtEpochMs
eventTimeEpochMs
eventTypeCode
eventTypeName
packageName
className
androidApiLevel
manufacturer
model
```

Reglas:

- `eventTimeEpochMs` proviene del evento Android.
- `collectedAtEpochMs` indica cuándo Moderá recuperó el evento.
- `queryBeginEpochMs` / `queryEndEpochMs` permiten auditar catch-up y solapamiento entre consultas.
- `packageName` y `className` se preservan tal como los expone Android; `className` puede ser `null`.
- `eventTypeCode` siempre se conserva aunque el logger no conozca su nombre.
- `eventTypeName` es una etiqueta diagnóstica; nunca reemplaza el código crudo.
- no registrar contenido de mensajes, notificaciones, contactos, fotos, ubicación precisa ni otros datos ajenos a esta validación.

## 5. Orden e idempotencia

Para F12-A.1 no se permite eliminar eventos de forma destructiva bajo una supuesta “deduplicación perfecta”.

Motivo: `UsageEvents.Event` no expone un identificador único general del evento. Dos registros con el mismo timestamp, tipo, package y class pueden ser indistinguibles desde esta API.

Por lo tanto:

1. conservar todos los eventos recuperados;
2. ordenar la exportación por `eventTimeEpochMs` y, ante empate, por orden de enumeración recibido;
3. conservar el orden de enumeración como metadato local opcional (`queryOrdinal`);
4. detectar duplicados potenciales de forma no destructiva durante el análisis posterior;
5. evaluar idempotencia del collector mediante consultas solapadas en F12-A.1, sin asumir antes de medir que un fingerprint sea identidad real.

## 6. Resultado de una ejecución del collector

Cada ejecución debe producir un resumen separado de los eventos:

```text
collectorRunId
requestedBeginEpochMs
requestedEndEpochMs
collectedAtEpochMs
usageAccessAvailable
queryReturnedNull
eventCount
errorCode
errorMessage
```

`eventCount = 0` solo significa “consulta válida sin eventos devueltos”.

No debe utilizarse para representar:

- permiso ausente;
- query `null`;
- excepción;
- intervalo no consultado;
- collector no ejecutado.

## 7. Piloto F12-A.1

### A1 — Pantalla / keyguard

Secuencia controlada:

1. dispositivo bloqueado;
2. encender pantalla;
3. observar keyguard;
4. desbloquear;
5. esperar unos segundos;
6. bloquear de nuevo.

Registrar manualmente los tiempos aproximados y luego comparar con la secuencia UsageEvents.

Pregunta: qué combinación de `SCREEN_*` y `KEYGUARD_*` se observa realmente y con qué orden.

No concluir todavía que esa secuencia constituye una `DEVICE_SESSION`.

### A2 — Actividades internas de una misma app

1. abrir app A;
2. permanecer en Activity inicial;
3. navegar a otra Activity interna;
4. volver a la Activity anterior;
5. salir.

Pregunta: cuántos `ACTIVITY_RESUMED/PAUSED` aparecen sin que exista una nueva apertura de app desde el launcher.

Resultado esperado del experimento: decidir si `ACTIVITY_RESUMED` puede o no utilizarse directamente como proxy de `APP_OPENING_COUNT`.

### A3 — A → B → A

1. abrir app A;
2. pasar a app B;
3. volver a app A.

Pregunta: si la secuencia permite reconstruir de manera reproducible cambio de app, foreground episode y retorno a una app sin confundirlos con Activities internas.

### A4 — Background sin bloqueo

1. usar app A;
2. llevar A al background manteniendo pantalla interactiva;
3. permanecer en launcher u otra superficie;
4. bloquear después.

Pregunta: separar foreground/background de aplicación respecto de estado de pantalla/keyguard.

### A5 — Collector retrasado y catch-up

1. ejecutar A1–A4 sin recolectar inmediatamente;
2. esperar un intervalo controlado;
3. consultar una ventana que cubra los eventos;
4. repetir una consulta solapada.

Preguntas:

- ¿los eventos previos siguen disponibles?
- ¿preservan `eventTimeEpochMs`?
- ¿aparecen nuevamente en una consulta solapada?
- ¿cómo distinguir repetición por reconsulta de pérdida/duplicación del origen?

Este caso no pretende todavía medir el límite máximo de retención.

## 8. Evidencia que se debe guardar por caso

Por cada A1–A5:

```text
caseId
device
androidApiLevel
manufacturer
model
manualSequence
manualTimestamps
queryWindow
rawExportFile
collectorSummary
observedEventSequence
missingExpectedEvents
unexpectedEvents
timingDifferences
semanticConclusion
openQuestions
```

Los `manualTimestamps` pueden obtenerse mediante cronometraje/log independiente o ADB cuando aporte un timestamp externo útil.

## 9. Métricas de F12-A.1

Todavía sin tolerancias de aprobación congeladas:

- cantidad observada vs cantidad esperada;
- error temporal de inicio;
- error temporal de fin;
- eventos esperados ausentes;
- eventos inesperados;
- orden recuperado;
- repetición bajo query solapada;
- recuperabilidad tras collector retrasado.

`durationError` y `transitionRecoveryRate` se calculan solamente cuando exista una regla de reconstrucción explícita y auditable; no desde el logger crudo.

## 10. Criterios de cambio metodológico

F12-A.1 debe obligar a revisar el contrato si aparece cualquiera de estos resultados:

- eventos necesarios ausentes de forma sistemática;
- diferencias relevantes entre Activity y app que invaliden `APP_OPENING_COUNT`;
- imposibilidad de distinguir pantalla/keyguard/sesión con la semántica pretendida;
- intervalos abiertos por shutdown/restart que impidan duración confiable;
- recuperación tardía insuficiente para el esquema de collector propuesto;
- comportamiento materialmente distinto por API/OEM.

No se corrige una discrepancia cambiando silenciosamente el significado del fenómeno. Se documenta y se decide después si:

1. cambia la reconstrucción;
2. cambia el nombre del fenómeno;
3. se introduce abstención/missing;
4. se abandona esa métrica.

## 11. Fuera de alcance de F12-A.1

Quedan para bloques posteriores:

- scheduler productivo con WorkManager;
- política definitiva de frecuencia del collector;
- persistencia Room final;
- exportación del niño real;
- thresholds de coverage;
- definición final de sesión/apertura/unlock;
- adapters `RawUsageEvent -> BehavioralObservation`;
- comparación multi-OEM formal;
- batería/Doze/restricciones de background completa;
- casos de medianoche, restart y revocación/restauración de Usage Access.

Estos elementos no están descartados; simplemente no son necesarios para responder primero las ambigüedades semánticas A1–A5.
