# F16: resultado durable del procesamiento histórico

## Alcance y estado

Cambio preparado sobre `bef0db66da4003ac65439de281f821477fc44f1c`.
La verificación descrita corresponde al espacio de trabajo de preparación;
la aplicación, prueba y commit en el checkout del proyecto deben registrarse
por separado. Este documento no declara cerrado el conjunto de F16.

El servicio conserva el resultado técnico de cada nueva representación en
el mismo archivo y reemplazo atómico que su representación y estado analítico.
El recibo contiene la identidad del stream, la versión del emisor y el
`HistoricalAnalysisResult` completo: referencia, evaluación, emisión (incluida
la ausencia de evento) y estado siguiente. No se necesita una cola, backend
o entidad de comunicación para recuperar este resultado local.

`HistoricalInterpretation` conserva su contrato descriptivo. Su persistencia
no forma parte de este cambio; puede construirse usando el resultado recuperado
y la representación original. La prueba de recuperación verifica esa posibilidad.

## Contrato de reintento

La identidad utilizada sigue siendo `representation_record_id`, única en el
repositorio. Un reintento compatible devuelve el resultado guardado sin ejecutar
otra vez el analizador ni escribir el archivo.

Deben coincidir:

- La representación completa: identidad, sujeto, especificación, fenómeno,
  intervalo, valor, unidad, estado, cobertura, flags, procedencia y `computed_at`.
- La identidad del stream: sujeto, especificación, familia, parámetros C1 y
  versión de análisis.
- `emitter_version`, incluso cuando la evaluación original no emitió evento.

Los nuevos `evaluation_id`, `event_id`, `computed_at` y `emitted_at` suministrados
al **servicio** en el reintento no reemplazan los originales. Estos metadatos
del intento se diferencian del `computed_at` contenido en la representación,
que pertenece a la entrada persistida y sí debe conservarse.

El `next_state` del resultado recuperado describe aquel procesamiento. No es
necesariamente el estado actual del stream. Recuperar un recibo anterior nunca
reemplaza el estado de procesamientos posteriores.

Un cambio incompatible provoca `ValueError` antes de publicar modificaciones.
Cambiar una política no convierte un reintento en un reanálisis autorizado.

## Archivo y compatibilidad

El formato conjunto de `FileHistoricalRepository` pasa de 1 a 2, con un mapa
`receipts`. Los otros stores de estado o representaciones mantienen su formato.

Se pueden leer archivos de formato 1. La lectura los adapta en memoria y no
reescribe el archivo. Una escritura posterior publica formato 2 conservando
representaciones y streams anteriores. No se fabrican recibos para registros
antiguos: volver a procesar una identidad ya guardada sin recibo produce un error
explícito. El código antiguo de formato 1 no puede leer un archivo ya actualizado
a formato 2; volver a aquella versión requiere recuperar una copia anterior o
diseñar una conversión explícita.

`save_analysis_progress` conserva su uso previo sin resultado para compatibilidad
con los consumidores de bajo nivel. Ese uso no crea recibos. El servicio
`process_c1_representation` siempre suministra el resultado completo.

## Límite operativo

El repositorio requiere **un único escritor**: el llamador debe serializar
el procesamiento que usa el mismo archivo. El reemplazo atómico no implementa
exclusión mutua entre procesos ni resuelve actualizaciones concurrentes.

La prueba de fallo anterior a `os.replace` verifica que no se publique progreso
parcial. La de respuesta perdida después del guardado verifica que un reintento
recupere el evento original. Estas pruebas no equivalen a validar todos los
fallos físicos del sistema de archivos o cortes de energía.

## Verificación en preparación

Comando: `python -m unittest discover -s tests/historical`.

Resultado: 156 pruebas descubiertas, 155 satisfactorias y 1 omitida por ausencia
del artefacto PMU en este espacio de trabajo. La omisión corresponde a la
predicción PMU, no a las pruebas de recibos.

Se agregan diez pruebas de recibos y se sustituye la expectativa histórica de
rechazar todo duplicado por la recuperación del resultado compatible.
Se cubren ABSTAIN, NO_CHANGE y emisión de DetectionEvent, fechas e IDs originales,
reapertura, reintentos de registros anteriores, conflictos de entrada y políticas,
fallo antes de publicar, respuesta perdida tras publicar, lectura del formato
anterior y rechazo de formato 2 sin mapa de recibos.

También se verificaron los hashes de los 28 archivos base disponibles del módulo
y sus pruebas contra el árbol de GitHub en el commit indicado. El parche se
comprueba sobre una copia limpia y sus archivos resultantes se comparan con los
archivos probados.
