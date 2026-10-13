# Backlog único corroborado de Moderá

Actualización de lectura, 13/10/2026: este inventario conserva el estado de su
fecha. Para el candidato `1fd977c` y los cierres posteriores, usar
[JUANMA_DELIVERY_2026-10-13.md](JUANMA_DELIVERY_2026-10-13.md): motor adulto,
reglas 14/14, revisiones y pruebas Windows ya no están pendientes de implementación.
Las dependencias externas no se cierran por esa actualización.

Inventario de lo recuperable en esta auditoría, no certificación de que todos
los chats/archivos del proyecto estén accesibles. Base 94ff3a8 verificada; las
cuatro ramas entregadas permanecen intactas. Cambios nuevos en rama separada.

## Fuentes y fuerza de evidencia

- S1: código y documentos publicados de 94ff3a8;155 blobs verificados en snapshot
  acotado. Se leyeron módulos analytics/historical, collector/exportador/mapper,
  herramientas, tests e intervention_engine/history/service/reader.
- S2: salidas Windows compartidas por Matías:288 casos (287 PASS,1 omisión),15
  raíz,6 scripts; HTTP/persistencia/reinicio, Docker/health, manifiesto13066a14…,
  imagen8a8dac4d…. Commit/push94ff3a8 y status limpio. Evidencia declarada local,
  no archivos de Windows inspeccionados desde este entorno.
- S3: modera_analytics_auditoria_contrato_2026-10-11.md, versión1 leída completa:
  documenta el pedido de Juanma y marca arquitectura/rutas iniciales PROPUESTO.
  Su descripción de funcionalidades ausentes era correcta para esa fecha/base,
  no el estado posterior publicado.
- S4: búsqueda de contexto recuperó resúmenes de mensajes del11/10 sobre servicio
  único y formulario; no devolvió el texto literal completo original. El mensaje
  del formulario también está citado en el contexto visible del usuario. No se
  presume aceptación de todas las propuestas ni envío del último borrador.
- S5: politica_ofertas_automaticas_2026-10-10.md recuperada íntegra y secciones
  pertinentes auditadas; auditoría/propuesta,
  no política aprobada ni implementación diurna. Sus números/estados no se adoptan.
- S6: recomendaciones_tarjeta_adulto_2026-10-10.md recuperada íntegra y secciones
  pertinentes auditadas; propuesta con
  variantes/candidatas, revisión y decisiones pendientes. Su título no acredita
  aprobación. No se verificaron ahora todos sus papers ni se reutilizan sus
  afirmaciones sanitarias como reglas de código.
- S7: docs/f12/F12_A_EMULATOR_VALIDATION_REPORT, F12_B2, F12_C2 y docs/f16/status,
  scope, revisión profesional; antecedentes leídos, no reruns de sus datasets.
  E50 no fue leído completo aquí; las menciones a E50 en S5/S6 son referencias
  secundarias. No afirmar revisión formal completa de ese documento.
- S8: Texto pegado(20261012-045130).txt leído completo: consola de la publicación
  anterior61e31ce. Confirma un antecedente, no pruebas físicas nuevas.

No se abrió api.zip. No se tiene el código del backend de Juanma ni dictámenes
profesionales respondidos en las fuentes leídas. Tampoco export físico nuevo.

## Inventario y criterios de cierre

Estado: I=implementado; V=validación; C=conexión; D=decisión; P=propuesta. P0/P1/P2
son prioridad de este backlog, no aprobación clínica ni fechas comprometidas.

| ID/prioridad | Parte y estado actual | Evidencia | Dependencia / responsable | Criterio de cierre |
|---|---|---|---|---|
| B01/P0 | Servicio/API/worker/puerto único: I, V local Windows/Docker | S1/S2, analytics_api/http/settings/Docker | Juanma: integrar Compose/red/credencial | Backend consume health y POST de capacidades en su entorno, sin exponer token a Android |
| B02/P0 | Export F12 → v2: I, V con fixtures; C física pendiente | S1/S2, f12_export/f12_bridge/harness | Matías + Android SDK/teléfono | Build APK y paridad de bytes/límites/estado/duración; bitácora física y alcance explícito |
| B03/P0 | Tres brechas de contrato y paquete: correcciones nuevas; V Linux | Contraejemplos + tests de esta rama | Matías/entorno Windows: nuevo candidato | Minutos dentro de intervalo, computed_at al cierre, overlap coherente, paquete íntegro; nueva validación sin trasladarPASS94 |
| B04/P0 | Perfil/aparato/asignación/namespace: contrato propuesto; C pendiente | S1/S3/S4 | Juanma/equipo, backend autenticado | IDs reales documentados, separación de cuentas y asignaciones, prueba de autorización y ausencia de mezcla |
| B05/P0 | Cola/payload durable del backend: D/C pendiente | S1 y DAILY_EVIDENCE_CLOSURE | Juanma: DB/transacción/dispatcher | Crash antes/después de HTTP, replay estable, trabajo conservado y orden por serie; no confundir repo analytics con outbox |
| B06/P0 | Cierre diario: D; preflight offline I | EXPORT_PENDING/READY/ABSENCE, tests nuevos | Equipo/Juanma: quién/cuándo fija evidencia | Decisión explícita sin deadline inventado; no pendiente→MISSING automático; contrato/versiones y escenarios de aceptación |
| B07/P0 | Corrección tardía: D, API actual inmutable | S1, receipt/order409; S6 propone revisión | Equipo/Juanma | Procedimiento versionado aprobado, linaje/recibos originales y eventual replay aislado comprobado; no IDs ficticios para evadir |
| B08/P0 | C1 configuración de producto: D/V pendiente | S1/S7, perfilSMOKE_ONLY | Equipo/metodología | k/threshold/min_history justificados y aprobados con protocolo; no números por disponibilidad de fixtures |
| B09/P0 | Catálogo18 y restricciones funcionales: P/D/V profesional pendiente | S1, matrizv2 nueva, instrumentoF16 | Profesional + equipo; Juanma/UX | Dictamen por consigna/variante, requisitos y versiones, mapeo aceptado y pruebas de combinaciones |
| B10/P1 | None/desconocido/combinaciones: I,V técnica; C formulario real | S1/S4 y31 combinaciones testeadas | Juanma/Android | Ninguna exclusiva, omisión explícita, una movilidad, consolidación de disponibilidad/consigna; no none→aprobación global |
| B11/P1 | Persistencia/lease/recibos analytics: I,V local; operación real C | S1/S2 | Juanma: volumen/perfil/backup | Un escritor, restart/replay, corrupción/eliminación detectable, restauración documentada sin borrar marcas/locks |
| B12/P1 | Salud/autenticación/body límites: I,V; operación C | S1/S2 | Juanma/red interna | Readiness versus liveness y fallos401/400/409/503 tratados; token separado de autorización de perfil |
| B13/P1 | PMUM HU v1: experimental I,V artefacto anterior; C entrega backend | S1/S2 previo, ZIP/modelSHA | Juanma/equipo | Recepción/verificación de artefactos confiables, montajesRO y alcance interno; no uso familiar o alertas sin aprobación |
| B14/P1 | Formulario PMUM adulto/códigos/ventana30d: D/C | S1, adapter HU | Equipo/Juanma | Correspondencia exacta parental edad/códigos/categorías, faltantes→abstención; Android minutos no reemplazan declaración |
| B15/P2 | HU v2 sin sexo: P/experimental, no activado | S3 y guíaHU | Equipo/metodología | Evaluación separada y decisión justificada antes de cambiar modelo; no migración automática |
| B16/P1 | Motor voluntario/descanso y offer_id/respuestas: I legado, C pendiente | S1/S7, engine/history/service/reader | Android + equipo/Juanma | Registro vinculable y entrega visual confirmada, identidad/autorización/fecha, respuesta válida; ningún JSONL demuestra pantalla |
| B17/P1 | Ofertas diurnas y coordinador global: P/D, no implementado | S5; no existe en engine publicado | Equipo + Android | Política explícita, medición real-time/paridad, topes/esperas/consentimiento y entrega/errores; no usar histórico diario como disparo |
| B18/P1 | Integridad operativa del JSONL de ofertas: C/V pendiente | _append_jsonl no lease/fsync transaccional | Equipo/Juanma: elegir store | Reserva/escrituras/retry/entrega consistentes bajo concurrencia y corte; no transferir garantías del repositorioC1 |
| B19/P2 | Aprendizaje de preferencias: I conteo opcional, V/C pendiente | reader vincula oferta/respuesta; S7 | Equipo + profesional | Exposición/elección verificadas, no elegidas≠rechazadas, ponderación/diversidad evaluadas; no aprender de fuentes rotas |
| B20/P1 | Tarjeta adulta/7 contra 7: P/D/V, no API publicada | S6/S7 | Equipo/Juanma/profesional | Dueño único del agregado, calidad/paridad/serie, regla y textos aprobados, episodes/correcciones y comprensión con adultos |
| B21/P1 | Recomendaciones adultas G/R1–R4: P/V profesional pendiente | S6 | Profesional + equipo | Revisión registrada, texto/versiones aprobados, comprensión, abstención; no plantilla inventada ante falta de aprobado |
| B22/P2 | v3/agregados/contexto: candidato distinto, V/C pendiente | S1/S7 | Equipo/metodología/Android | Semántica/paridad/política evaluadas; no cambiar serie/ref C1 ni inferir cortes físicos a partir de v2 |
| B23/P1 | RF-10/CU-04/E50: D/documentación formal pendiente | S7 y referencias secundariasS5/S6 | Matías/equipo/tutor | Leer versión vigente y reformular requisito/caso de uso con alcance realmente aprobado, sin conservar riesgo clínico por herencia |
| B24/P2 | Dataset sintético 1400/modelo 11 variables: V metodológica pendiente | S7 scopeF16 | Equipo/metodología/profesional | Protocolo de plausibilidad/distribuciones/dependencias/sensibilidad; no validado por revisión del catálogo |
| B25/P2 | Validez poblacional/ground truth C1: V abierta | S7 MEDIATICINO/semisintético | Equipo/metodología | Declarar límites, protocolo/fuentes apropiados; rendimiento en perturbaciones no equivale a sensibilidad/especificidad real |
| B26/P1 | Android/UI/consigna accesible y teléfono compartido: C/V | S1, sin código app real revisado | Android + equipo | Acceso/modalidad, entrega confirmada, asociación real; SCREEN_INTERACTIVE no acredita quién mira |
| B27/P1 | AWS/despliegue/operación conjunta: C pendiente | S3/S4 solicita infraestructura | Juanma | Imagen y config adecuadas, volúmenes, secretos/red, health/restart/restore en entorno real; no ejecutado aquí |
| B28/P0 | Entrega documental/mensaje: borrador actualizado, envío no realizado por este agente | S1/S2 + nuevos documentos | Matías/Juanma | Actualizar estado del nuevo candidato trasWindows; enviar solo con versión/enlaces ciertos y recibir feedback de contrato |

## Secuencia recomendada sin ampliar implementación

1. Revisar/validar el candidato nuevo (B03), conservar94 y publicar solo una rama
   nueva cuando corresponda. B01 ya tiene una base técnica para integración.
2. En paralelo, compilar/probar teléfono (B02) y acordar identidad/cierre/outbox
   con Juanma (B04–B07). El formato no requiere esperar una aprobación clínica,
   pero la entrega de producto sí depende de configuración/alcance (B08).
3. Resolver variantes/formulario/profesional (B09–B10) antes de activar filtros
   por etiquetas. La prueba del selector no aprueba el catálogo.
4. Abrir bloques separados para ofertas (B16–B19), tarjeta/recomendaciones
   (B20–B21), v3/modelos/metodología (B13–B15/B22–B25), requisitos y despliegue.

## Decisiones externas agrupadas

Recomendación backend: job Python reutilizando el preparador, IDs existentes si
realmente representan asignación y namespace; tabla de asignación si falta.
Payload y reserva en almacenamiento transaccional antes de HTTP; no afirmar que
Juanma ya dispone de esa tabla. Acordar quién fija evidencia y guardar tardíos
como revisión pendiente antes de diseñar replay.

Recomendación catálogo: preguntas por tareas/requisitos y variantes revisadas,
sin deducir capacidades de diagnósticos/etiquetas. Ninguna solo resuelve su
pregunta, no disponibilidad ni acceso a consigna. Mantener unknown ante falta.

Recomendación ofertas/adultos: conservar como propuestas, validar primero
medición/tareas y comunicabilidad; PMUM fuera de frecuencia/actividades/alertas.
No adoptar números de esperas/topes deS5 ni reglas/M/K deS6 por estar redactados.

Este backlog recupera tareas que faltaban en la lista corta anterior —JSONL de
ofertas, formalizaciónRF-10/CU-04, dataset sintético, preferencias, regla/adulto—.
No permite asegurar exhaustividad sobre fuentes que no se pudieron leer.
