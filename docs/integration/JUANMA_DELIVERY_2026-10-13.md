# Entrega técnica preparada para Juanma

Fecha: 13/10/2026. Este documento organiza el candidato y la integración.
No es redacción de tesis, publicación, despliegue ni confirmación de recepción.

## Versión que se entrega

**Candidato de código:** `adult-messages-integrated-path-candidate`,
`1fd977c8d03409778ea8ae67ca1cfc5fc842aba5`, árbol
`fabbb37b5fe584106f87166cc6ff089504fde52c`.

Cadena conservada: `e090bd4 → 109060e → 249168a → 7b7d0f5 → 1fd977c`.
Contiene el motor adulto, correcciones UTF-8, auditoría de persistencia y ensayo
integrado. No hay que reaplicar sus patches históricos ni mezclar worktrees.

La consulta remota de este bloque muestra `7b7d0f5` publicado en
`adult-messages-bounded-audit-candidate` y ninguna referencia
`adult-messages-integrated-path-candidate`. Matías importó y verificó `1fd977c`
localmente en Windows. Por tanto, no se ofrece un enlace GitHub como si el
candidato ya estuviera publicado. El bundle integrado ya entregado permite
transportar el código sobre `7b7d0f5`.

Esta preparación documental se realiza en otra rama:
`adult-messages-handoff-ready-candidate`, sobre `1fd977c`. Conserva exactamente
el código probado; agrega guías, ejemplos ficticios y evidencia documental.

## Función de cada componente

| Componente | Datos y salida | Relación con los demás |
|---|---|---|
| PMUM HU v1 | Cuatro características parentales/demográficas; estimación experimental de PMUM-SF | Endpoint interno independiente. No dispara mensajes, C1 ni actividades; no sustituye una puntuación observada del cuestionario |
| Preparador F12 | Binding autorizado y exports JSON/JSONL; duración diaria de pantalla interactiva v2, procedencia y estado | Reutilizar el adaptador Python. No sumar TV/tablet/consola manuales ni inferir quién usó el teléfono |
| Histórico C1 | Serie v2 y perfil explícito; análisis, estado y recibo original persistentes | Evento técnico, no tarjeta familiar. Se conserva `all_prior_usable_records_v1`; no se sustituye por ventanas 14/14 |
| Mensajes al adulto | Días observados/verificados de la misma serie; comparación y seguimiento del episodio | Genera explicación breve y consejo. C1 aporta referencias de evidencia, no un gate; PMUM no interviene |
| Actividades | Catálogo, contexto y elegibilidad explícita | Selector y flujos existentes se conservan. El endpoint de selección no crea una oferta ni acredita entrega/realización |

PMUM mantiene `hu_pmum_sf_experimental_v1`, cuatro entradas y el objetivo
`PMUMTotal/9`. Su binario y manifiesto son **externos al Git y a esta entrega**:
usar los originales ya verificados, no entrenar otro modelo para completar el
paquete. SHA-256 del joblib registrado:
`56c991f40e56d2241196dc6f9efc1c9027c079e98a1b67549f48b10292e371e0`.
Contrato y seis campos HTTP: [PMUM/C1](../model_closure/PMUM_C1_CONTRACT_2026-10-12.md).
No reemplazar categorías parentales por minutos Android ni mostrar el score
como diagnóstico/riesgo validado. Tampoco comparar sus estimaciones como un
estimador longitudinal validado.

## Evidencia de cierre técnico

| Revisión | Evidencia | Alcance y procedencia |
|---|---|---|
| `109060e` | Windows: 365 aprobados, 1 omitido, 190 subtests; demo PASS con `-X utf8` | Antecedente informado por Matías; no atribuido a revisiones posteriores |
| `7b7d0f5` | Linux: 378 aprobados. Windows: 377 aprobados, 1 omitido, 190 subtests; demo PASS sin `-X utf8` | Motor/persistencia y correcciones; consola aportada por Matías |
| `1fd977c` | Linux: 385 aprobados y 190 subtests; focalizadas sin modo UTF-8: 48 aprobadas | Ejecuciones del agente en el bloque integrado; XML en la evidencia ya entregada |
| `1fd977c` | Windows: 7 tests integrados; CLI PASS; regresión: 384 aprobados, 1 omitido y 190 subtests en 106,80 s | Consola aportada por Matías el 13/10. XML y directorio de ensayo permanecen en su Windows; no se recibieron aquí sus archivos |
| PMUM/C1, cierre del 12/10 | Original HU, HTTP Windows y Docker PASS | Antecedente separado de `83fc635`, conforme al resumen recibido; no acredita una ejecución Docker nueva con mensajes de `1fd977c` |

La advertencia de Starlette/httpx permanece; no hubo fallos por ella ni cambios
de dependencias. Los subtests no se suman a los tests. No se conoce aquí el nombre
del caso omitido en el último XML Windows; no se inventa su identificación.

El ensayo integrado usa datos ficticios controlados: 140 primeras evaluaciones
C1, ocho de mensajes, aumento/disminución con apertura–actualización–retorno,
dos casos insuficientes, seis versiones entre dos tarjetas. Reintenta todos los
recibos tras recrear runtimes y agrega cuatro reinicios antes de continuar los
episodios. No modifica estado/recibos/versiones por replay. Su coordinación es
del harness y no una integración automática ya implementada en el backend.
La calidad se justifica por el oráculo del fixture, con cobertura `null`;
no se deduce del éxito del preparador. Perfil C1: `smoke-only-not-calibrated`.

## Pendientes antiguos cotejados con cierres posteriores

Los IDs remiten a [MODERA_BACKLOG_2026-10-12.md](MODERA_BACKLOG_2026-10-12.md).
Este cotejo reemplaza su lectura como lista vigente, sin borrar antecedentes.

| IDs / tema | Estado vigente | Qué resta y a quién corresponde |
|---|---|---|
| B01/B03/B11/B12: API, guardas, persistencia, auth, transporte | Implementados y probados; Windows/Linux cerrados para el candidato | Juanma: red, secretos, volumen y recuperación en su entorno; Docker nuevo con mensajes aún no comprobado |
| B20: tarjetas, episodios y reglas | Implementado: 14/14 semanal, referencia congelada, retorno, vigencia, espera/tope, correcciones y DTO | Juanma: job, almacenamiento de enlace y panel. El 7/7 antiguo no es la regla vigente |
| B07: evidencia tardía | Mensajes admite revisión creciente y nuevas versiones; C1 conserva recibos originales | Equipo/Juanma: conservar evidencia tardía y enlazar revisión. No existe API de rebuild/corrección C1; no prometerla ni eludir 409 |
| B21: consejos | Textos breves iniciales implementados; no se eliminaron alertas/recomendaciones | Equipo/profesional: revisión de comprensión/contenido antes de afirmar aprobación para familias; no tarea de infraestructura de Juanma |
| B02/B04/B05/B06: captura, identidad, outbox y cierre diario | Adaptador y preflight implementados; recorrido ficticio probado | Juanma/Matías: IDs reales, quién fija evidencia/calidad, calendario y pruebas de captura/cola. Las pruebas relatadas por Juanma son antecedentes, no auditadas aquí |
| B08/B25: perfil C1 y validez poblacional | Núcleo conservado; antecedentes reales/semisintéticos documentados | Equipo/metodología: perfil de producto y evaluación externa. El smoke no es una calibración; no fabricar parámetros nuevos en esta entrega |
| B13/B14: HU y formulario | Contrato, artefacto original y evaluación interna existentes | Matías/equipo: procedencia del ajuste final, pregunta weekday completa y límites de fuente. Juanma recibe originales/campos exactos si se habilita uso interno |
| B09/B10: catálogo/condiciones | Resolución técnica de opciones y abstención conocidas; catálogo provisional | Equipo/profesional: dictamen y mapping funcional. Juanma integra known/unknown/none sin inventar filtros |
| B16/B17/B18/B19: ofertas/preferencias | Voluntaria/descanso y vínculos existentes; no equivalen a entrega visual ni coordinador diurno completo | Módulo infantil/equipo: entrega real, persistencia de ofertas y alcance diurno. No declarar terminada toda la app por cerrar mensajes |
| B15/B22/B24: HU v2, representación v3 y prototipo sintético 1.400 | Fuera del candidato actual; sin activación o validación transferida | Mantener separados. No son requisitos para documentar HU v1/C1/mensajes ni instrucciones para construir otro estimador |
| B23/B28: RF-10/CU-04 y entrega escrita | Paquete técnico preparado en este bloque; documento formal aún no integrado | Matías/equipo: redacción posterior contra la versión vigente, revisión y envío manual. No se redactó tesis aquí |
| B26/B27: UI real, Android, despliegue | No acreditados por el ensayo analytics | Juanma/Android/equipo: panel, autorización, captura y entorno. No se desplegó ni se envió mensaje a Juanma |

No se reabren el motor adulto, el replay ni la persistencia por estar todavía
enumerados en documentos viejos. Los parámetros de mensajes están definidos
como política de ingeniería del candidato, no como cortes sanitarios derivados
de papers ni como óptimos demostrados. Tampoco se descartan los límites de PMUM
por haber pasado los tests.

Hay evidencia real anterior: HU es una fuente parental transversal, y F12-B2/C2
usan trayectorias humanas reales/descriptivas y perturbaciones semisintéticas.
Eso no valida captura física Moderá, tarjetas con familias ni eficacia. No
presentar el proyecto como si toda su evidencia fuese ficticia o toda fuese real.

## Contrato y aceptación de la integración

Usar [BACKEND_ADULT_MESSAGES_CONTRACT_2026-10-13.md](BACKEND_ADULT_MESSAGES_CONTRACT_2026-10-13.md)
y sus ejemplos ficticios. Orden práctico para Juanma:

1. Fijar IDs de cuenta/perfil/dispositivo/asignación, zona y serie activa; autorizar
   desde el backend, sin confiar en un profile_id enviado libremente por Android.
2. Reutilizar el preparador, guardar originales/payload antes del HTTP y enviar
   C1 en orden por serie. Separar transferencia pendiente de ausencia confirmada.
3. Armar la entrada semanal de mensajes desde esos mismos días, con atribución
   y calidad justificadas. Persistir el request completo antes del envío.
4. Conservar recibo/evaluación/card_id/version y consultar historial vigente para
   el panel. Probar caída/reintento de su backend sin crear alertas duplicadas.
5. Mostrar título, explicación y consejo; agrupar por card_id y no revertir el
   panel cuando un retry devuelve una versión anterior original.

Para acreditar esa integración falta una traza real de extremo a extremo con
binding, export/huellas, request congelado, recibo y panel, más pruebas de
autorización, faltantes y retry del backend. No hace falta fabricar 28 días
reales para repetir la regresión: una demo histórica usa fixtures claramente
rotulados; una comprobación de captura física conserva su evidencia propia.

## Estado al entregar

Nuestra parte técnica de mensajes queda documentable en el alcance probado.
No se necesita otro benchmark, un nuevo estimador ni repetir suites por este
agregado documental. La recepción/publicación, integración real y revisión de
producto conservan sus responsables y criterios. No se afirma que toda la app
esté terminada. El siguiente trabajo editorial podrá describir lo implementado
y sus límites usando esta entrega; no se inicia automáticamente aquí.
