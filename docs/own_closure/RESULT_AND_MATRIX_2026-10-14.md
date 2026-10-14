# Resultado transversal: cierre propio antes de redactar

> Estado histórico del cierre e43695a. El cierre posterior de tarea 1 está en
> `CHILD_COORDINATOR_RESULT_2026-10-14.md`: el bloqueo de coordinación infantil
> queda resuelto en el componente. Esta actualización no reaudita las demás filas
> ni ignora la evidencia PMUM recuperada después en el chat.

> Tarea 2 posterior: `PMUM_PROVENANCE_CLOSURE_2026-10-14.md` cierra la cadena
> recuperable de PMUM, atribución de errores y NoChildren. La matriz inferior
> conserva su estado histórico; no debe usarse como lista de bloqueos vigente.

14/10/2026. Base `1f67111c8fd9c9b45124bfd0bf5182490a9d4765`, rama nueva
`modera-own-scope-closure-candidate`. El bloque se ejecutó sin tocar catálogo,
Android/backend, datos reales, PMUM/C1/mensajes, parámetros o despliegues.
No se redactó tesis, publicó, hizo merge o contactó terceros.

## Veredicto

Se completó la auditoría de los cuatro frentes, se corrigieron defectos del
historial infantil y se guardó un checkpoint por bloque. **NO está cerrado todo
para redactar nuestra parte como terminada.** Hay dos bloqueos propios concretos:
política/coordinador infantil aún no aceptados/implementados y originales de
PMUM/registro del ajuste no disponibles. No se ocultan como limitaciones menores
ni se decide unilateralmente que dejaron de formar parte del alcance.

Sí se puede describir con evidencia el candidato técnico existente y el alcance
experimental C1/PMUM, pero esta tarea no inicia esa redacción ni la declara final.
La decisión anterior de «cuatro frentes bastan» era un plan de investigación,
no garantía de que toda evidencia necesaria fuese recuperable.

## Matriz final

| Función/afirmación | Estado | Evidencia y responsable | Criterio de cierre |
|---|---|---|---|
| API, representación diaria y recibos C1 | Cerrado técnico en alcance probado | Código/contratos y evidencia heredada; equipo | Conservar alcance y originales; no repetir el benchmark |
| Mensajes al padre con explicación/consejo, revisiones y replay | Cerrado técnico | `1fd977c`, Linux/Windows y ensayo ficticio; equipo | No atribuir eficacia ni entrega real; implementación se conserva |
| Escritura infantil, identidad y vínculos | Corregido y probado Linux | Ocho escenarios defectuosos contando bypass temporal y tipado; doce tests nuevos; Matías | Nuevo candidato Windows pendiente de su propia comprobación |
| Repetición del mismo evento congelado | Cerrado en writer | Concurrencia y nuevo proceso; bytes originales conservados | No reconstruir UUID/fecha en retry; mismo objeto/evento |
| Coordinador diurno/descanso, cupos y rechazo/expiración | BLOQUEADO, no implementado | Código sólo voluntaria/descanso; propuesta leída y chats sin aceptación; Matías/equipo | Política explícita aceptada y luego implementación/pruebas. Mantener 60 min existentes no resuelve el coordinador |
| Entrega mostrada, misma oportunidad entre canales y realización | Diferido por usuario | No hay app/backend auditados; Juanma/equipo | Prueba real y ACK/evento observable; selección no prueba realización |
| PMUM: dominio/cohorte/código/evaluación fija versus anidada | Cotejo cerrado documental | Loader, train, auditoría y antecedentes; Matías | Mantener cifras de sus ejecuciones originales y alcance interno |
| PMUM: cadena completa del binario original | BLOQUEADA por originales | Hash registrado y PASS Windows anterior; no joblib/manifest/log aquí; Matías | Aportar originales y registro del ajuste/enlace al resultado; no sustituir por entrenamiento nuevo |
| Weekday completo y recodificación NoChildren | Evidencia pendiente | Metadata truncada/antecedente; Matías/fuente | Recuperar instrumento/recodificación antes de afirmar su semántica completa |
| C1 configurado/calibrado para producto | No acreditado | Sólo perfil de ensayo explícito; equipo/metodología | Si se promete producto calibrado, requiere protocolo/evidencia propia; no usar smoke como tal |
| C1 como candidato experimental | Cerrado documental | Carga de perfil/huella, núcleo y evidencia heredada | Publicar en tesis únicamente afirmaciones respaldadas de ese alcance |
| Privacidad: inventario, fronteras y conservación/eliminación | Cerrado contrato documental | Auditoría del código y fuentes oficiales; equipo | Cotejar material de Juanma cuando esté disponible; no certificar cumplimiento operativo |
| Derechos, autorización familiar, TLS/cifrado, purga/backup reales | Diferidos con integración | No implementados/acreditados por este bloque; Juanma/equipo | Prueba y política del sistema real, no simple cita de ley |
| Catálogo/condiciones/adaptaciones | Diferido por usuario; sin dictamen | Cecilia dijo que revisaría, no devolvió dictamen | Registrar versión/alcance y aplicar cambios tras devolución |
| RF-10/CU-04 y consistencia del documento vigente | Trabajo editorial posterior | E50 es antecedente; versión consolidada no aportada nueva | Cotejar requisitos, nombres y funciones con versión vigente; no declararlo actualizado sin leerla |
| Ranking aprendido, HU v2/v3 y prototipo 1.400 | Fuera de este bloque/candidato | Decisiones y contratos previos | No activar ni convertir sus pendientes históricos en nuevas tareas obligatorias |

No se encontró una quinta tarea técnica independiente resoluble que debiera
ampliar este bloque. Sí aparece un requisito transversal: al redactar hay que
cotejar el documento vigente y su cumplimiento académico, incluido el papel
real de la IA. Eso no se acredita solamente por tests o por un score aislado.
No se recuperaron todas las conversaciones del proyecto; la recuperación es
acotada y se contrastó con los cierres posteriores para no revivir fases cerradas.

## Pruebas de este código

- Linux/Python 3.12.14: **406 aprobados, 192 subtests, una advertencia**, 15,72 s.
  La suite incluye tests/ y nueve casos del lector de ofertas de raíz que no
  estaban en la orden anterior. Comparación: 385 + doce nuevos + nueve del
  lector = 406; no son veintiún tests nuevos de implementación.
- Focalizadas finales de ofertas/historial/servicio/lector/elecciones:
  **27 aprobadas y cuatro subtests**.
- Locale C, PYTHONUTF8=0, PYTHONCOERCECLOCALE=0, `-X utf8=0`, ofertas nuevas
  y comprobación UTF-8 de catálogo: **13 aprobadas**, una advertencia.
- La advertencia heredada Starlette/httpx no fue fallo; no cambiaron dependencias.
- **Windows nuevo no ejecutado aquí.** El 384 PASS/uno omitido/190 subtests del
  usuario pertenece a `1fd977c`, no a esta modificación infantil.

El test nuevo de reemplazo fallido no se contó como contraejemplo de la base:
su primer fallo era ausencia del hook de implementación. Los seis defectos
iniciales sí se reprodujeron; el bypass adicional se reprodujo contra el primer
checkpoint corregido y luego pasó. No se publica una cuenta inflada de defectos.
El bypass de tipado True==1 también se reprodujo contra su checkpoint antes
de corregir; se conserva el original y se rechaza el falso replay.

Se restaura sólo data/intervention_history.jsonl generado por tests del nuevo
worktree. Nuevos eventos ficticios temporales no se incorporan al commit.
No se tocan históricos del usuario ni se borran locks operativos de otros repos.

## Evidencia y material faltante

Reportes por bloque: [ofertas](OFFERS_2026-10-14.md), [PMUM](PMUM_2026-10-14.md),
[C1](C1_2026-10-14.md), [privacidad](PRIVACY_2026-10-14.md).
La evidencia externa del ensayo contiene XMLs, identificación del perfil y
resumen de procedencia. No contiene HU, microdatos, identidades reales o tokens.

Para terminar los dos bloqueos no hace falta enviar toda la computadora:
originales hu_pmum_sf_experimental_v1.joblib/json (o ZIP original), registro
disponible del entrenamiento y documento/pasaje que apruebe la política infantil.
Si no existe esa decisión, debe tomarse explícitamente: no recuperar una
propuesta como aprobación. La pregunta weekday requiere su instrumento original.
Las fichas de privacidad de Juanma y versión vigente de la tesis pueden cotejarse
cuando estén disponibles; no se asegura que no existan por no localizarlas aquí.
