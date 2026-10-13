# Cierres y tareas finales del modelo y su integración

13/10/2026. Revisión acumulativa: los backlogs del12/10 son antecedentes, no una
lista vigente sin cotejo. Se contrastaron con e090bd4,109060e, el mensaje de
Juanma (backend aa832892) y las salidas Windows recibidas hoy.

## Componente propio del modelo

| Parte | Estado corroborado | Trabajo restante acotado |
|---|---|---|
| PMUM HU v1 | Fuente/cohorte/contratos y evaluación interna documentados; artefacto original verificado en Windows según evidencia anterior | Documentar el alcance; no reentrenar ni usar cambios del score para mensajes |
| C1 | Núcleo preservado; benchmark simulado ejecutado; persistencia/replay comprobados | Mantener configuración explícita de ensayo y límites; no fabricar perfil clínico |
| Mensajes adultos | Motor/API/historial/revisiones implementados en109060e; Linux366PASS; Windows365PASS1omitido con UTF8; demoPASS | Corrección localizada UTF8 y cierre documental |
| UTF8 | Fallo Windows del test de catálogo reproducido por decodificaciónCP1252; rerunUTF8PASS | Esta rama añade codificación explícita al test afectado y herramientas de demo/evaluación; sin cambio de reglas |
| Redacción de tesis | Propuesta previa del12/10 existe pero no incluye mensajes del13/10 | Nuevo texto separado; contrastar con el documento final vigente antes de integrarlo |

El20,92% PMUM tiene atribución documental al OOF fijo y discrepancia con el
antecedente de Claude. No se inventa una traza ni se usa esa cifra en el nuevo
texto: la discrepancia no exige entrenar otro modelo ni bloquea los mensajes.

## Integración concreta que sí falta para el producto

| Parte | Estado según evidencia disponible | Cierre necesario |
|---|---|---|
| Backend→Historical | Juanma reporta227tests y smoke con60c8764, cola durable, retry/conflicto/serialización | Repetir contra referencia actual; conservar resultados. No se afirma auditoría de su código |
| Android→backend→preparador | F12/adaptador probado con fixtures; Juanma implementa captura y sync | Export real compatible, originales conservados, recepción idempotente y preparador server-side |
| Atribución histórica | Assignment todavía reutiliza Device.id según Juanma | Asignación con período válido o garantía equivalente que impida atribución errónea; no interpretar ID de aparato como asignación histórica |
| Cierre diario/calidad | Pendiente según Juanma | Cuándo congelar evidencia, pendientes/ausencia/ceros y revisión; quality_verified no se deduce de recepción |
| Análisis y Alertas | DTO técnico de mensajes disponible; recibosHistorical guardados por backend | Vista descriptiva y última versión de tarjeta, autorizar perfil, mostrar fechas y recomendaciones, probar el recorrido |
| Actividades | Juanma reporta preferencias/ofertas/selecciones y contador; mapping de consideraciones incompleto | Mapping funcional revisado, unknown conservador, probar consignas y preferencias reales; offer_id no acredita renderizado |
| Operación | Compose privado/reinicio local reportados; AWS actual pendiente | Montar nuevo store de mensajes y configuración, reinicio/replay en entorno real; no se afirma despliegue ya ejecutado |

No se reabre la persistencia y las pruebas ya cerradas del modelo. El progreso
del backend hace obsoletas algunas etiquetas antiguas de “no implementado”,
pero el reporte de Juanma no cierra atribución, export real o cierre diario.

## Evidencia externa y tareas que no se agregan al cierre

La revisión profesional del catálogo/consejos y la comprensión de mensajes deben
registrarse cuando existan. No se afirma que hayan sido obtenidas. La validación
argentina o con familias y eficacia no se producen con tests sintéticos.

HU v2 sin sexo, nuevo estimador longitudinal, nuevas variables sintéticas,
aprendizaje avanzado de preferencias, agregadosv3 y una política adicional de
meses no forman parte de este cierre. El modelo sintético de11 variables se
documenta como antecedente, sin intentar validarlo retrospectivamente como HU.

## Entrega única que se prepara para Juanma

Contrato/versiones + estado técnico + texto actual de tesis + lista breve de
dependencias de integración. La actualización editorial no requiere esperar
un resultado de eficacia con familias: requiere describir correctamente lo
implementado y distinguirlo del recorrido aún no comprobado.

La propuesta de tesis del12/10 cotejó páginas seleccionadas de un E50 PDF de147
páginas. No hay una nueva versión final aportada en esta conversación: esta
revisión no afirma cotejarla completa ni autorizar reemplazos de capítulos sin
leerlos. El Word de negocio/branding es una tarea separada.
