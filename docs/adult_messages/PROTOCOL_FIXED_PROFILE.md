# Evaluación acotada del perfil fijo

13/10/2026. Se registra antes de ejecutar esta evaluación. El perfil del módulo
adult_messages.py queda fijo: ventana14, M20, K10, margen5, vigencia56,
espera14, una tarjeta nueva por28 días. Son decisiones de ingeniería del
candidato interno, no umbrales clínicos ni valores obtenidos por optimización.

Se reutilizan las600 series ficticias del benchmark C1 ya explorado. Se añaden
cuatro escenarios usando exactamente las100 trayectorias S0 (50 semillas,
dos sigmas): baja25%, baja50%, escalón50% durante14 días y retorno, escalón50%
con un cero aislado en el día85. No se generan nuevas semillas ni se presenta
esto como validación independiente.

Evaluaciones lunes cada7 días, desde día28 hasta112, con todos los días previos
de la serie; sin faltantes. Se ejecuta la transición de episodios del producto,
sin SQLite/HTTP en este bloque (cubiertos por pruebas distintas). Se conserva
cada decisión, apertura, actualización, salida y demora condicional.

Se informa: tarjetas nuevas totales y en fase de reporte (56,112]; series con
alguna apertura hasta el límite56 (no necesariamente vigente); aumentos/disminuciones; retornos/vencimientos;
trayectorias que no abrieron el aviso esperado y demoras entre inicio nominal
y primera apertura de la dirección esperada. No se llama FPR/sensibilidad
clínica a estos conteos. En patrón semanal no hay inicio nominal nuevo.
La evaluación del límite56 ocurre antes de observar el primer día modificado:
se excluye del reporte y de la demora atribuida al cambio. Esta precisión fue
corregida tras la primera ejecución para no contar una apertura previa como
detección del escalón; se repite el análisis con los mismos parámetros.

C1 no se optimiza ni se modifica: el perfil candidato lo conserva como evidencia
complementaria, no como condición. Esta es una decisión de alcance explícita;
la evaluación no demuestra que un gate C1 sea inferior. PMUM no participa.

Las pruebas de aceptación cubren aparte ausencia/ceros, correcciones, idempotencia,
concurrencia, cambio de serie, contextos, límites, calendario y transporte.
Si aparece un error de implementación se corrige y se registra; si los resultados
son poco satisfactorios se informa sin retocar umbrales silenciosamente.
