# Cierre revisado PMUM/C1: evidencia y pendientes

Estado: candidato técnico interno propuesto para revisión académica y verificación externa de entorno. No es aprobación clínica, calibración de producto o validación externa argentina.

## Feedback acumulativo: reauditoría solicitada

Los resultados de los bloques 2A/2B se comprobaron de nuevo con mayor profundidad. Conteos PMUM confirmados independientemente desde SEM.sav: 810/806/803 y 800 al añadir el filtro del cuidador del SEM original; subgrupo NoChildren=1: 300. Se reprodujeron PMUM OOF y F12-C2 completos: ambos JSON coinciden exactamente con las ejecuciones guardadas. El entrenamiento de evaluación fue en memoria; no se guardó/reemplazó el HU entregado. Se cotejaron pasajes específicos del PDF E50 y se conservaron los límites de fuente/formulario/recodificación ya documentados.

Se precisaron dos aspectos C2: los gaps proceden de DayInStudy trasladado a fechas artificiales, y el cruce experimental no es una emisión de API. Un contraejemplo ficticio produce CHANGE/cruce en el primer registro elegible pero NO_EMIT por estadístico anterior None. Se mantienen el experimento y núcleo originales; sus tasas no se reasignan a eventos productivos.

Los antecedentes escritos no se convierten en aprobaciones. La lectura primaria PMUM confirma su alcance original y la necesidad de validación clínica/cortes; NIST no valida esta referencia robusta adaptativa. No se recuperaron dictámenes nuevos de Cecilia/Santiago ni metadatos/licencia del registro HU actualmente inaccesible.

## Correcciones y estabilidad de contratos

- Guardas PMUM de objetivo/fuente/alcance/tipos, sin certificar textos libres ni sustituir el artefacto.
- Guardas de coherencia de recibos C1 y auditoría offline de referencias, conservando IDs, fechas, estado y replay. No autenticación criptográfica ni corrección automática del historial.
- Edad entera extrema: rango validado antes de float; abstención funcional y servicio disponible, sin ocultar fallos reales de inferencia.
- Aplicador: destino/rama nuevos, hash del parche, cinco referencias, inventario de archivos y preservación del estado del worktree original. Copia los bytes verificados a un parche temporal; no crea commits, merge o push.
- Ensayo con core.autocrlf=true detectó una diferencia CRLF: se corrigió la conversión sólo para crear/aplicar en el destino, sin cambiar configuración del repo original. Regresión incorporada.
- Validador Windows: separa fixtures históricos de eventual HU original; prueba original en HTTP Windows y Docker si disponible. Etapas omitidas/faltantes quedan explícitas como pendientes.

No se modificaron historical/, k/h/min_history, políticas de referencia, v2, selector/catálogo/ofertas/tarjetas ni perfiles anteriores. No hay v3, teléfono físico, negocio/pagos, contacto con Juanma, merge o AWS. Se ignoró api.zip.

## Evidencia exacta

Ver los JSON y logs del paquete. La reauditoría usa Linux/Python 3.12.14 y versiones científicas 1.7.2/2.2.6/1.15.3/1.5.3, con pandas 2.3.3.

El árbol publicado 60c8764 se reconstruyó íntegramente para el ensayo: 204 blobs y árbol e0fefa74092657ee403bd7757a9eaee404576df4, con sus hashes verificados; se reprodujo el objeto commit público. No se reconstruyó toda la historia Git pública. El aplicador se ensayó offline contra esos objetos, con autocrlf=true; la consulta pública de referencias se hizo mediante el conector, no mediante ese fetch Git de ensayo. La ejecución Windows hará su propio fetch.

La copia aplicada pasó 332 casos de tests/, 15 de raíz, siete ensayos de aplicación incluidos en esa suite y seis scripts heredados separados. HTTP nativo con predictor ficticio: coexistencia PMUM/C1, cinco abstenciones incluyendo edades extremas, 401, seed, terminación/reinicio, replay con bytes iguales, auditoría del snapshot y rechazo de corrupción sin reescribirla. No se suman scripts o pruebas focalizadas a la suite. La advertencia Starlette/httpx no fue un fallo.

HU original no cargado en Linux; Windows/Docker no ejecutados aquí. El paquete no contiene microdatos, PDFs originales o binarios reales. Las verificaciones de aplicación prueban archivos/contratos; no convierten el predictor ficticio o el perfil SMOKE_ONLY en validación del producto.

## Clasificación final y responsables

| Parte | Estado | Responsable / criterio de cierre |
|---|---|---|
| Correcciones/guardas/contratos de este candidato | Implementados y probados en Linux | Matías: ejecutar aplicación/validación agrupada en Windows y conservar resumen |
| Fuentes, cohorte, particiones y resultados OOF/C2 | Reproducidos en condiciones declaradas | Equipo: conservar fuentes con hash; no atribuir validez externa |
| Artefacto HU v1 y dependencias originales | Pendiente de evidencia con guardas nuevas | Matías: ambos originales registrados, hash/pipeline/grilla/HTTP Windows/Docker; no reentrenar ante fallo |
| Procedencia exacta del entrenamiento final | Pendiente de evidencia | Equipo: código/entorno/log de ajuste y artefacto; huella/grilla no prueban coeficientes entrenados sobre la cohorte |
| Weekday completo y recodificación NoChildren | Pendiente de evidencia | Equipo/fuente: recuperar cuestionario y recodificación; no completarlos por analogía |
| Independencia de hogar/informante y generalización | No establecidas | Equipo: fuentes/protocolo independiente antes de ampliar uso; IDs únicos no bastan |
| Perfil C1 para producto | Pendiente de evidencia y decisión | Equipo/metodología/profesional: objetivo, población, calidad, madurez, k/h, adaptación/gaps y criterios de comunicación justificados |
| Texto de tesis | Propuesta contrastada parcialmente con E50 | Matías/dirección: versión vigente, bibliografía de datasets y aceptación del alcance; PDF no modificado automáticamente |
| Backend/operación real | Pendiente de evidencia externa | Equipo backend: identidad/asignación, payload durable, cierre/orden/correcciones y autorización; contrato no acredita su implementación |

Para el 15 se recomienda presentar el candidato interno con estas evidencias y restricciones, conservar HU v1 y C1 actuales y agrupar las verificaciones externas. No inventar un perfil calibrado, reemplazar silenciosamente el modelo o declarar aprobadas las comunicaciones/actividades. Un fallo conserva el worktree, originales, volumen y logs para investigación.
