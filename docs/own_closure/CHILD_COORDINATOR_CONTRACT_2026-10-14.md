# Coordinador automático infantil: contrato y decisiones

Base local `e43695acbfabef512409cd5ca5f5a941c8434fac`. Rama nueva
`child-offer-coordinator-candidate`; ramas anteriores conservadas. Matías autorizó
completar tarea 1 y tomar decisiones justificadas de ingeniería el 14/10/2026.
Este contrato sustituye el bloqueo de política/coordinador de la auditoría previa.
No es redacción de tesis ni una política clínicamente validada.

## Política operativa v1

| Regla implementada | Justificación de ingeniería |
|---|---|
| Diurno: intervalo continuo verificado de al menos 45 min; desde 08:00 hasta antes de 20:00 | Umbral fijo y explicable para evitar ofertas ante usos breves; no se afirma que 45 min sea un límite saludable |
| El diurno termina antes si empieza la ventana de descanso configurada | Evita reabrir diurno después de una hora de descanso temprana |
| Descanso: de 60 min antes de la próxima hora resuelta hasta esa hora inclusive; tiene prioridad al abrir | Conserva la ventana existente; no depende de los 45 min diurnos |
| Espera compartida de 120 min desde la primera entrega confirmada | Evita sumar interrupciones por cambiar entre flujos o canales; sin excepciones por PMUM/C1 |
| Máximo total 3, diurno 2 y descanso 1 | Permite hasta dos oportunidades diurnas y una de descanso; no obliga a ofrecerlas ni a reservar un aviso que viole espera |
| Aplicar cada cupo tanto al día local como a 24 h móviles | Medianoche o cambio de offset no reinician el presupuesto; descanso puede suprimirse si la noche anterior ocurrió hace menos de 24 h |
| Una oferta automática por intervalo continuo identificado, entre ambos flujos | La misma sesión no se convierte en nuevas oportunidades por reinicio o por cambiar de canal |
| Vigencia de generación: 10 min; desde primera entrega, otros 10 min para responder | Limita propuestas obsoletas. El segundo canal no reinicia la vigencia |
| Dos rechazos explícitos consecutivos: pausa automática de 24 h desde el último | Respeta rechazo repetido; una selección o postergación rompe la secuencia. Silencio/descarte no la incrementa ni la rompe |
| Repetición: IDs de las últimas tres ofertas entregadas se pasan al selector existente | Usa su penalización/diversidad, sin inventar un nuevo ranking ni garantizar que jamás repita cuando hay pocas elegibles |

Todos son valores fijos de ingeniería autorizados, no parámetros calibrados,
inferidos de papers o elegidos para mejorar un benchmark. No hay adaptación por
diagnóstico, score, edad, C1 o supuesta realización. La validación profesional del
catálogo continúa pendiente. El objeto `POLICY` queda vinculado al store y sus
cambios requieren una migración explícita, no reiniciar silenciosamente el estado.

## Entrada confiable y fronteras

`analytics_service.child_offers.ChildOfferCoordinator` es el coordinador de
referencia de nuestro componente. Usa `select_activities` y, para comprobar
elegibilidad de un listado congelado, `recommend_activities` con todo el catálogo.
Conserva catálogo y algoritmo. No agrega HTTP, Android, notificaciones reales,
captura, backend, un estimador de sesiones o aprendizaje nuevo.

`OfferEvidence` exige IDs globales de perfil, serie e intervalo; timestamps ISO
con offset; próxima hora de descanso **ya resuelta** por el adaptador; autorización
automática, identidad, uso compartido, captura, pantalla, juego, período escolar
y elegibilidad explícitos. `capture_verified` significa cobertura/control del
intervalo completo, no simplemente que se pudo preparar un export. No se acepta
elegibilidad desconocida como lista completa. El fixture construye condiciones
conocidas; no demuestra que un teléfono pueda verificarlas.

El adaptador debe resolver zona horaria, cambios de hora y hora de descanso
ambigua/inexistente. El coordinador recibe instantes inequívocos y compara tiempo
transcurrido. Para diurno usa la hora local del instante de evaluación y la hora
local configurada de descanso. No deduce el calendario escolar o juego por sí
solo. Si estos hechos no son conocidos, el llamador no debe inventar booleanos.

El intervalo comienza sólo con evidencia controlada y termina en una transición
verificada a pantalla apagada. Un reinicio, callback, ausencia de muestra o cambio
de request ID no son intervalos nuevos. Serie/intervalo conservan su instante de
inicio; cambiarlo con los mismos IDs produce conflicto. El llamador conserva el
ID ante retry y no inventa otra serie para eludir cupos. El presupuesto es por
perfil y sobrevive a cambios de serie. Identidad incierta, teléfono compartido,
captura desconocida, pantalla apagada o período escolar suprimen automáticas.

La solicitud voluntaria y las funciones legadas siguen disponibles; no consumen
estos cupos automáticos. Las automáticas de la futura integración deben pasar por
este coordinador. Llamar además al motor legado de descanso constituiría un bypass
del presupuesto. No se certifica que Juanma ya haya realizado ese cableado.

## Identidad, estados y canales

`evaluate(request_id, evidence)` crea como máximo una oferta pendiente por perfil,
con `offer_id` UUID estable, evidencia congelada, lista/títulos, huellas del catálogo
y selector, y vigencia. La generación no equivale a entrega. Mientras existe una
oferta pendiente/entregada, otra oportunidad queda bloqueada. Dentro de la misma
oportunidad se conserva la oferta si sigue elegible y en su contexto. No se muta
una lista ya ofrecida para acomodar nuevos filtros: se suprime su presentación.

Juego activo propone canal `notification`; fuera de juego, `overlay`. Una
notificación confirmada puede pasar a overlay con **el mismo offer_id**. Sin
confirmación del primer canal no se autoriza ese cambio. La integración debe
deduplicar la presentación por offer_id/canal y evaluar con contexto fresco antes
de mostrarla; usar el DTO congelado sin esta comprobación es incorrecto.

`record_event` registra `delivered`, `delivery_failed`, `selected`, `rejected`,
`postponed` o `dismissed`. Sólo `delivered` incrementa indirectamente los cupos;
se cuenta la oferta, no el número de canales. La primera entrega conserva su
instante y el segundo canal no reinicia espera/TTL. Un acuse declara que el canal
se mostró, no que el niño lo miró ni realizó la actividad.

La respuesta exige entrega anterior, pertenencia al mismo perfil y ocurrir antes
del vencimiento. Selección exige ID de la lista ofrecida; otros eventos no admiten
ID seleccionado. Hay una respuesta por oferta. `dismissed` registra `ignored`,
sin convertirlo en rechazo. El vencimiento de una entrega registra estado
`ignored` y un evento derivado; no fabrica una respuesta del niño.

Una generación vencida sin acuse pasa a `delivery_unknown`. Bloquea nuevas
automáticas hasta reconciliar `delivered` o `delivery_failed`; jamás se cuenta
como entrega ficticia. El fallo confirmado libera la reserva, pero esa oportunidad
ya se consumió: no produce un bucle inmediato de ofertas en el mismo intervalo.
Si el llamador no puede resolver la entrega, sigue bloqueado hasta recuperación
explícita. Es una decisión conservadora ante pérdida de acuses, no un diagnóstico.

Eventos tardíos separan `occurred_at` de `now` de procesamiento. Puede recuperarse
una entrega/respuesta que realmente ocurrió dentro del plazo, manteniendo los
eventos derivados originales. No se aceptan tiempos futuros, anteriores a la
oferta o procesamiento que retrocede. Un acuse posterior de otro canal no puede
cambiar hacia atrás la primera entrega registrada; el protocolo exige confirmar
el primer canal antes de cambiarlo.

## Persistencia, recibos y DTO

SQLite y `BEGIN IMMEDIATE` cubren estado, eventos y recibo en una transacción.
La configuración y cantidad de recibos se comprueban antes de cada operación.
Inicializar exige `create=True`; reabrir usa el valor por defecto `False`. Un
store faltante, vacío/incompleto o de otra política no se reconstruye sin aviso.
No constituye respaldo, protección ante corrupción arbitraria o recuperación
del disco; tampoco acredita cifrado, autenticación, purga o rendimiento masivo.

El request ID identifica globalmente una petición al store. Retry conserva todos
sus campos, incluido `now`; obtiene el recibo original, más `replayed=True`.
Cambiar contenido con ese ID produce conflicto. Otro ID crea una evaluación nueva,
que consulta el estado vigente. El replay no vuelve a seleccionar, no genera
UUID, no escribe eventos ni cambia cupos. **Un recibo reproducido es evidencia
histórica, no permiso para volver a mostrar una oferta vencida o respondida.**

`history(profile_id)` devuelve ofertas actuales y eventos originales en DTO JSON;
la consulta es de lectura y no avanza reloj ni expiración. `evaluate` y eventos
realizan las transiciones temporales. Los recibos congelados conservan versiones
previas aunque el estado actual avance. No se sobrescriben recibos tras un acuse
tardío. No hay transacción distribuida ni doble escritura implícita en el JSONL
legado: mezclar ambos stores sin adaptador transaccional duplicaría fuentes.

Los IDs son pseudónimos, no anonimización. El store conserva filtros, intereses,
contexto y timestamps: debe estar bajo los controles de acceso, conservación y
eliminación del contrato de privacidad al integrarse. No incluye nombres,
credenciales, diagnósticos, datos PMUM o telemetría de aplicaciones. Los acuses
proceden de un adaptador confiable; esta librería no autentica una sesión remota.

## Criterios diferidos para integración real

- Identidad global y asignación inequívoca; cobertura real del intervalo sin
  completar huecos; reloj/zona/hora de descanso resueltos; escuela/juego verificables.
- Automáticas exclusivamente por el coordinador; voluntarias conservadas.
- Mismo offer_id entre canales; presentación deduplicada; comprobación fresca;
  acuse durable dentro de la validez, con hora real y reintento del mismo evento.
- Recuperación de acuses perdidos y store; permisos/restricciones Android;
  acceso, almacenamiento, purga y respaldos según privacidad.
- Dictamen de Cecilia para catálogo/condiciones, sin atribuirlo a este ensayo.

Estos criterios quedan registrados para Juanma/equipo. La tarea interna se cierra
con código y ensayo controlado; entrega visual, captura y eficacia reales siguen
diferidas y no se acreditan por el PASS.
