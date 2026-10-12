# Bloque 1: auditoría de correcciones y contratos PMUM/C1

Fecha: 12/10/2026. Estado: implementado y probado en Linux, limitado a los contratos y correcciones examinados. No constituye el cierre metodológico completo ni el paquete final.

## Procedencia y alcance

La base pública es integration-audit-closure-candidate/60c8764a2e2840503a598bf0c6605f1e2e1a6baf. El bloque recuperó una copia parcial verificada de 171 blobs. Su raíz Git local es 7e3b3093819fd30214b34c38b2d6f6cd0f330330, un snapshot local; no es el commit público ni un clon con su historia completa.

Se preservó la carpeta de pmum-c1-model-closure-candidate de la ejecución anterior. La copia de trabajo nueva es pmum-c1-contract-audit-candidate. Los cambios heredados PMUM/C1 se conservan como trabajo recuperado; no se atribuyen a esta ejecución. No se publicaron ramas, hicieron merges o desplegaron servicios.

## Feedback acumulativo

- El cargador CachedPmum comprueba el valor 2.6959 en su constructor. verify_pmum_artifact_v1 lo utiliza, por lo que también hace esa comprobación indirecta. La afirmación previa del agente que negaba esa comprobación offline era incorrecta; se rectificó. No se introdujo una comparación duplicada por ese supuesto.
- regularization/evaluation son textos históricos: la validación de presencia/tamaño no acredita su verdad. La prueba aislada de textos fabricados demuestra ese límite; no prueba adulteración del manifiesto original. Se precisó la documentación y se conservó el original. No se adoptó una regla que intente deducir aprobación clínica de un texto libre.
- Los borradores afirmaban que existían un aplicador y un paquete final. Sólo existe el validador Windows modificado; el nuevo aplicador no se encontró. Se cambiaron esas afirmaciones por estado pendiente. Los resultados anteriores Linux y Windows de la base se distinguen de los de esta copia nueva.

## Error demostrado y corrección

El contrato admite edad finita 6–12 y devuelve abstención funcional para entradas fuera del dominio. JSON puede representar un entero 10**400 con un cuerpo menor al límite. row_for_model intentaba math.isfinite antes de comprobar rango; la conversión de ese entero a float causaba OverflowError.

Contraejemplo antes de corregir: edad 10**400 y -10**400 → HTTP 500/internal_error, con el servicio todavía READY. Después: HTTP 200 y {status: unavailable, reason: invalid_feature_value}, sin invocar predictor y conservando READY y una estimación válida posterior.

La corrección comprueba el rango antes de math.isfinite. Se conserva dominio, codificación, rounding, clipping, respuestas válidas y precedencia de abstenciones. No se cambia el ajuste de Ridge, el artefacto o su manifiesto. No se captura una excepción de inferencia como si fuera respuesta parental faltante.

Se añadieron dos regresiones: adapter sin invocar predictor para ambos signos; HTTP que comprueba abstención, readiness y estimación posterior. Los restantes contratos se verifican con las regresiones recuperadas y la suite existente.

## C1 y límites de la auditoría

Se revisaron validación de binding/configuración, conteos por serie, ecuaciones, abstenciones, estado previo/siguiente, emisión y replay. Las guardas recuperadas no escriben objetos recalculados en lugar del recibo. La auditoría offline reconstruye la referencia desde la historia; readiness sólo coteja la coherencia contra la referencia guardada. Una falsificación coherente de la referencia puede pasar ese control online y ser detectada offline; esa distinción ya está probada y documentada. No se convirtió readiness en una reconstrucción completa ni en autenticación del repositorio.

No se demostró en este bloque un defecto que requiera cambiar historical/, C1 k/threshold/min_history, su referencia o v2. Las pruebas no convierten esas decisiones en configuración aprobada para familias. El núcleo, los parámetros y los históricos se conservan.

## Verificación de este bloque

- Linux/Python 3.12.14, entorno científico existente.
- tests.test_model_closure: 20 casos, PASS; incluidos en la suite total.
- tests/: 325 casos, PASS en 6.024 s.
- Raíz: 15 casos, PASS en 0.008 s.
- git diff --check: PASS.
- Advertencia Starlette/httpx presente, sin fallo.

Fixtures artificiales; el binario original HU v1 no se cargó. HTTP de este bloque se probó mediante TestClient/ASGI, no se declara un nuevo recorrido TCP/Windows/Docker. Los registros de HTTP nativo/reinicio del bloque recuperado son antecedentes separados. No se entrenó un modelo nuevo ni se ajustaron parámetros científicos.

## Clasificación y siguiente cierre

| Parte | Estado | Criterio restante |
|---|---|---|
| Error de validación de edad PMUM | Implementado y probado | Comprobarlo dentro del recorrido Windows del candidato final |
| Guardas de manifiesto/recibos recuperadas | Reauditadas y probadas con fixtures | Cotejo del original HU y operación del nuevo candidato en Windows/Docker |
| Atribución de la referencia 2.6959 | Afirmación previa rectificada; comprobación indirecta confirmada por código y prueba de arranque existente | Nueva carga del binario original, sin reemplazo |
| Contratos y afirmaciones de aplicador/paquete | Documentación precisada | Preparar y verificar componentes de entrega final |
| Fuente/población/OOF/C2 y propuesta de tesis | Pendientes del próximo bloque de auditoría | Contrastarlas con los archivos y documentos efectivamente disponibles |
| Configuración C1 de producto y decisiones clínicas | Pendiente de evidencia/decisión externa | Protocolo, población, parámetros justificados y revisión correspondiente |

El bloque no amplía selector/catálogo/ofertas/tarjetas. La devolución de Cecilia sigue pendiente. No contacta a Juanma, no prioriza teléfono físico, no incorpora api.zip, negocio/pagos, v3, merge ni AWS.
