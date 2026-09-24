# F12-C1 — Validación semisintética pareada sobre trayectorias humanas reales

## 1. Objetivo

F12-C1 evalúa si el detector histórico C1 implementado en Moderá responde de manera coherente a cambios técnicos conocidos introducidos sobre trayectorias humanas reales.

El experimento no estima sensibilidad, especificidad ni tasa de falsos positivos sobre población real, porque el dataset no dispone de ground truth sobre cambios conductuales reales.

## 2. Fuente de datos

Se utilizó `Dataset_LongFormat.csv` de MEDIATICINO.

SHA-256:

`cdfdb5b2d665efcfcc25da6337d2102877541201e7da55ff3f0e121b57f0b51e`

El artefacto contiene 2587 registros correspondientes a 93 participantes.

Para F12-C1 se utilizó `totOnDurPerDayMin`, interpretada únicamente como duración diaria total distribuida por el estudio fuente. No se presupone equivalencia con sesiones, aperturas de aplicaciones ni desbloqueos.

## 3. Diseño experimental

Se construyeron contrafactuales pareados sobre las mismas trayectorias reales.

Para cada ventana admisible:

- control: continuación humana observada;
- intervención: la misma continuación con una perturbación técnica conocida;
- ambos brazos utilizan exclusivamente historia humana real estrictamente anterior para construir la referencia;
- los valores perturbados nunca ingresan en referencias posteriores;
- los días ausentes no se imputan ni se reinterpretan como cero.

La perturbación se expresó en unidades de la escala robusta individual de la referencia: +1 y +2 escalas, durante tres registros observados consecutivos.

Se evaluaron experimentalmente:

- k = {0.5, 1.0};
- h = {3.0, 5.0};
- historia mínima experimental = 7 registros previos.

Estos valores constituyen condiciones experimentales. F12-C1 no selecciona parámetros definitivos del producto y el valor 7 no se establece como madurez definitiva del Analizador Histórico.

## 4. Implementación

El experimento reutiliza la implementación productiva existente de:

- `build_scalar_reference()`;
- `evaluate_c1()`;
- `C1DetectorConfig`;
- `CusumState`.

No se implementó una segunda versión de CUSUM dentro del experimento.

`CHANGE` representa el resultado de una evaluación del detector cuyo estadístico alcanza el umbral configurado. No equivale todavía a un `DetectionEvent` de producto. F12-C1 tampoco evalúa políticas de reset, cooldown o rearmado.

## 5. Escenarios evaluados

Se obtuvieron 1836 ventanas humanas base admisibles.

Cada ventana fue evaluada bajo ocho combinaciones experimentales:

2 valores de k × 2 thresholds × 2 magnitudes de perturbación.

Por lo tanto, el artefacto contiene 14688 evaluaciones pareadas de condición. Estas 14688 evaluaciones no deben interpretarse como 14688 trayectorias humanas independientes.

Se omitieron 184 posiciones por no disponer de tres registros observados de continuación. No fue necesario excluir ventanas adicionales por referencia inicial no estimable entre las que superaron los restantes criterios de admisión.

## 6. Resultados

La respuesta del detector aumentó sistemáticamente al incrementar la magnitud de la perturbación de +1 a +2 escalas robustas.

Para k=0.5 y h=3, la proporción de ventanas con `CHANGE` en intervención pasó de 0.3655 con +1 escala a 0.8083 con +2 escalas.

Para k=0.5 y h=5 pasó de 0.1514 a 0.4924.

Para k=1.0 y h=3 pasó de 0.2042 a 0.5861.

Para k=1.0 y h=5 pasó de 0.0888 a 0.2789.

Aumentar k o h redujo, en estas condiciones experimentales, la frecuencia de evaluaciones `CHANGE`.

Cuando hubo respuesta durante la intervención, el primer `CHANGE` ocurrió dentro de los tres registros evaluados. El offset utilizado es base cero: 0 corresponde al primer registro, 1 al segundo y 2 al tercero.

## 7. Interpretación

Los resultados muestran que la implementación C1 presenta una respuesta técnica ordenada frente a perturbaciones conocidas introducidas sobre fondos longitudinales humanos reales.

El experimento permite evaluar comportamiento técnico del detector bajo contrafactuales controlados. No demuestra eficacia clínica ni capacidad para detectar uso problemático real.

La `control_change_rate` tampoco debe interpretarse como false-positive rate. Una continuación humana real puede contener cambios genuinos y el dataset no aporta etiquetas que permitan clasificarlos como cambios verdaderos o falsos.

Del mismo modo, una configuración que produzca más respuestas ante la intervención no puede considerarse automáticamente superior, y una configuración con menor `control_change_rate` tampoco puede considerarse automáticamente mejor. F12-C1 no selecciona k, threshold ni madurez de producto.

## 8. Alcance y limitaciones

F12-C1 estudia duración diaria total porque es la variable longitudinal del dataset con semántica más directamente utilizable para este objetivo.

No se replica automáticamente el mismo experimento con `totTurnONPerDay`: su semántica exacta no permite equipararla con `APP_OPENING_COUNT`, sesiones o desbloqueos de Moderá. Repetir el experimento no resolvería esa limitación semántica.

La validación utiliza fondos humanos reales, pero las perturbaciones son semisintéticas. Tampoco valida todavía captura Android física, interpretación conductual, comunicación al usuario, alertas o recomendaciones.

## 9. Evidencia reproducible

Runner:

`tools/f12/run_f12c_semisynthetic.py`

Artefacto agregado:

`artifacts/f12/f12_c1_semisynthetic_duration.json`

El runner verifica el SHA-256 del dataset antes de ejecutar y registra explícitamente las restricciones epistemológicas y las condiciones experimentales utilizadas.
