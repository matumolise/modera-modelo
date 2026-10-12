# Propuesta revisable para la tesis: PMUM y analizador C1

No modifica automáticamente el documento original. Se contrasta con el E50 accesible (metadata 22/08/2026, 147 páginas PDF / 145 impresas) y la adenda F16.2. Si existe una versión posterior, cotejarla antes de pegar: no se afirma conocerla. Las decisiones de alcance del texto propuesto requieren revisión académica y no aprueban uso con familias.

## Correcciones localizadas respecto de E50

| Ubicación leída (página impresa) | Corrección propuesta |
|---|---|
| Introducción / objetivos, 9–10 | No presentar riesgo o necesidad individual como inferencia acreditada por PMUM/C1 |
| Alcance, 10–11 | Separar la captura Android de la entrada parental experimental; no afirmar que PMUM se alimenta de esas métricas |
| RF-07/RF-08, 53 | Conservar comparación histórica; especificar que la regresión actual utiliza respuestas parentales, no métricas Android intercambiables |
| CU-02 pasos 6–10, 56 | Describir C1 técnico en el flujo de métricas; sacar la estimación parental de ese procesamiento automático y tratarla en su contrato independiente |
| 3.2.4, 64–77 | Registrar el modelo sintético de once variables como antecedente; documentar HU v1 por separado, con nueva fuente/objetivo/evaluación |
| Evaluación del modelo previo, 74 (página 76 del PDF) | No reutilizar MAE .6743/RMSE .8179/R² .1478 como resultados del modelo HU |
| Limitaciones / conclusión | No presentar calibración, validación externa, teléfonos o backend como ya comprobados por pruebas técnicas |

La adenda F16.2 ya propone separar comunicaciones adultas e infantiles. Esta propuesta no reabre ni implementa ese diseño. Se limita a corregir las afirmaciones del modelo y su evidencia.

El bloque 2B cotejó directamente el PDF identificado por SHA y las páginas indicadas de RF-07/RF-08, CU-02 y CU-04. Se corrigió la confusión entre índice del PDF y número impreso al localizar las métricas sintéticas. Esa comprobación parcial no equivale a lectura completa de la tesis ni a aprobación de sus cambios.

## Texto propuesto: alcance del análisis

Moderá distingue dos componentes analíticos con fuentes y finalidades diferentes. El analizador histórico C1 procesa representaciones de duración de uso del dispositivo y compara cada observación admisible con una referencia construida a partir de observaciones anteriores de la misma serie. Por separado, el candidato PMUM-SF HU v1 estima la media parental de una medida de uso problemático de medios de pantalla a partir de edad, código de sexo y categorías de tiempo de pantalla informadas por un adulto responsable. Las categorías parentales no se sustituyen por minutos obtenidos de Android.

Ambos componentes se presentan como candidatos para investigación y verificación técnica. Sus salidas no constituyen diagnósticos ni categorías de riesgo, y no acreditan por sí solas la necesidad de una intervención individual. La comunicación a familias y la utilización de resultados para decisiones de producto requieren una justificación y una revisión específicas. El alcance de la entrega técnica no supone que esas habilitaciones hayan sido obtenidas.

## Texto propuesto: desarrollo del candidato PMUM-SF

El desarrollo inicial incluyó un prototipo con once variables y un objetivo sintético denominado synthetic_pmu_severity. Ese prototipo se conserva como antecedente de exploración técnica; sus resultados no corresponden al candidato posterior entrenado con respuestas parentales reales.

El candidato HU v1 utiliza el archivo SEM.dat del conjunto húngaro recuperado mediante el archivo identificado como Zenodo 21802447. Su procedencia se conserva por medio de la huella SHA-256 del ZIP. Se seleccionaron registros con filter=1 y edad de 6 a 12 años. De 810 registros en ese intervalo, 806 tenían los nueve ítems PMUM completos, con valores válidos y total coincidente con la suma. El candidato conservó 803 registros cuyo código de sexo del niño era 1 o 2 y excluyó tres con código 4. Esta selección operativa no equivale exactamente a la condición useobservations de SEM.inp, que también restringía el código de sexo del cuidador.

La variable objetivo se definió como PMUMTotal dividido por nueve, en escala de 1 a 5. Las variables predictoras fueron edad y tres variables categóricas: sexo del niño, tiempo de pantalla en día hábil y tiempo de pantalla en fin de semana. La edad se estandarizó y las categorías se codificaron mediante one-hot dentro de cada partición de entrenamiento. Se utilizó Ridge con alpha=1 para el candidato entregado. Ese valor fue fijado después de una evaluación exploratoria previa; no se presenta como elección realizada sobre una evaluación externa independiente.

La fuente se refiere al hijo del hogar seleccionado por mayor tiempo de pantalla y comparte informante adulto entre predictores y objetivo. Las categorías de tiempo tienen intervalos discontinuos y no se convierten en minutos ni en puntos medios. La pregunta de fin de semana incluye distintos dispositivos; la redacción completa de día hábil permanece pendiente por truncamiento en los metadatos disponibles. Estas características restringen la generalización y la equivalencia con un formulario de uso local.

## Texto propuesto: evaluación PMUM y limitaciones

Se realizó una comprobación exploratoria interna mediante predicciones fuera de pliegue, con cinco particiones y preprocesamiento ajustado exclusivamente sobre el entrenamiento correspondiente. El Ridge fijo alpha=1 obtuvo MAE 0.6427, RMSE 0.7839 y R² 0.2231 sobre 803 registros. Las predicciones constantes basadas en la media y mediana del entrenamiento obtuvieron MAE 0.7430 y 0.7455, respectivamente. Las métricas describen desempeño interno sobre la misma cohorte utilizada para el desarrollo.

Se distinguió esa comprobación de una selección anidada entre alpha=1, 10 y 100 con cuatro particiones internas. Dicha selección eligió alpha=10 en uno de los cinco pliegues externos y alpha=1 en los otros cuatro; obtuvo MAE 0.6427, RMSE 0.7826 y R² 0.2257. Aunque los MAE redondeados coinciden, no se atribuyen al mismo procedimiento ni a un único artefacto entrenado.

Las variables y las alternativas se habían explorado previamente, por lo que estos resultados no constituyen una validación externa ni un conjunto de prueba independiente no observado. No se contó con validación argentina, evaluación longitudinal independiente, puntos de corte clínicos ni prueba de utilidad para tomar decisiones individuales. La validación publicada del instrumento PMUM-SF tampoco valida por extensión esta regresión de cuatro entradas.

El artefacto entregado conserva su versión y huella registradas. Su comprobación técnica previa en Windows constituye un antecedente. La carga y revisión de ese binario con las guardas del candidato actualizado quedan sujetas al ejecutor de validación; las pruebas con predictores ficticios no se describen como verificación del original. Tampoco se afirma haber reproducido los bytes de su entrenamiento final.

## Texto propuesto: analizador histórico C1

La representación diaria v2 conserva valor, intervalo, estado de observación, cobertura declarada, indicadores de calidad y procedencia. La identidad de serie depende de la asignación de sujeto y dispositivo y de la versión de medición. Los registros faltantes no se convierten en duración cero, ni la cobertura desconocida se declara completa.

La referencia C1 se construye con mediana y escala robusta 1.4826*MAD de valores admisibles estrictamente anteriores al intervalo evaluado. El adaptador API candidato aplica la política all_prior_usable_records_v1. El detector acumula desviaciones estandarizadas en dos direcciones mediante CUSUM y produce un estadístico técnico. Si la referencia no es estimable o no hay evidencia admisible suficiente, se abstiene sin avanzar el estado. El emisor conserva un evento al cruce ascendente del umbral configurado; ese evento no fecha el comienzo del cambio ni mide su duración o gravedad.

Los parámetros k, umbral y madurez se proporcionan mediante un perfil explícito y versionado. El perfil de datos ficticios se utiliza exclusivamente para comprobar procesamiento, persistencia y reintentos. No es una calibración de uso real. No se introdujeron parámetros nuevos ni se incorporó el agregado v3.

La API guarda representación, estado y recibo en un mismo reemplazo atómico, con coordinación de escritor. Un reintento compatible recupera el resultado original y sus identificadores sin volver a avanzar CUSUM. Un contenido incompatible produce conflicto y no altera la historia. Las verificaciones adicionales cotejan los recibos y permiten auditar referencias mediante snapshots de sólo lectura; no reescriben resultados.

## Texto propuesto: evidencia histórica y alcance de la entrega

El archivo fuente de F12-C2 contiene 2.587 filas de 93 participantes MEDIATICINO. En esta fuente, 75 participantes aportan las 1.836 ventanas admisibles que producen 14.688 escenarios pareados de condición. Esos escenarios reutilizan trayectorias y no constituyen sujetos independientes. Se añaden perturbaciones conocidas a tres registros observados; 285 ventanas admitidas presentan saltos de días calendario en esa continuación. El experimento conserva como referencia sólo la historia humana no perturbada y expresa cada perturbación mediante la escala disponible en cada registro, por lo que sus tasas no validan por sí solas la política adaptativa del servicio API.

Los offsets de detección del experimento cuentan posiciones 0, 1 y 2 de esos registros, no necesariamente días transcurridos. Los denominadores de nuevos cruces excluyen las ventanas cuyo estado ya superaba el umbral al comienzo; no describen todas las ventanas ni estiman falsos positivos reales. El archivo guardado contiene resúmenes, sin los registros de cada escenario; su coherencia aritmética y correspondencia con el artefacto publicado se cotejan por separado de una reproducción completa.

Los intervalos del experimento se construyen desde DayInStudy con una fecha base artificial. Sus saltos corresponden a ese índice del estudio y no validan fechas reales, husos horarios ni límites de día Android. Además, el conteo experimental de cruces no ejecuta el emisor: en la primera observación elegible puede contar un cruce desde CUSUM cero, mientras que el emisor del analizador se abstiene de emitir si no dispone de estadístico elegible anterior. Las tasas experimentales no se identifican con tasas de DetectionEvent de la API.

No se dispone de etiquetas independientes que permitan interpretar los cruces como verdaderos o falsos eventos clínicos. No se presentan esas tasas como sensibilidad, especificidad o falsas alarmas clínicas. La población y semántica de duración del archivo tampoco se equiparan automáticamente con niños de 6 a 12 años o con captura Android interactiva.

Las pruebas técnicas del candidato actualizado verifican contratos, abstenciones, coordinación, persistencia, recuperación y reintentos con datos ficticios. Se documentan por separado las comprobaciones Linux realizadas y las pendientes Windows/Docker. La compilación Android, captura en teléfono físico y conexión con el backend real no forman parte de la evidencia de este bloque.

## Referencias para integrar a la bibliografía vigente

DOMOFF, S. E.; HARRISON, K.; GEARHARDT, A. N.; GENTILE, D. A.; LUMENG, J. C.; MILLER, A. L. Development and validation of the Problematic Media Use Measure: a parent report measure of screen media “addiction” in children. Psychology of Popular Media Culture, 2019, 8(1), 2–11. DOI: 10.1037/ppm0000163. Consultar la copia de autora enlazada en el inventario de fuentes.

NIST/SEMATECH. e-Handbook of Statistical Methods. Sección 6.3.2.3, CUSUM Control Charts. La teoría se cita con su alcance; no demuestra calibración de la versión robusta adaptativa implementada.

SCIKIT-LEARN. Documentación versión 1.7: DummyRegressor. Referencia de los baselines constantes mean y median.

Completar la cita bibliográfica del dataset HU y MEDIATICINO a partir de sus registros originales accesibles antes de consolidar referencias. No inventar autores, fecha o licencia a partir de un nombre de ZIP. Las huellas permiten trazabilidad técnica, pero no reemplazan la referencia académica.
