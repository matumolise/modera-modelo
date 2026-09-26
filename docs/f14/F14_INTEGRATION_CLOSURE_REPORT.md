\# Fase 14 — Integración del Historical Analyzer



\## 1. Objetivo



La Fase 14 tuvo como objetivo integrar el Historical Analyzer desarrollado y validado en las fases anteriores dentro del flujo técnico de Moderá.



El propósito no fue ampliar el detector con nuevas reglas ni conectar automáticamente una detección con alertas o recomendaciones. La fase buscó construir y verificar un primer recorrido técnico completo desde información observable obtenida en Android hasta una evaluación histórica persistible.



El primer vertical integrado corresponde a la duración diaria de pantalla interactiva reportada por Android.



Esta métrica debe interpretarse como un proxy técnico basado en los eventos disponibles mediante Android. No representa de forma directa atención visual, intención de uso, una sesión del niño ni una evaluación de uso problemático.



\---



\## 2. Separación de responsabilidades



Durante la integración se mantuvo la separación entre los componentes principales del proyecto.



\### 2.1. Modelo PMU



El flujo PMU conserva su responsabilidad sobre las features agregadas y la inferencia continua desarrollada previamente.



El resultado del modelo PMU no se utiliza como estado interno del Historical Analyzer y no se construyó un riesgo combinado entre ambos componentes.



\### 2.2. Historical Analyzer



El Historical Analyzer trabaja sobre representaciones temporales individuales y compara una observación actual con historia previa del mismo sujeto.



El flujo consolidado es:



`HistoricalRepresentation → Reference → DetectorEvaluation → DetectionEvent`



Una detección es un evento técnico. No constituye por sí misma una alerta, una recomendación, un diagnóstico ni una clasificación clínica.



\### 2.3. Intervenciones, alertas y recomendaciones



La Fase 14 no conecta automáticamente `DetectionEvent` con el motor de intervenciones existente.



La interpretación del cambio detectado, su comunicabilidad y la eventual generación de alertas o recomendaciones pertenecen a una capa posterior y requieren criterios semánticos y evidencia específica.



\---



\## 3. Arquitectura integrada



El primer vertical completo quedó organizado de la siguiente forma:



`RawAndroidUsageEvent`

→ normalización de eventos de pantalla

→ reconstrucción del intervalo diario

→ `BehavioralObservation`

→ adaptador versionado

→ `HistoricalRepresentation`

→ servicio del Historical Analyzer

→ construcción de referencia

→ CUSUM bilateral C1

→ `DetectorEvaluation`

→ decisión de emisión

→ posible `DetectionEvent`

→ persistencia de representación y estado analítico



No se creó una segunda arquitectura de captura Android. Se reutilizó el contrato producido por el logger diagnóstico desarrollado en F12.



Tampoco se incorporó una fachada adicional para unir componentes que ya podían componerse mediante sus interfaces existentes.



\---



\## 4. Definición del primer vertical



El fenómeno integrado es:



`DAILY\_USE\_DURATION`



La representación versionada correspondiente es:



`daily\_use\_duration\_minutes\_v1`



Para este vertical, la duración diaria se define operacionalmente como el tiempo acumulado, dentro de un intervalo diario explícitamente delimitado, durante el cual Android informa que la pantalla se encuentra en estado interactivo mediante la secuencia de eventos `SCREEN\_INTERACTIVE` y `SCREEN\_NON\_INTERACTIVE`.



Esta definición no debe reinterpretarse como:



\- tiempo durante el cual el niño necesariamente observó la pantalla;

\- tiempo de teléfono desbloqueado;

\- duración de una sesión conductual;

\- duración de uso de una aplicación;

\- indicador clínico de uso problemático.



\---



\## 5. Reconstrucción y calidad de captura



La integración diferencia el éxito de una consulta Android de la evidencia suficiente para reconstruir un intervalo diario.



Una consulta exitosa no implica por sí sola que exista información suficiente para considerar completo el día.



Para que el primer vertical considere suficiente la reconstrucción se requiere:



1\. cobertura continua de las ventanas de consulta sobre el intervalo objetivo; y

2\. conocimiento del estado de pantalla al comienzo del intervalo.



Cuando estas condiciones no se cumplen, la observación se representa como `MISSING`.



No se inventa un valor cero para completar información ausente.



`OBSERVED\_ZERO` queda reservado para un cero efectivamente representable bajo evidencia de captura suficiente.



La cobertura utilizada en esta primera integración no recibe artificialmente un valor numérico de `1.0`. Su cuantificación general continúa abierta.



\---



\## 6. Tratamiento de eventos Android



El contrato Python utiliza únicamente los campos del evento raw necesarios para este vertical.



Los eventos `SCREEN\_INTERACTIVE` y `SCREEN\_NON\_INTERACTIVE` se transforman a estados internos de pantalla. Otros tipos de eventos no se reinterpretan como duración diaria.



No se realiza deduplicación destructiva de eventos raw basada solamente en timestamp, tipo, paquete o clase, debido a que el contrato disponible no proporciona un identificador universal del evento Android.



La integración verifica además la trazabilidad entre cada evento raw utilizado y el `collector run` que respalda su ventana de consulta.



Los límites sintéticos utilizados durante la reconstrucción de un intervalo son recursos computacionales y no se reinterpretan como eventos Android realmente observados.



\---



\## 7. Integración con el Historical Analyzer



El `BehavioralObservation` resultante se transforma mediante un adaptador explícito y versionado a `HistoricalRepresentation`.



La representación conserva:



\- sujeto;

\- fenómeno;

\- intervalo temporal;

\- valor y unidad;

\- estado de observación;

\- cobertura;

\- indicadores de calidad;

\- provenance;

\- momento de cálculo.



El servicio de procesamiento recupera el historial y el estado analítico previamente persistidos, ejecuta el análisis C1 y guarda conjuntamente la nueva representación y el estado resultante.



Las representaciones fuera de orden o temporalmente superpuestas se rechazan en el flujo online actual.



Los huecos temporales pueden existir y no se rellenan con observaciones inventadas.



\---



\## 8. Persistencia



La primera persistencia integrada utiliza `FileHistoricalRepository`.



El repositorio mantiene:



\- representaciones históricas;

\- identidad del stream analítico;

\- estado CUSUM positivo y negativo;

\- último estadístico elegible necesario para la política de emisión.



La identidad del stream incluye sujeto, especificación de representación, familia del detector, parámetros analíticos y versión de análisis. Esto evita continuar accidentalmente un mismo estado después de modificar una configuración analítica.



La escritura conjunta utiliza un archivo temporal y reemplazo del documento previo para reducir el riesgo de dejar una versión parcialmente escrita.



Esta implementación no se presenta como una base de datos productiva ni como una garantía transaccional frente a cualquier tipo de fallo físico o concurrencia.



\---



\## 9. Emisión de DetectionEvent



La emisión mantiene una separación explícita entre evaluación y evento.



Un `DetectionEvent` sólo se genera cuando una evaluación elegible produce `CHANGE` y existe un cruce ascendente desde un estadístico elegible previo por debajo del umbral hacia un estadístico actual igual o superior al umbral.



Una primera evaluación elegible sin estadístico previo no establece artificialmente un cruce.



`ABSTAIN` no genera un evento y no reemplaza el último estadístico elegible.



La política actual no incorpora automáticamente:



\- reset;

\- rearm;

\- cooldown;

\- adaptación de referencia posterior a una detección;

\- alerta;

\- recomendación;

\- intervención.



Estas decisiones permanecen separadas.



\---



\## 10. Validación end-to-end de F14



Se incorporaron pruebas verticales que recorren las interfaces reales del sistema desde eventos Android hasta el Historical Analyzer.



Las pruebas verifican al menos los siguientes comportamientos:



\- un día Android reconstruible produce una observación diaria y llega a la persistencia histórica;

\- durante cold-start el analizador puede abstenerse sin perder la representación necesaria para formar historia;

\- una captura diaria incompleta queda como `MISSING` y conserva `value=None`;

\- un `MISSING` no se transforma en cero;

\- el historial y el estado analítico sobreviven a la reapertura de `FileHistoricalRepository`;

\- el procesamiento puede continuar después del reinicio;

\- una historia madura y un cambio técnico controlado pueden producir un cruce ascendente y un `DetectionEvent`.



Los parámetros utilizados para provocar de forma determinista el cruce en las pruebas son parámetros de integración del test. No constituyen defaults ni umbrales seleccionados para el producto.



La prueba de emisión tampoco atribuye significado clínico a la magnitud utilizada en el fixture.



\---



\## 11. Seguridad y privacidad — auditoría de alcance



\### 11.1. Aspectos verificables en el primer vertical



El contrato histórico del primer vertical no necesita almacenar contenido de mensajes, fotografías, contactos ni ubicación precisa para calcular `DAILY\_USE\_DURATION`.



La representación persistida contiene principalmente identificador de sujeto, fenómeno, intervalo temporal, valor agregado, estado, cobertura, indicadores de calidad y provenance.



Esto constituye minimización respecto del objetivo técnico de este vertical, pero no demuestra por sí solo minimización de datos en toda la aplicación Moderá.



\### 11.2. Identidad del sujeto



El contrato utiliza `subject\_id`.



La existencia de este campo no demuestra que el producto haya implementado pseudonimización. La generación, vinculación, almacenamiento y protección de la identidad del niño y del adulto responsable deberán definirse en la arquitectura productiva de identidad.



Por lo tanto, en el estado actual no se afirma que `subject\_id` sea un identificador pseudonimizado productivo.



\### 11.3. Persistencia en reposo



`FileHistoricalRepository` serializa la información histórica en un archivo JSON local.



La implementación actual no incorpora una capa propia de cifrado en reposo para ese archivo.



En consecuencia, esta persistencia debe considerarse una implementación local del MVP técnico y no una solución final de almacenamiento de información de menores.



\### 11.4. Autenticación y autorización



El Historical Analyzer no implementa por sí mismo autenticación ni autorización.



Antes de exponer información histórica mediante una aplicación productiva deberá garantizarse que el acceso corresponda al perfil y al vínculo niño–adulto autorizado definidos por Moderá.



\### 11.5. Retención y eliminación



La implementación actual no define una política productiva de retención ni eliminación automática del historial.



La cantidad de historia necesaria para el análisis deberá diferenciarse de la cantidad máxima de datos que el producto conserva.



Antes del MVP productivo deberá existir una política explícita de conservación, eliminación y tratamiento de datos históricos.



\### 11.6. Backups Android



El APK diagnóstico utilizado durante F12 declara actualmente `android:allowBackup="true"`.



Esta configuración pertenece al entorno diagnóstico y no debe trasladarse automáticamente a la aplicación productiva.



La política de backup y extracción de datos deberá revisarse antes de almacenar información productiva del menor en Android.



\### 11.7. Datos en tránsito



El vertical implementado en F14 es local y no demuestra todavía protección de datos durante una eventual transmisión hacia un backend.



Si las representaciones, análisis o datos derivados salen del dispositivo, la arquitectura productiva deberá definir protección en tránsito, autenticación del canal y autorización del receptor.



\### 11.8. Alcance de esta auditoría



Esta sección es una auditoría técnica del código actualmente integrado.



No constituye una certificación de seguridad, una evaluación jurídica ni una afirmación de cumplimiento normativo.



La normativa aplicable y los requisitos jurídicos específicos para el tratamiento de datos de menores deben documentarse y validarse separadamente antes de considerar completa la arquitectura productiva.



\---



\## 12. Decisiones cerradas en F14



Al cierre técnico de la fase quedan consolidadas las siguientes decisiones:



\- PMU e Historical Analyzer permanecen como flujos analíticos diferentes.

\- El primer vertical histórico integrado es duración diaria de pantalla interactiva.

\- `BehavioralObservation` y `HistoricalRepresentation` permanecen separados.

\- La representación histórica utilizada por C1 conserva historial previo y no utiliza la observación actual para construir su propia referencia.

\- `MISSING`, `OBSERVED\_ZERO` y `NOT\_APPLICABLE` mantienen semánticas diferentes.

\- Una captura incompleta no se transforma en cero.

\- La persistencia mantiene historia y estado analítico entre ejecuciones.

\- `DetectorEvaluation` y `DetectionEvent` son conceptos diferentes.

\- Un `DetectionEvent` técnico no genera automáticamente una alerta, recomendación o intervención.

\- No se reutiliza la generación sintética del modelo PMU como fuente productiva del Historical Analyzer.



\---



\## 13. Decisiones que permanecen abiertas



La Fase 14 no selecciona ni congela:



\- valor productivo de `k`;

\- threshold productivo;

\- madurez mínima definitiva;

\- umbral general de cobertura;

\- política general de quality flags;

\- adaptación de referencia después de una detección;

\- reset, rearm o cooldown del detector;

\- política definitiva de zona horaria y viajes;

\- semántica productiva de sesiones, aperturas, desbloqueos o transiciones;

\- métricas históricas adicionales;

\- conexión semántica entre detección, alerta y recomendación;

\- pseudonimización productiva;

\- cifrado final en reposo;

\- autenticación y autorización productivas;

\- política de retención y eliminación;

\- política productiva de backups;

\- arquitectura definitiva de almacenamiento local/backend.



Mantener estas decisiones abiertas evita presentar decisiones experimentales o de integración como requisitos ya validados.



\---



\## 14. Limitaciones del cierre



El cierre de F14 debe interpretarse dentro de las siguientes limitaciones:



1\. el primer vertical técnicamente integrado cubre únicamente la duración diaria de pantalla interactiva;

2\. la validación F12-C sobre trayectorias humanas reales se realizó sobre duración diaria y no valida automáticamente otras futuras representaciones;

3\. el logger Android fue validado en emulador y la replicación en dispositivo físico continúa pendiente;

4\. la continuidad de ventanas de consulta no garantiza que Android haya entregado absolutamente todos los eventos posibles;

5\. el contrato Android no dispone de un identificador universal de evento para una deduplicación destructiva general;

6\. la política de zona horaria y viajes no está cerrada;

7\. la persistencia JSON es adecuada para la integración técnica actual, no para afirmar seguridad productiva;

8\. el vertical no valida todavía interpretación psicoeducativa, alertas ni recomendaciones;

9\. la integración técnica no constituye validación clínica;

10\. los datos humanos utilizados en F12 no equivalen a una validación específica sobre niños argentinos de 6 a 12 años.



\---



\## 15. Criterio de cierre de F14



F14 puede considerarse técnicamente cerrada cuando:



\- el vertical Android → observación → representación → Historical Analyzer → persistencia es reproducible;

\- las pruebas históricas completas permanecen verdes;

\- el recorrido end-to-end verifica cold-start, datos faltantes, reinicio y emisión técnica;

\- el código y las pruebas quedan persistidos y sincronizados en el repositorio;

\- las limitaciones y decisiones abiertas quedan documentadas;

\- seguridad y privacidad quedan tratadas explícitamente sin afirmar capacidades todavía no implementadas.



Este cierre significa que el Historical Analyzer dispone de un primer vertical técnicamente integrado y reproducible.



No significa que estén finalizadas todas las métricas históricas posibles, la interpretación de los cambios, el sistema de alertas/recomendaciones ni la arquitectura productiva completa de seguridad y privacidad.
