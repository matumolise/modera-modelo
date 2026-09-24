# F12-B2 — Auditoría descriptiva de trayectorias humanas reales

## Propósito

Evaluar si un conjunto longitudinal humano real ofrece historia intraindividual
suficiente para construir referencias históricas robustas sin imputar observaciones
ni aplicar todavía el detector CUSUM.

Dataset inspeccionado: Dataset_LongFormat.csv (MEDIATICINO / estudio longitudinal).
El dataset fuente no se versiona en este repositorio.

SHA-256:
cdfdb5b2d665efcfcc25da6337d2102877541201e7da55ff3f0e121b57f0b51e

## Alcance

Esta etapa NO:
- ejecuta CUSUM;
- selecciona k ni h;
- selecciona una madurez histórica;
- imputa días ausentes;
- interpreta ausencia de fila como cero;
- excluye automáticamente DayInStudy == 1;
- convierte OUTLIERS o SD en reglas de elegibilidad de Moderá.

Los checkpoints 1, 3, 7, 14 y 28 son exclusivamente descriptivos.

## Resultados principales

Artefacto distribuido:
- 2587 filas;
- 93 participantes;
- 0 duplicados (ID, DayInStudy);
- mediana de 30 días observados por participante;
- 74/93 participantes presentan huecos internos.

Subconjunto reconstruido con los filtros del estudio fuente
(OUTLIERS == 1 y SD == 1):
- 2548 filas;
- 82 participantes;
- 67/82 presentan huecos internos.

La reconstrucción 82/2548 coincide con la población analítica reportada
previamente para el estudio fuente y se utiliza sólo como contraste descriptivo.

Las variables totOnDurPerDayMin y totTurnONPerDay presentan variación
intraindividual en las trayectorias disponibles. La escala robusta basada en
MAD puede ser degenerada durante el cold-start. Con al menos 7 valores previos,
las filas que alcanzan ese checkpoint en esta muestra presentan escala MAD
positiva para ambas métricas y ambas cohortes.

Esto NO selecciona 7 observaciones como madurez de producto. Exigir más historia
reduce progresivamente la disponibilidad: los checkpoints se utilizan para
cuantificar ese compromiso, no para declarar un valor universal.

## Interpretación para Moderá

La evidencia respalda mantener:
1. referencia estrictamente prequential, construida sólo con historia previa;
2. abstención cuando la escala robusta no es finita o positiva;
3. tratamiento explícito de huecos sin inventar ceros ni observaciones;
4. separación entre disponibilidad de referencia y decisión del detector.

La evidencia NO valida sensibilidad, especificidad ni tasa de falsos positivos,
porque las trayectorias humanas no proporcionan ground truth de cambios reales.

El significado físico exacto de totTurnONPerDay no se equipara a
APP_OPENING_COUNT, DEVICE_SESSION_COUNT ni unlocks de Moderá.

## Evidencia reproducible

Script:
tools/f12/audit_mediaticino_longitudinal.py

Salida agregada:
artifacts/f12/f12_b2_mediaticino_audit.json

El CSV fuente permanece fuera de Git.
