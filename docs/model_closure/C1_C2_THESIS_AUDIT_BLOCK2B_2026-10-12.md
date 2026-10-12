# Bloque 2B: C1/C2 y contraste parcial de tesis

Estado vigente: ver [cierre Windows/Docker y entrega](WINDOWS_DOCKER_CLOSURE_2026-10-12.md). Este informe conserva el alcance y los pendientes de su bloque original; los cierres posteriores no se atribuyen retrospectivamente a esa ejecución.

Revisión del 12/10/2026 desde d5eb630. No modifica núcleo, parámetros, perfil, v2 o resultados históricos. No ejecuta teléfono/Windows/Docker, ni una nueva simulación completa. Conserva la distinción entre código inspeccionado, verificaciones directas y resultados de la ejecución anterior.

## Fuente y denominadores

Se leyó directamente Dataset_LongFormat.csv, SHA cdfdb5b2d665efcfcc25da6337d2102877541201e7da55ff3f0e121b57f0b51e. Tiene 2.587 filas y 93 IDs de participante, sin pares ID/DayInStudy duplicados. Se reconstruyeron la ordenación por participante, admisión de tres registros posteriores, historia mínima experimental de siete y mediana/MAD estimable.

La admisión resulta en 1.836 ventanas de 75 participantes, 184 posiciones cortas y cero exclusiones adicionales por referencia no estimable. Ocho condiciones por ventana dan 14.688 escenarios. De las ventanas admitidas, 285 tienen saltos calendario entre las tres observaciones. Son cifras agregadas; no se redistribuyen filas ni IDs.

El runner preserva estado preintervención por replay y lo comparte entre brazos. Dentro de cada brazo avanza el estado propio, pero las referencias siguen usando exclusivamente historia real no perturbada. La perturbación escala por la referencia de cada registro; no es necesariamente una suma constante definida al comienzo. Esto difiere de guardar observaciones alteradas en la API y admitirlas después a su referencia all_prior_usable_records_v1.

## Resultados guardados y alcance

f12_c2_reproduced.json recuperado es estructuralmente idéntico a artifacts/f12/f12_c2_stateful_semisynthetic_duration.json. Para las ocho condiciones se comprobó que: excedencia previa + ventanas elegibles = 1.836; las cuatro celdas pareadas suman uno y corresponden a conteos enteros; las tasas control/intervención coinciden con sus celdas; el conteo de offsets coincide con cruces de intervención. Los denominadores elegibles son 1.180, 1.418, 1.547 y 1.664 según k/h.

Es coherencia de resultados agregados, no reproducción del detector para cada escenario. El JSON declara que no conserva registros individuales de escenarios. La ejecución anterior tiene un log de reproducción, pero no se atribuye una nueva ejecución completa a este bloque. No se cambian el runner o el artefacto publicado para introducir nuevos denominadores retrospectivos.

Los offsets son posiciones 0–2 de observaciones, no latencia calendario. Las ventanas solapadas no son independientes. Un nuevo cruce bajo perturbación conocida no proporciona sensibilidad/especificidad ni FPR de cambios humanos reales. Tampoco justifica min_history=7, k=0.5/1 o h=3/5 como parámetros de producto. La evaluación no prueba la emisión/API/captura física completa.

## Contraste con E50

Se abrió directamente el PDF E50 disponible, 147 páginas y SHA 861169714c20e285a99eb176eb0d2f6f868e9d9f5cd28abbc39dc4e8a9af9d6f. Se revisaron los pasajes pertinentes de RF-07/RF-08, CU-02 y CU-04, y se buscó la ubicación de synthetic_pmu_severity y las métricas .6743/.8179/.1478. No se afirma lectura completa o que ésta sea la última versión consolidada.

La tabla previa de propuesta ubicaba las métricas sintéticas en páginas impresas 76–77. La búsqueda directa las localiza en página PDF 76 / impresa 74. Se corrigió esa referencia. CU-02 está en PDF58/impresa56; CU-04 en PDF59/impresa57. RF-08/CU-02 todavía describen la estimación del modelo a partir de métricas Android; eso no equivale a las cuatro entradas parentales de HU v1. La propuesta conserva esa separación. RF-10/CU-04 describen comunicación/recomendación, cuyo funcionamiento completo no queda demostrado por un cruce técnico C1. No se implementó o aprobó aquí un flujo nuevo de comunicación.

## Estado

Comprobado: fuente y admisión; 75 contribuyentes; 285 gaps; igualdad del resumen recuperado/publicado; coherencia aritmética; rutas relevantes del código y pasajes específicos del PDF. Corregido: precisión de denominadores, offsets y referencia de páginas. Sin cambios de código: no se repite la suite 325+15 del bloque 1 por estas ediciones documentales.

Pendiente: reconstrucción final del paquete, inventario de evidencia, cotejo restante de documentos/fuentes y evidencia de binario original/Windows; población/ground truth y perfil C1 de producto requieren evidencia y decisión. La devolución de Cecilia no se presume recibida. No hay merge, publicación, AWS, Juanma, selector/catálogo/ofertas/tarjetas, negocio/pagos o api.zip.
