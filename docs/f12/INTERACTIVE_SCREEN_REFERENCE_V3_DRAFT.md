# Referencia v3 para duración diaria de pantalla interactiva

Estado: **borrador ejecutable para contrastar con Android**. Este módulo no
modifica la serie histórica v2 ni acepta todavía agregados calculados por la
app. Archivo: `historical/interactive_duration_v3.py`. Casos compartidos:
`tests/fixtures/interactive_screen_vectors_v3.json`.

## Significado de la medición

La salida es la duración en minutos durante la cual la pantalla de **este
dispositivo** estuvo en estado interactivo dentro de un día delimitado por
instantes con zona horaria. No mide atención, desbloqueos ni uso atribuible al
niño si otras personas utilizan el dispositivo.

`OBSERVED` incluye un valor positivo; `OBSERVED_ZERO` exige captura suficiente
y exactamente cero; `MISSING` lleva `minutes=null` y un motivo. Una consulta
exitosa no demuestra que Android haya preservado absolutamente todos los
eventos; nuestra cobertura sólo verifica que las ventanas consultadas no
dejan huecos temporales.

## Regla de reconstrucción para el piloto

1. Validar las consultas y cada evento contra su ejecución y ventana. El
   código numérico del evento es la fuente; el nombre es diagnóstico.
2. Buscar evidencia de estado anterior al comienzo del día. Desde esa marca
   temporal hasta el fin del día debe haber consultas exitosas de cobertura
   continua. Si no la hay, el resultado es `MISSING`.
3. Si hay solapamientos, elegir consultas completas por tramos disjuntos. En
   cada paso usar la consulta que llega más lejos; desempatar por recolección
   más reciente y por ID. En su tramo se conservan **todos** sus eventos. No
   deduplicar eventos por `(timestamp, tipo)` ni borrar el registro crudo.
   Antes de calcular, comparar la secuencia, con multiplicidad, dentro de
   cada intervalo en que dos consultas exitosas se solapan. Si discrepan,
   marcar `CONFLICTING_OVERLAPPING_QUERIES`.
4. Dentro de una consulta, ordenar por `(event_time_epoch_ms, query_ordinal)`.
   `query_ordinal` debe ser el orden original de enumeración de Android. Si
   tipos distintos tienen el mismo instante **y el mismo ordinal**, marcar
   `AMBIGUOUS_EVENT_ORDER`; no elegir un orden por nombre ni tipo.
5. Acumular sólo los intervalos que comienzan con `SCREEN_INTERACTIVE` y
   terminan con `SCREEN_NON_INTERACTIVE`. El comienzo del día se inicializa
   con el último estado anterior observado; un intervalo todavía interactivo
   se recorta en el fin exclusivo del día. El siguiente día reconstruye su
   estado inicial desde su propia evidencia. El fin no se calcula sumando
   24 horas al inicio local: el contrato aporta ambos instantes.
6. Si hay `DEVICE_SHUTDOWN` o `DEVICE_STARTUP` durante el día, el piloto se
   abstiene: `OPEN_INTERVAL_ACROSS_RESTART` si había un intervalo interactivo,
   o `UNKNOWN_STATE_AFTER_RESTART` si no se puede demostrar el estado posterior.
   Un reinicio anterior al comienzo no invalida el día si otro evento previo
   al comienzo restablece el estado y hay cobertura continua. Esta política
   estricta debe contrastarse con registros de teléfonos físicos; Android
   anteriores a API 29 pueden no exponer esos eventos.

Una consulta fallida no aporta cobertura, pero tampoco invalida un día cuando
otras consultas exitosas cubren el intervalo y concuerdan en sus solapamientos.
Una contradicción entre consultas produce un faltante; no se resuelve
eligiendo arbitrariamente una secuencia.

## Límite de esta entrega

Los vectores cubren empates, solapamientos compatibles e incompatibles,
consultas fallidas y huecos, cero observado, cruce de medianoche, día local de
25 horas, cierre exclusivo y reinicios. Son casos sintéticos **de prueba de
código**, no datos para entrenar un modelo ni evidencia de que `queryEvents`
sea exhaustivo en teléfonos reales.

Antes de recibir `interactiveScreenMinutes` de Android en el histórico:

- ejecutar estos mismos vectores en Kotlin y comparar estado, minutos y motivo;
- contrastar registros de prueba en teléfonos físicos y documentar diferencias;
- contrastar en Android el contrato de agregado y el adaptador Python ya
  bosquejados abajo, manteniendo el `spec_id` separado de
  `daily_use_duration_minutes_v2`;
- acordar cómo el backend vincula perfil y dispositivo y conserva la fecha
  local, zona IANA, ventanas, evidencia inicial y versión del algoritmo;
- resolver la atribución cuando el dispositivo es compartido;
- decidir cómo se tratan días corregidos o recibidos fuera de orden antes de
  incorporarlos al C1 persistente.

## Contrato de agregado v3, todavía aislado

`historical/interactive_aggregate_v3.py` define un contrato tipado y un
adaptador experimental **sin conectarlo al detector ni a la persistencia**.
La representación usa `interactive_screen_device_minutes_v3_draft`,
`DEVICE_INTERACTIVE_SCREEN_DURATION` y `subject_id=device_id` seudónimo. El
perfil infantil y la vinculación del dispositivo quedan en el backend. Los
minutos son del dispositivo y no se atribuyen automáticamente al chico.

| Campo interno | Significado |
| --- | --- |
| `capture_id`, `device_id` | Identidad de la captura e identificador seudónimo del dispositivo. |
| `local_date`, `time_zone_id` | Fecha local y zona IANA vigente; conservar la zona usada al calcular. |
| `interval_start`, `interval_end` | Instantes con zona que delimitan las dos medianoches locales, inicio incluido y fin excluido. Pueden abarcar 23, 24 o 25 horas. |
| `computed_at`, `algorithm_version` | Momento del cálculo y versión exacta `interactive-screen-reference-v3-draft`. |
| `status`, `interactive_screen_minutes`, `missing_reason` | `OBSERVED` > 0, `OBSERVED_ZERO` = 0 o `MISSING` con minutos nulos y motivo. |
| `initial_state` | Último evento de estado anterior al inicio: timestamp en epoch ms y código 15 o 16. Es una declaración de Android; el agregado por sí solo no prueba que sea el último. |
| `query_windows` | Cada consulta: `run_id`, comienzo/fin en epoch ms y `succeeded`. Las consultas fallidas no dan cobertura. |
| `restart_in_day`, `conflicting_overlaps`, `ambiguous_event_order` | Resultados de los controles hechos sobre eventos en Android. Cualquiera verdadero obliga a abstenerse. |

El adaptador comprueba la fecha local, la versión, valores, estado inicial y
cobertura temporal continua desde ese estado hasta el fin del día. Si falta
evidencia, produce `MISSING` con minutos nulos; no inventa cero. Conserva
`coverage.value=None`: las ventanas exitosas **no prueban** exhaustividad de
los eventos ni permiten recalcular el total. Los indicadores de reinicio,
solapamiento y orden, así como que el estado inicial sea realmente el último,
son afirmaciones del collector que sólo se pueden contrastar con eventos o
pruebas de paridad. No presentarlos como verificación independiente de Python.

La implementación de Android debe persistir su agregado con las ventanas y
el estado inicial para auditoría, y conservar una vía diagnóstica de eventos
para las pruebas de paridad. Ante permisos denegados, consulta nula o fallida,
estado desconocido o conflicto, enviar `MISSING` y el motivo. Backend debe
identificar revisiones y entregas repetidas sin reescribir el pasado; ese
contrato de persistencia aún no está cerrado. No mandar esta representación al
C1 ni combinarla con `daily_use_duration_minutes_v2` hasta resolver paridad,
atribución y política de correcciones.

El entorno Windows necesita datos de zonas IANA: `tzdata` está declarado en
`requirements.txt`. La verificación local es
`python -m unittest tests.historical.test_interactive_aggregate_v3 -v`.

## Comparación automática con Android

La implementación Kotlin debe correr los 15 casos del JSON compartido con
**el mismo algoritmo** que calculará los agregados diarios. Puede exportar un
archivo JSON de resultados de esta forma (ejemplo parcial):

```json
{
  "schema_version": "interactive-screen-parity-v3-draft",
  "results": [
    {"id": "ordered_equal_timestamp", "status": "OBSERVED", "minutes": 120.0, "reason": null},
    {"id": "ambiguous_equal_timestamp", "status": "MISSING", "minutes": null, "reason": "AMBIGUOUS_EVENT_ORDER"}
  ]
}
```

Debe incluir **todos** los IDs de los vectores, uno por caso. Para comparar:

```text
python tools/f12/compare_interactive_v3.py android-results.json
```

El comparador informa casos faltantes, duplicados o desconocidos, además de
diferencias de estado, motivo y minutos (tolerancia de 0,000001 minuto). Un
`PASS` prueba paridad sólo para estos casos preparados, no calidad del registro
real. Para teléfonos físicos hay que conservar un diagnóstico acotado con
eventos y resúmenes de consulta, comparar ambos cálculos por día y documentar
modelo, versión Android, zona horaria, permisos, cobertura, discrepancias y
decisión sobre cada caso. No incluir datos personales en el export de paridad.

No se pueden recalcular minutos desde un agregado sin los eventos. Los metadatos
permiten revisar cobertura y coherencia, no reproducir la suma. La política de
conservar o exportar eventos diagnósticos requiere una decisión aparte.
