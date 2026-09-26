# F15 — Cierre de interpretación histórica

## 1. Objetivo

La Fase 15 incorporó una capa de interpretación descriptiva entre la detección técnica producida por el Historical Analyzer y las futuras decisiones de comunicación, alertas o recomendaciones.

El objetivo de esta fase no fue determinar si el comportamiento observado es bueno, malo, riesgoso o problemático, sino transformar un `DetectionEvent` técnico en una representación auditable de qué cambio fue detectado respecto de la referencia histórica individual.

La separación implementada queda expresada de la siguiente manera:

`DetectionEvent → HistoricalInterpretation → futura decisión de comunicabilidad → posible observación/alerta → posible recomendación`

Las etapas posteriores a `HistoricalInterpretation` no forman parte de F15.

## 2. Principio semántico

Un `DetectionEvent` representa una detección técnica producida por el analizador histórico. Por sí solo no constituye evidencia de riesgo, daño, empeoramiento, mejora, uso problemático ni diagnóstico.

Por este motivo, `HistoricalInterpretation` se mantiene deliberadamente descriptivo y conserva únicamente información que puede derivarse del análisis ejecutado y de la representación conductual evaluada.

No se incorporan inferencias clínicas ni valoraciones sobre el niño.

## 3. Contrato HistoricalInterpretation

Se incorporó el contrato `HistoricalInterpretation` junto con `ChangeDirection` y el constructor `build_historical_interpretation`.

La interpretación conserva:

- identidad de la interpretación;
- sujeto;
- `DetectionEvent` y `DetectorEvaluation` de origen;
- representación y especificación evaluadas;
- fenómeno y unidad;
- intervalo conductual evaluado;
- valor observado;
- valor de referencia;
- cambio respecto de la referencia;
- cambio relativo cuando la referencia permite calcularlo;
- dirección descriptiva (`INCREASE`, `DECREASE` o `UNCHANGED`);
- cantidad de observaciones históricas utilizadas por la referencia;
- instante de corte de la referencia;
- cobertura y flags de calidad;
- versión de interpretación;
- instante de cálculo.

El valor de referencia no se recalcula dentro de esta capa. Se utiliza el valor registrado por `DetectorEvaluation`, evitando introducir una segunda implementación de la referencia histórica.

## 4. Magnitud y dirección

La magnitud principal se expresa mediante:

`value_change = observed_value - reference_value`

Por lo tanto, `value_change` conserva el signo del cambio.

La dirección se deriva exclusivamente de esa diferencia:

- valor positivo → `INCREASE`;
- valor negativo → `DECREASE`;
- valor igual a cero → `UNCHANGED`.

También se conserva `relative_change` como información contextual:

`relative_change = value_change / reference_value`

Cuando la referencia es cero, el cambio relativo se representa como `None` en lugar de inventar un valor o producir una división inválida.

Estas magnitudes describen la diferencia respecto de la referencia individual. No representan severidad, importancia clínica ni impacto sobre la salud.

## 5. Contexto histórico y temporal

La interpretación conserva el intervalo que fue efectivamente evaluado, `reference_history_count` y `reference_cutoff`.

Esto permite sostener afirmaciones descriptivas del tipo:

> En el intervalo evaluado se observó un valor respecto de una referencia construida a partir de las observaciones históricas que resultaron elegibles para integrarla.

La implementación actual no permite afirmar de forma válida:

- cuándo comenzó realmente un cambio;
- durante cuántos días persiste;
- que existe una tendencia conductual;
- que varios eventos pertenecen a un mismo episodio;
- que el comportamiento está empeorando o mejorando.

No se agregaron campos artificiales para representar información que el sistema todavía no calcula.

La persistencia, repetición o agrupación de cambios podrá analizarse posteriormente si resulta necesaria para decidir qué información conviene comunicar.

## 6. Integración con el vertical Android

F15 fue integrada con el vertical técnico existente para `DAILY_USE_DURATION`.

El recorrido actualmente probado es:

`Android UsageEvents`
→ `daily interactive duration`
→ `BehavioralObservation`
→ `HistoricalRepresentation`
→ referencia histórica
→ `DetectorEvaluation`
→ `DetectionEvent`
→ `HistoricalInterpretation`

La prueba de integración utiliza la representación realmente persistida por el flujo antes de construir la interpretación. De esta manera se verifica que la interpretación se obtiene a partir del mismo dato que atravesó el vertical histórico y no de un cálculo paralelo preparado exclusivamente para el test.

## 7. Frontera semántica

`HistoricalInterpretation` excluye deliberadamente conceptos pertenecientes a capas posteriores o que requerirían evidencia adicional.

Entre ellos:

- riesgo;
- nivel de riesgo;
- severidad;
- significado clínico;
- uso problemático;
- mejora;
- empeoramiento;
- duración inferida de persistencia;
- supuesto instante de comienzo del cambio;
- comunicabilidad;
- alerta;
- recomendación.

Esta frontera cuenta además con una prueba de regresión específica sobre el contrato para detectar la incorporación accidental de campos de decisión o significado clínico.

La existencia de una interpretación tampoco provoca automáticamente una intervención. La decisión sobre si un cambio debe mostrarse, notificarse o utilizarse como contexto para una recomendación queda fuera de F15.

## 8. Validación técnica

Al cierre de F15 se ejecutó la suite histórica completa mediante:

`.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py" -v`

Resultado final:

- 142 tests ejecutados;
- 142 tests satisfactorios;
- 0 fallos;
- 0 errores.

La suite incluye pruebas específicas del contrato de interpretación y pruebas del vertical Android integrado.

La suite incluye además pruebas de regresión que verifican que importar y utilizar el paquete histórico no modifica el contrato de entrada ni la predicción del modelo PMU existente.

## 9. Decisiones deliberadamente no cerradas

F15 no define:

- criterios de comunicabilidad;
- persistencia mínima para comunicar un cambio;
- agrupación de eventos repetidos;
- frecuencia de comunicación;
- prioridad de alertas;
- texto final dirigido al padre o tutor;
- recomendaciones asociadas;
- actividades fuera de pantalla;
- criterios clínicos;
- niveles de riesgo;
- umbrales universales de relevancia conductual.

F15 tampoco incorpora persistencia propia de HistoricalInterpretation. La interpretación se construye a partir de la representación histórica persistida y del resultado del análisis disponible durante el procesamiento. Si las etapas posteriores requieren conservar interpretaciones o decisiones de comunicabilidad para trazabilidad, esa persistencia deberá diseñarse explícitamente.

Tampoco modifica las decisiones todavía abiertas del Historical Analyzer respecto de parámetros de producto, adaptación de referencia, reset, rearm o madurez definitiva.

Estas cuestiones no deben inferirse a partir del cierre técnico de F15.

## 10. Continuidad

La siguiente etapa debe trabajar sobre la separación:

`HistoricalInterpretation → CommunicabilityDecision → posible comunicación → posible Recommendation`

F16 deberá determinar cómo utilizar una interpretación descriptiva para decidir qué información resulta pertinente comunicar y cómo vincularla, cuando corresponda, con recomendaciones respaldadas por evidencia.

Las decisiones de contenido dirigidas a niños o adultos deberán diferenciarse de la detección estadística y requerirán el nivel de respaldo bibliográfico y validación profesional correspondiente.

## 11. Estado de cierre

F15 queda técnicamente implementada para el primer vertical histórico integrado de `DAILY_USE_DURATION`.

El cierre demuestra la transformación reproducible de una detección técnica en una interpretación descriptiva y auditable, manteniendo separadas las inferencias clínicas, las decisiones de comunicación, las alertas y las recomendaciones.

Este cierre no implica que el Historical Analyzer completo, el sistema de alertas/recomendaciones ni el MVP global de Moderá estén finalizados.