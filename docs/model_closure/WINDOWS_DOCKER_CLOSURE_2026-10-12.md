# Cierre de evidencia Windows/Docker y estado de entrega — 12/10/2026

## Estado vigente

Versión técnica publicada: `pmum-c1-closure-reviewed-candidate`, commit `83fc635e4fadca9a0ecc17e0f23c637ea6a7a398`, árbol `c842fd148a32f286d6de1521dfc3bfde05a0e5c4`, padre `60c8764a2e2840503a598bf0c6605f1e2e1a6baf`.

Matías ejecutó el aplicador y validador en Windows/Python 3.10.0, aportó consola y `validation_summary.json`, creó el commit y publicó la rama. La ejecución concluyó `PASS`, con `pending_evidence: []`, carga HU original confirmada y Docker ejecutado. No hubo merge o despliegue. Este documento actualiza el estado de entrega; no modifica código, modelo, parámetros, datos o política del producto.

## Procedencia de la evidencia

- [Resumen original recibido](evidence/windows_2026-10-12/validation_summary.json): conservado byte a byte, SHA-256 `7af90c0963f0d35c3847a23afff8318bf0c9a19a51d2dd9bb19a8a31ab9a94c1`. No generado ni reemplazado por el agente.
- [Extracto de consola](evidence/windows_2026-10-12/console_excerpt.txt): selección documental del mensaje aportado por Matías, no log íntegro ni ejecución local del agente.
- Directorio de evidencia externo: `C:\Users\matum\Documents\modera_pmum_c1_final_20261012-173042-acabed26`. Los logs, reportes individuales, originales HU y snapshots completos permanecen allí; no se inspeccionaron todos desde este cierre.
- Inicio/fin del resumen: `2026-10-12T20:30:43.086209+00:00` / `2026-10-12T20:37:51.774275+00:00`. La consola indica 332 casos en 53.593 s y 15 de raíz en 0.301 s.
- `tested_source_manifest_sha256`: `1ca030eafd6c350692ab8f53b82a6fd258bc77c4171bbdfad2cfeb7d8cafd794`. Esta huella identifica el inventario del runner y no es la huella del árbol Git; su contenido completo no fue aportado aquí.

La prueba se realizó antes del commit, por eso `tested_commit` y `candidate_base` muestran `60c8764`, no `83fc635`. El resumen registra la rama nueva y el inventario de archivos versionados/no versionados. Después Matías creó y publicó el commit de 25 archivos. El árbol público de `83fc635` se cotejó con el checkpoint auditado local: idéntico. La cadena utiliza consola, resumen y cotejo de árbol; no se presenta como una comprobación adicional independiente del manifiesto del runner, que no se recibió.

## Qué cierra el PASS

| Recorrido | Evidencia recibida | Alcance |
|---|---|---|
| Aplicación | Consola: 25 archivos verificados, referencias y worktree previo conservados | Aplicación sobre la base y rama previstas |
| Entorno y suites | Python 3.10.0; pip_check=PASS; 332 casos, 331 aprobados/uno omitido; 15 raíz; seis scripts=PASS | Los scripts y las repeticiones no se suman a los casos unitarios |
| HTTP Windows histórico | seed, restart/replay y auditoría snapshot=PASS | Serie y perfil de ensayo |
| HU original | original_pmum_artifact_loaded=true; pmum_original_artifact=PASS | El verificador exige hash/pipeline/grilla/referencia; resumen de etapa, sin nueva inspección del binario desde Linux |
| Coexistencia Windows | windows_pmum_c1_http y windows_c1_replay_with_pmum=PASS | PMUM original junto con histórico ficticio |
| Docker histórico | build, seed, restart/replay, identity, healthcheck, image_identity y snapshot_audit=PASS | Construcción/operación del contenedor de prueba; no suite completa ejecutada dentro de Docker |
| Docker PMUM/C1 | docker_pmum_c1_http y docker_c1_replay_with_pmum=PASS; docker_history_bytes_unchanged_with_pmum=true | Convivencia y conservación del histórico en el recorrido |

El código contiene `test_lost_writer_lease_path_marks_unavailable`, exclusivo de POSIX. Es consistente con la omisión Windows; el resumen y la consola recibida no nombran el caso omitido, por lo que no se afirma identificación definitiva. Starlette/httpx emitió una advertencia; no hizo fallar la suite y no se cambiaron dependencias en este cierre.

`fixture_only=false` significa que se cargó un original PMUM. **No significa histórico real:** `historical_fixture_only=true` y `configuration_calibrated=false`. `pending_evidence=[]` se limita a las etapas del runner; no enumera ni resuelve todos los pendientes metodológicos o de integración.

## Estado único de entrega para el 15

| Frente | Clasificación actual | Criterio restante |
|---|---|---|
| Guardas y contratos PMUM/C1 | Implementados y probados; candidato publicado | Conservar evidencia; no repetir suites por edición documental |
| HU original bajo nuevas guardas | Verificador y HTTP Windows/Docker PASS | No sustituye trazabilidad del entrenamiento final |
| Evaluación OOF PMUM y F12-C2 | Reproducidas en los bloques previos, con límites documentados | Mantener separación fijo/anidado y cruce/evento; no nueva evaluación científica aquí |
| Entrenamiento HU final | Evidencia pendiente | Código/entorno/log del ajuste final y enlace al artefacto; no reconstruir o reemplazar modelo para aparentar cierre |
| Weekday, NoChildren, hogar/informante | Aclaraciones pendientes | Fuente/diccionario/recodificación; no completar por analogía |
| Perfil C1 de producto y generalización | Evidencia y decisión pendientes | Objetivo, población, calidad/madurez, parámetros y protocolo de evaluación |
| Backend→histórico | Pruebas informadas por Juanma | Aportar código/logs para auditoría independiente; no trasladar PASS del runner al backend |
| Android/F12→preparador→backend | Integración física no acreditada | Export compatible, vinculación efectiva, originales durables, cierre diario, paridad física |
| Evidencia tardía/correcciones | Política propuesta, no API implementada | Versionado/conciliación explícitos; no sobrescribir recibos ni eludir conflictos |
| UI Análisis y Alertas | Contrato/política pendientes de integración y decisión | Reusar interpretación interna; separar evento técnico, candidata y publicación; no activar por CHANGE automáticamente |
| PMUM en producto | internal_research_only | No mostrar como diagnóstico/riesgo ni usar para decisiones de alertas/actividades |
| Texto final de tesis | Propuesta revisable, E50 sólo antecedente | Obtener versión vigente e integrar bajo revisión académica/profesional; Cecilia pendiente |

El mensaje de Juanma informa persistencia previa al HTTP, procesamiento, idempotencia, caída/retry y conflictos. Se incorpora como antecedente comunicado; no acredita por sí solo recepción F12 real, identidad/autorización completas, cierre diario, medición física, operación AWS o producción.

## Uso de documentos anteriores

Los bloques 1/2A/2B conservan su alcance y pendientes de su fecha. No se reescriben como si hubieran cargado el original o ejecutado Windows. Las guías de aplicadores históricos describen una primera aplicación; **no repetir el aplicador PMUM/C1** sobre `C:\tesis_modelo_pmum_c1_final`, que ya existe y fue publicado.

La actualización documental va en rama nueva `pmum-c1-evidence-docs-candidate` sobre `83fc635`, preservando las seis ramas de la secuencia entregada. No cambia las respuestas a Juanma en un contrato ya aprobado: ubicación servidor, clave de ingestión y capa comunicable son propuestas por acordar/implementar. No incorpora v3, perfiles nuevos, alertas, catálogo, teléfono, merge o AWS.

Referencias: [cierre técnico/metodológico](PMUM_C1_CLOSURE_2026-10-12.md), [matriz de afirmaciones](METHOD_CLAIMS_MATRIX_2026-10-12.md), [texto propuesto](THESIS_MODEL_TEXT_PROPOSAL_2026-10-12.md), [contrato](PMUM_C1_CONTRACT_2026-10-12.md), [fuentes/reproducción](SOURCES_AND_REPRODUCTION_2026-10-12.md).
