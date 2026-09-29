# F16: recibos históricos y alcance del motor infantil

## Base y estado

El ajuste de recibos se preparó sobre b52667a99864d1bb5279ff4e347e5838e32d6870
y se integró en c38abb1. F12 (bef0db6), recibos durables (b52667a),
elegibilidad infantil (8abd7ab) y ofertas vinculadas (0bc5ea9) están en
phase14-integration. La lectura verificada de ofertas se añade en el bloque
posterior de esta sección.
No declara cerrado F16, RF-10/CU-04 ni la validación profesional.

## Correcciones frente a la adenda candidata F16.2, versión 11

- La fecha computed_at de una representación recalculada no modifica su
  compatibilidad. Deben coincidir los demás campos, procedencia y políticas.
  Se devuelve el resultado original y se conserva la fecha persistida.
- Formato 3: records_without_receipt identifica excepciones explícitas y
  receipts_required marca la activación. Después del primer recibo no se admite
  guardar progreso nuevo sin resultado. Una asociación ausente provoca un error
  de integridad; no se recalcula silenciosamente.
- Formato 1: los registros se reconocen como legacy sin inventar recibos.
- Formato 2: una ausencia se clasifica unclassified, porque el formato anterior
  no permite demostrar si es legado o pérdida. Ese registro no es recuperable
  automáticamente; una entrada posterior válida puede continuar el stream y
  conservar la excepción explícita. No se declara íntegro el resultado ausente.
- La lectura migra en memoria sin reescritura. Una nueva escritura publica
  formato 3. Los lectores anteriores no admiten este formato: conservar una
  copia del archivo antes de actualizar si se necesita volver al código anterior.
- Los recibos nuevos guardan previous_state, evidencia del estado previo al
  procesamiento. No se inventa este dato en recibos anteriores.

Se mantiene un único escritor por archivo. La comprobación de asociaciones
no es una defensa contra manipulación deliberada del JSON. No se incorporan
comunicabilidad, riesgo, recomendaciones ni cambios a HistoricalInterpretation.

## Verificación de preparación

`python -m unittest discover -s tests/historical`: 163 casos, 162 aprobados,
1 omitido porque el artefacto binario PMU no está disponible en este entorno.
Se añadieron siete regresiones: fecha de representación, recibo eliminado,
activación, legado explícito, ausencia ambigua v2, recuperación intacta v2 y
preservación del estado anterior a un evento tras avances posteriores.
La ejecución completa en el proyecto del usuario queda pendiente.

## Motor infantil existente: reutilización y pendientes

La inspección de recommendations.py, intervention_engine.py,
intervention_history.py e intervention_service.py partió de b52667a y se
actualizó con los bloques infantiles posteriores:

| Componente | Disponible | Pendiente |
| --- | --- | --- |
| Selección | Contexto, intereses, penalización de repetición, variedad de categorías, elegibilidad funcional explícita y salida 0..N | Revisión profesional del catálogo y criterios de elegibilidad específicos por edad/capacidad |
| Activación | Solicitud voluntaria y transición al descanso | Validación de reglas operativas de producto |
| Catálogo | Actividades y metadatos básicos | Revisión profesional, requisitos y adaptaciones respaldadas; catálogo no congelado |
| Respuestas | Oferta registrada antes de la respuesta mediante `offer_id`; selección, rechazo, postergación o ignorado | Integridad referencial al leer el historial, versión estable de la oferta e integración obligatoria en la app |
| Aprendizaje | No se observa actualización por preferencias históricas | Aprender de elecciones con exposición conocida y conservar variedad |

Los registros nuevos distinguen `event_type=offer` y `event_type=response`.
El JSONL previo no tiene `event_type` y sigue siendo legado. La función anterior
de registro de respuestas continúa disponible y puede producir `offer_id=null`;
por eso esta etapa aporta trazabilidad cuando se usa el flujo nuevo, pero aún
no garantiza que toda respuesta corresponda a una oferta persistida.

Orden propuesto de implementación:
1. Trazabilidad de ofertas y respuestas antes de inferir preferencias.
2. Preferencias aprendidas con diversidad y evidencia suficiente de exposición.
3. Evaluación separada de IA para selección, adaptación o generación.

### Lectura de exposición verificada

El lector `read_linked_offer_responses` acepta únicamente respuestas posteriores
a una oferta presente en el mismo JSONL. Verifica identidad del niño, origen,
contexto, lista y orden de actividades, selección válida y una sola respuesta
por oferta. Una referencia rota o incompatible interrumpe la lectura con error;
no se transforma en una preferencia. Las ofertas sin respuesta no producen una
elección observada. Las respuestas legadas sin `event_type` y las respuestas
nuevas con `offer_id=null` quedan fuera de los pares para aprendizaje.

Este lector no calcula preferencias ni confirma realización de actividades.
No interpreta el tiempo posterior sin pantalla como efecto de una actividad.
El catálogo todavía necesita identidad/versionado estable para comparar ofertas
antiguas tras una revisión profesional. La política sobre múltiples respuestas
a una misma oferta requiere una decisión explícita antes de habilitarlas.

Elegir no demuestra realizar; dejar de usar el teléfono no demuestra beneficio
causado por una actividad. El motor infantil no se dispara por score PMU,
severidad ni magnitud CUSUM.

## Comunicación al adulto

Sigue pendiente resolver criterios de publicación y revisar profesionalmente
el contenido. La asociación temática general con fuentes y posibilidad de
abstención continúa como candidata. No hay obligación de orientar por evento.
La app familiar/backend no está disponible en este repositorio; no se justifica
introducir aquí colas, confirmaciones de entrega ni tablas adicionales por
anticipación. El analizador técnico y la comunicación al adulto son contratos
separados.
