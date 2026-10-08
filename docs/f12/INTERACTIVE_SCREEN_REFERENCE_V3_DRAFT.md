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
- fijar el contrato del agregado y un adaptador Python con `spec_id` separado
  de `daily_use_duration_minutes_v2`;
- acordar perfil, dispositivo, fecha local, zona IANA, instantes UTC, ventanas
  consultadas, evidencia del estado inicial y versión del algoritmo;
- resolver la atribución cuando el dispositivo es compartido;
- decidir cómo se tratan días corregidos o recibidos fuera de orden antes de
  incorporarlos al C1 persistente.

No se pueden recalcular minutos desde un agregado sin los eventos. Los metadatos
permiten revisar cobertura y coherencia, no reproducir la suma. La política de
conservar o exportar eventos diagnósticos requiere una decisión aparte.
