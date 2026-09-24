# F12-C2 — Validación semisintética stateful sobre trayectorias humanas reales

## 1. Objetivo

F12-C2 evalúa la respuesta técnica del detector histórico C1 implementado en Moderá frente a cambios conocidos introducidos sobre trayectorias humanas reales, preservando el estado secuencial acumulado por el detector antes del comienzo de cada intervención.

Este experimento corrige y supersede metodológicamente a F12-C1.

F12-C2 no estima sensibilidad, especificidad ni tasa de falsos positivos sobre población real, porque el dataset utilizado no dispone de Ground Truth independiente sobre cambios conductuales reales.

El objetivo es más acotado: comprobar cómo responde el detector implementado ante perturbaciones técnicas controladas cuando éstas se aplican sobre fondos longitudinales humanos reales y cuando el estado CUSUM previo se conserva correctamente.

## 2. Fuente de datos

Se utilizó `Dataset_LongFormat.csv` de MEDIATICINO.

SHA-256:

`cdfdb5b2d665efcfcc25da6337d2102877541201e7da55ff3f0e121b57f0b51e`

El artefacto contiene 2.587 registros correspondientes a 93 participantes.

Para F12-C2 se utilizó `totOnDurPerDayMin`, interpretada únicamente como duración diaria total distribuida por el estudio fuente.

No se presupone equivalencia con sesiones, aperturas de aplicaciones, desbloqueos ni otras métricas productivas de Moderá.

El uso de MEDIATICINO proporciona fondos longitudinales humanos reales, pero no constituye una validación poblacional específica sobre niños argentinos de 6 a 12 años.

## 3. Relación con F12-B

F12-B2 mostró que las trayectorias distribuidas presentan variación intraindividual, gaps y suficiente historia en una parte relevante de las observaciones para construir referencias robustas prequentiales.

F12-C2 utiliza esas trayectorias con una finalidad diferente.

F12-B responde principalmente:

> ¿puede construirse una referencia histórica sobre trayectorias humanas reales sin inventar observaciones?

F12-C2 responde:

> ¿cómo responde el detector implementado cuando se introduce un cambio técnico conocido sobre una continuación humana real?

Por lo tanto, F12-C2 no reemplaza a F12-B y tampoco vuelve a utilizar DetectionEventRate como supuesto false-positive rate.

## 4. Diseño contrafactual pareado

Para cada ventana admisible se construyen dos brazos sobre la misma trayectoria.

### Control

Continúa utilizando los valores humanos reales observados.

### Intervención

Utiliza la misma continuación humana, pero incorpora una perturbación técnica conocida.

Ambos brazos parten de:

- la misma trayectoria histórica;
- la misma referencia preintervención;
- el mismo estado CUSUM preintervención;
- la misma configuración del detector;
- la misma estructura de missingness;
- la misma cantidad de registros posteriores disponibles.

Las referencias posteriores continúan construyéndose exclusivamente con historia humana real estrictamente anterior.

Los valores perturbados no ingresan en las referencias posteriores.

De esta manera, la intervención modifica la observación evaluada pero no contamina artificialmente el baseline contra el cual se la compara.

## 5. Corrección metodológica respecto de F12-C1

La revisión posterior de F12-C1 identificó una amenaza metodológica relevante.

La implementación original de `run_arm()` inicializaba:

`state = CusumState()`

al comienzo de cada brazo experimental.

Esto introducía un reset del estado CUSUM exactamente en el punto de inicio de la intervención.

Sin embargo, la implementación del detector de Moderá conserva el estado entre evaluaciones elegibles y no realiza automáticamente dicho reset.

Por lo tanto, F12-C1 era reproducible respecto del procedimiento que había implementado, pero ese procedimiento no representaba correctamente el comportamiento secuencial que se pretendía evaluar.

F12-C2 corrige este problema reconstruyendo el estado preintervención mediante replay de la trayectoria humana real anterior utilizando el detector implementado.

Control e intervención reciben luego exactamente el mismo estado inicial reconstruido.

Por esta razón:

**F12-C1 queda supersedida como evidencia metodológica vigente.**

Su commit y sus artefactos históricos permanecen disponibles mediante Git para trazabilidad.

## 6. Reconstrucción del estado preintervención

F12-C2 incorpora `build_preintervention_state()`.

Para cada punto de intervención, la función recorre secuencialmente las observaciones reales anteriores.

En cada paso:

1. construye una referencia usando exclusivamente historia estrictamente anterior;
2. ejecuta `evaluate_c1()`;
3. conserva el `next_state` producido;
4. utiliza ese estado como entrada de la siguiente evaluación.

De esta manera, el estado entregado a los brazos control e intervención representa la acumulación producida por el detector sobre la trayectoria humana real anterior.

No se reconstruye el estado mediante una aproximación externa al producto: se reutilizan las funciones del Analizador Histórico implementado.

## 7. Configuraciones experimentales

F12-C2 conserva las configuraciones experimentales utilizadas para estudiar la respuesta del detector:

- `k = 0.5` y `k = 1.0`;
- `h = 3.0` y `h = 5.0`;
- `min_history = 7`;
- perturbaciones de `+1` y `+2` escalas robustas;
- ventana de tres registros observados posteriores.

Estos valores son condiciones del experimento.

No constituyen parámetros productivos definitivos de Moderá.

En particular:

**`min_history = 7` experimental ≠ madurez histórica productiva validada.**

Del mismo modo, `h = 3`, `h = 5`, `k = 0.5` y `k = 1.0` no representan una selección de parámetros óptimos.

## 8. Magnitud de las perturbaciones

Las perturbaciones se expresan respecto de la escala robusta individual disponible para la trayectoria correspondiente.

Por lo tanto:

**+1 escala robusta ≠ +1 minuto**

y:

**+2 escalas robustas ≠ +2 minutos.**

Las perturbaciones tampoco representan magnitudes clínicas ni umbrales de intervención.

Su finalidad es introducir cambios técnicos comparables respecto de la variabilidad histórica individual.

Dentro del experimento se estudia si una perturbación de mayor magnitud técnica produce una respuesta diferencial del detector.

## 9. Definición de nuevo cruce

Preservar el estado histórico introduce una distinción necesaria.

Una ventana puede comenzar con el estadístico CUSUM ya por encima del threshold debido a evidencia acumulada anteriormente.

En ese caso, observar posteriormente `CHANGE` no demuestra que la intervención haya provocado un nuevo cruce.

Por este motivo, F12-C2 distingue:

- excedencia preexistente del threshold;
- permanencia sobre el threshold;
- nuevo cruce ascendente durante la ventana.

Se considera nuevo cruce cuando:

`previous_statistic < threshold`

y:

`current_statistic >= threshold`

en una evaluación que no produce `ABSTAIN`.

Por lo tanto:

**DetectorEvaluation.CHANGE ≠ nuevo cruce del threshold.**

Esta definición pertenece al protocolo experimental de F12-C2.

No congela todavía la política productiva de emisión de `DetectionEvent`.

## 10. Ventanas y escenarios evaluados

Se obtuvieron 1.836 ventanas humanas base admisibles.

Cada ventana fue evaluada bajo ocho combinaciones:

- 2 valores de `k`;
- 2 valores de `h`;
- 2 magnitudes de perturbación.

Esto produjo:

**14.688 escenarios pareados de condición.**

Se omitieron 184 posiciones por no disponer de tres registros observados posteriores suficientes.

No fue necesario excluir ventanas adicionales por referencia inicial no estimable entre aquellas que cumplían los restantes criterios de admisión.

Las ventanas pueden solaparse dentro de una misma trayectoria.

Por lo tanto:

**14.688 escenarios ≠ 14.688 muestras estadísticamente independientes.**

Los resultados se interpretan descriptivamente y no como inferencia poblacional basada en independencia de las ventanas.

## 11. Excedencia preexistente del threshold

La reconstrucción stateful permitió identificar ventanas cuyo estado ya superaba el threshold antes de introducir la perturbación.

Para `k = 0.5` y `h = 3`:

- 656 de 1.836 ventanas;
- tasa aproximada: 0.3573.

Para `k = 0.5` y `h = 5`:

- 418 de 1.836 ventanas;
- tasa aproximada: 0.2277.

Para `k = 1.0` y `h = 3`:

- 289 de 1.836 ventanas;
- tasa aproximada: 0.1574.

Para `k = 1.0` y `h = 5`:

- 172 de 1.836 ventanas;
- tasa aproximada: 0.0937.

Estas ventanas se informan separadamente.

No se utilizan como denominador para atribuir un nuevo cruce a la ventana experimental, porque el threshold ya había sido excedido antes del inicio de la intervención.

Este resultado confirma que preservar el estado histórico modifica materialmente la interpretación del experimento respecto de F12-C1.

## 12. Resultados para perturbación de +1 escala robusta

Entre las ventanas elegibles para producir un nuevo cruce se obtuvieron los siguientes resultados.

### k = 0.5, h = 3

Ventanas elegibles: 1.180.

Control:

`control_new_crossing_rate = 0.218644`

Intervención:

`intervention_new_crossing_rate = 0.471186`

Intervención solamente:

`paired_intervention_only_rate = 0.288983`

### k = 0.5, h = 5

Ventanas elegibles: 1.418.

Control:

`control_new_crossing_rate = 0.116361`

Intervención:

`intervention_new_crossing_rate = 0.281382`

Intervención solamente:

`paired_intervention_only_rate = 0.181946`

### k = 1.0, h = 3

Ventanas elegibles: 1.547.

Control:

`control_new_crossing_rate = 0.110537`

Intervención:

`intervention_new_crossing_rate = 0.248869`

Intervención solamente:

`paired_intervention_only_rate = 0.149321`

### k = 1.0, h = 5

Ventanas elegibles: 1.664.

Control:

`control_new_crossing_rate = 0.058894`

Intervención:

`intervention_new_crossing_rate = 0.126803`

Intervención solamente:

`paired_intervention_only_rate = 0.072716`

La proporción de nuevos cruces fue mayor en intervención que en control para las cuatro configuraciones ensayadas.

## 13. Resultados para perturbación de +2 escalas robustas

Para una perturbación de mayor magnitud se obtuvieron los siguientes resultados.

### k = 0.5, h = 3

Ventanas elegibles: 1.180.

Control:

`control_new_crossing_rate = 0.218644`

Intervención:

`intervention_new_crossing_rate = 0.855085`

Intervención solamente:

`paired_intervention_only_rate = 0.667797`

### k = 0.5, h = 5

Ventanas elegibles: 1.418.

Control:

`control_new_crossing_rate = 0.116361`

Intervención:

`intervention_new_crossing_rate = 0.631876`

Intervención solamente:

`paired_intervention_only_rate = 0.532440`

### k = 1.0, h = 3

Ventanas elegibles: 1.547.

Control:

`control_new_crossing_rate = 0.110537`

Intervención:

`intervention_new_crossing_rate = 0.630899`

Intervención solamente:

`paired_intervention_only_rate = 0.531351`

### k = 1.0, h = 5

Ventanas elegibles: 1.664.

Control:

`control_new_crossing_rate = 0.058894`

Intervención:

`intervention_new_crossing_rate = 0.358774`

Intervención solamente:

`paired_intervention_only_rate = 0.304688`

En las cuatro configuraciones, la perturbación de +2 escalas produjo una proporción mayor de nuevos cruces que la perturbación de +1 escala.

Esto constituye evidencia de una respuesta técnica diferencial ante las magnitudes ensayadas.

No demuestra relevancia clínica de dichas magnitudes.

## 14. Interpretación del brazo control

Los nuevos cruces observados en el brazo control no deben denominarse falsos positivos.

El brazo control contiene continuaciones humanas reales y el dataset no dispone de Ground Truth independiente que determine que durante esos períodos no ocurrió ningún cambio real.

Por lo tanto:

**control_new_crossing_rate ≠ false-positive rate.**

Las tasas del control describen únicamente la frecuencia de nuevos cruces técnicos observados sobre las continuaciones humanas reales utilizadas por el experimento.

No deben utilizarse para calcular especificidad.

## 15. Primer nuevo cruce

Cuando la intervención produjo un nuevo cruce dentro de la ventana experimental, se registró el offset de la primera ocurrencia.

El offset es base cero:

- `0`: primer registro observado posterior;
- `1`: segundo registro observado posterior;
- `2`: tercer registro observado posterior.

Los nuevos cruces observados ocurrieron dentro de esta ventana de tres registros.

La mediana del primer nuevo cruce fue generalmente 1 en las configuraciones ensayadas.

Estos offsets no deben interpretarse automáticamente como cantidad de días calendario, porque las trayectorias distribuidas pueden contener gaps y los tres registros requeridos no son necesariamente tres días consecutivos.

## 16. Interpretación de k y h

Dentro de las condiciones experimentales evaluadas, configuraciones con valores mayores de `k` o `h` produjeron menos nuevos cruces.

Este resultado no se utiliza para seleccionar una configuración ganadora.

Una mayor frecuencia de respuesta frente a una perturbación técnica no implica automáticamente una mejor configuración productiva.

Del mismo modo, una menor frecuencia de cruces sobre el brazo control tampoco implica automáticamente una configuración superior.

F12-C2 no congela:

- `k`;
- threshold `h`;
- madurez histórica;
- política de adaptación de referencia;
- reset;
- cooldown;
- rearmado;
- política de emisión de eventos.

## 17. Separación entre evaluación técnica y DetectionEvent

El experimento utiliza el nuevo cruce del threshold como variable técnica de evaluación.

Esto no significa que la política productiva de `DetectionEvent` ya esté definida.

Continúan abiertos:

- persistencia necesaria del estado de emisión;
- comportamiento frente a `ABSTAIN`;
- tratamiento de permanencia sobre threshold;
- reset posterior a una emisión;
- cooldown;
- rearmado;
- adaptación de la referencia después de una detección.

Por lo tanto:

**new_threshold_crossing experimental ≠ DetectionEvent productivo validado.**

La definición de esa capa corresponde a la consolidación posterior del Analizador Histórico.

## 18. Persistencia agregada y minimización de datos

La implementación inicial de F12-C1 persistía los escenarios individuales utilizados durante el experimento.

Esto produjo un artefacto de tamaño innecesariamente grande para las conclusiones que debían conservarse.

F12-C2 modifica la política de persistencia.

Los escenarios pueden existir durante la ejecución para calcular los resultados, pero no se incluyen en el artefacto final.

El JSON persistido contiene resultados agregados y metadatos suficientes para auditar el experimento.

El diseño registra explícitamente:

- `shared_preintervention_detector_state = true`;
- `preintervention_state_replayed_with_product_detector = true`;
- `new_threshold_crossing_distinguished_from_change_state = true`;
- `preexisting_threshold_exceedance_reported_separately = true`;
- `scenario_level_records_persisted = false`;
- `overlapping_windows_treated_as_independent_samples = false`.

Esta decisión reduce la persistencia de datos sin eliminar la evidencia necesaria para las conclusiones agregadas.

## 19. Artefacto vigente

El artefacto vigente es:

`artifacts/f12/f12_c2_stateful_semisynthetic_duration.json`

SHA-256 reproducido:

`053d7905dad88b64357a23e9e5dc7183977a57b4d9a183120115c24985dd4acd`

La reproducción confirmó:

- `scenario_count = 14688`;
- ausencia de escenarios individuales persistidos;
- reproducción de los resultados agregados esperados.

El artefacto anterior de F12-C1 fue eliminado de la versión vigente del repositorio para evitar mantener una salida de más de un millón de líneas que ya no representa la metodología actual.

Permanece recuperable mediante la historia Git.

## 20. Pruebas automatizadas

Durante la reproducción final se ejecutó el conjunto actual de tests automatizados del Analizador Histórico mediante `unittest`.

Resultado:

**51 tests ejecutados, 51 correctos.**

También se ejecutó `git diff --check` sin errores.

El resultado de los tests aporta evidencia de que la corrección de F12-C2 no produjo fallas detectadas por el conjunto automatizado existente.

No debe interpretarse como sustituto de la validación metodológica específica del experimento.

## 21. Límites

F12-C2 no demuestra:

- sensibilidad clínica;
- especificidad clínica;
- tasa real de falsos positivos;
- capacidad diagnóstica;
- identificación validada de uso problemático;
- relevancia clínica de +1 o +2 escalas;
- configuración óptima de CUSUM;
- threshold productivo definitivo;
- madurez histórica óptima;
- validez sobre todas las representaciones históricas;
- validez poblacional específica para niños argentinos de 6 a 12 años;
- eficacia de alertas;
- eficacia de recomendaciones.

F12-C2 tampoco constituye una validación end-to-end desde `UsageEvents`.

Los fondos longitudinales utilizados provienen de MEDIATICINO y no del logger Android de F12-A.

Por lo tanto:

**F12-A + F12-B + F12-C ≠ pipeline productivo end-to-end ya validado.**

## 22. Conclusión

F12-C2 corrige la principal amenaza metodológica identificada en F12-C1 al preservar el estado CUSUM acumulado antes del comienzo de cada ventana experimental.

La corrección permitió distinguir las excedencias preexistentes del threshold de los nuevos cruces ocurridos durante la ventana.

Sobre las trayectorias humanas reales evaluadas, las perturbaciones conocidas produjeron una mayor proporción de nuevos cruces que las continuaciones control en las cuatro configuraciones ensayadas.

Asimismo, una perturbación de +2 escalas robustas produjo una mayor proporción de nuevos cruces que una perturbación de +1 escala en las cuatro configuraciones.

Estos resultados respaldan el comportamiento técnico del detector dentro del alcance experimental definido.

No proporcionan Ground Truth conductual ni justifican seleccionar automáticamente parámetros productivos.

## 23. Trazabilidad y estado

F12-C1 permanece disponible históricamente mediante el commit:

`5a4619157c06154d19f295701079a930894f5f51`

pero queda supersedida metodológicamente.

F12-C2 fue persistida mediante:

`16e5086433d94f95c4be246e5ca1def1d1c6833d`

en la rama:

`phase12-f12c-stateful-correction`

La verificación posterior confirmó igualdad entre:

`HEAD`

y:

`origin/phase12-f12c-stateful-correction`

para dicho commit.

Estado:

**F12-C2 = REPRODUCIDA + PERSISTIDA + SINCRONIZADA EN SU ALCANCE EXPERIMENTAL.**

La política productiva de eventos, reset, cooldown, rearmado, adaptación de referencia y selección definitiva de parámetros permanece abierta para la consolidación posterior del Analizador Histórico.