# Tarea 1: resultado del cierre del coordinador infantil

## Resultado

**Cerrada en el alcance interno/documental autorizado.** El bloqueo anterior de
política/coordinador se resuelve con decisiones de ingeniería explícitas y una
implementación reproducible. Código probado:
`0d806c21e57ec3153031a78e721a2d2a13113114`.

Base verificada `e43695acbfabef512409cd5ca5f5a941c8434fac`; nueva rama
`child-offer-coordinator-candidate`. El remoto consultado confirmó publicada
`adult-messages-bounded-audit-candidate` en `7b7d0f5`; no devolvió una referencia
`modera-own-scope-closure-candidate`. No se presenta por eso e43695a como base
publicada: es la base local importada/verificada por Matías. No se alteraron
ramas anteriores ni se publicó el nuevo candidato.

Se agregan biblioteca del coordinador, pruebas, ensayo de cinco casos y contrato.
No cambian catálogo, selector, motor legado, C1, PMUM, mensajes adultos, Android o
backend. La evidencia generada por los tests en el JSONL legado se restauró antes
de guardar el commit; no forma parte de esta entrega.

## Matriz del bloque

| Frente | Estado y evidencia | Responsable / criterio |
|---|---|---|
| Diurno/descanso y prioridad | Implementado; ventana continua, horario, descanso temprano y medianoche | Nuestro componente; tests de apertura y bordes |
| Espera/cupos compartidos | Implementado; primera entrega, día local y 24 h móviles, cambio de offset | Nuestro componente; tests sin reinicio artificial de presupuesto |
| Rechazo, postergación y silencio | Implementado; pausa por rechazo explícito, silencio separado, expiración | Nuestro componente; no atribuir causas ni eficacia |
| Repetición y elegibilidad | Adaptador/selector originales; historial de entregas y revalidación de lista congelada | Nuestro componente; catálogo sigue provisional |
| Identidad y canales | UUID estable; mismo perfil/serie/intervalo; notificación a overlay tras acuse | Contrato probado; canal real a cargo de integración |
| Persistencia/retry/reinicio | Transacción SQLite, recibos originales, proceso nuevo, concurrencia, rollback | Nuestro componente; no confundir recibo histórico con permiso de mostrar |
| Acuses perdidos/tardíos | Entrega desconocida bloquea; reconciliación, tiempos reales, eventos anteriores conservados | Nuestro componente y protocolo del adaptador |
| Captura y entrega reales | Diferidas; criterios en contrato | Juanma/equipo; teléfono/backend/Android todavía sin ensayo real |
| Catálogo/condiciones | Diferidas; sin dictamen | Cecilia/equipo; no se atribuye aprobación profesional |

El nuevo store es propio del coordinador; no escribe además en el JSONL legado.
Su DTO y eventos conservan trazabilidad y los recibos guardan versiones originales.
Los llamadores automáticos futuros deben usarlo como única vía. Las funciones
legadas permanecen compatibles, pero no sustituyen esa coordinación.

## Verificación final

Linux, Python 3.12.14, código de esta entrega:

- **451 tests aprobados, 192 subtests**, una advertencia, 16,63 s. Incluye los
  nueve casos de raíz del lector, igual que el cierre propio previo.
- **45 tests nuevos del coordinador**: identidad, generación/entrega, guardas,
  prioridad, filtros, espera/cupos, rechazo/silencio, repetición, expiración,
  acuses tardíos, retry de evaluación/entrega/respuesta, proceso nuevo,
  concurrencia, rollback, estado faltante/incompleto y cambios de hora.
- Locale C, `PYTHONUTF8=0`, `PYTHONCOERCECLOCALE=0`, `-X utf8=0`:
  **46 aprobados** (45 nuevos y comprobación UTF-8 del catálogo), una advertencia.
- Ensayo reproducible: **PASS, cinco casos ficticios controlados**: canales y
  replay, descanso, rechazos, entrega desconocida y evidencia insuficiente.
- Advertencia heredada Starlette/httpx; no es un fallo y no se cambiaron dependencias.
- Windows del nuevo código **pendiente de ejecutar por Matías**. El 405/uno
  omitido/192 subtests anterior corresponde a e43695a, no a esta modificación.

Los fixtures construyen identidad, reloj, continuidad y cobertura conocidas.
El PASS acredita lógica, vínculos, persistencia y DTO bajo esas condiciones;
no acredita captura real, acuses reales, comprensión, seguridad clínica o reducción
del uso. Los valores de política son decisiones de ingeniería defendibles por su
función, no umbrales clínicos demostrados ni calibración de producto.

## Hallazgos durante implementación y revisión

La función faltante era la coordinación automática; no bastaba el writer legado.
Al construirla se corrigió una diferencia tupla/lista entre el primer DTO y su
recibo persistido. La revisión agregó guardas para contexto cambiado, filtro
cambiado, paso de canal antes del primer acuse, recibos eliminados y estado
borrado. También se probó que un descanso temprano no reabre ofertas diurnas y
que offsets explícitos en cambios de hora se comparan como instantes reales.
No se atribuyen esos hallazgos a defectos de un coordinador anterior inexistente.
Las conexiones SQLite se cierran explícitamente al terminar la transacción;
no se depende del recolector para liberar archivos al recuperar el store.

No queda otro faltante interno demostrado del alcance de tarea 1 tras esta
revisión. Eso no cierra automáticamente PMUM/C1/privacidad o la redacción: este
bloque no los reaudita ni reemplaza la evidencia original de otras tareas.

Contrato completo: `CHILD_COORDINATOR_CONTRACT_2026-10-14.md`.
Importación y verificación: `CHILD_COORDINATOR_POWERSHELL_2026-10-14.md`.
