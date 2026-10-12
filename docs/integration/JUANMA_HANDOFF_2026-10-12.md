# Mensaje para Juanma — borrador, no enviado

Juanma, te comparto una ampliación de la entrega anterior. Ya quedó publicado el candidato del histórico y estoy dejando también una propuesta de conexión F12–backend y del formulario de condiciones para que podamos revisar esos contratos juntos.

**Ramas y documentación**

La entrega anterior sigue intacta en `analytics-api-candidate`, commit `6b0c55d`. El histórico está en `analytics-historical-candidate`, commit `26654b6`, y pasó la validación técnica completa en Windows y Docker.

La ampliacion candidata de F12 y formulario esta preparada para entrega en `analytics-integration-handoff-candidate` y tambien paso la validacion completa en Windows y Docker.

Rama de entrega, una vez confirmado el push:
https://github.com/matumolise/modera-modelo/tree/analytics-integration-handoff-candidate

Guia principal:
https://github.com/matumolise/modera-modelo/blob/analytics-integration-handoff-candidate/docs/integration/BACKEND_F12_C1_CONTRACT_2026-10-12.md

Matriz de las 18 actividades:
https://github.com/matumolise/modera-modelo/blob/analytics-integration-handoff-candidate/docs/integration/CONDITIONS_MAPPING_2026-10-12.md

Usa la rama directamente, sin volver a aplicar parches. No hice merge en phase14-integration.

**Qué hace ahora el histórico**

`POST /v1/historical/evaluate` recibe una representación canónica `daily_use_duration_minutes_v2` ya construida. Con un perfil C1 explícito procesa el día y guarda representación, resultado original y estado. Si se pierde la respuesta y se reintenta con la misma representación, recupera el mismo resultado, incluidos IDs y fechas, también después de reiniciar.

Una respuesta HTTP 200 `processed` puede contener una abstención del análisis. Eso es un procesamiento guardado y reconocido; no hay que reintentarlo hasta obtener un cambio. Un conflicto de contenido u orden devuelve 409; no hay que generar un ID nuevo para eludirlo.

El histórico no recibe exports Android, eventos brutos, PMUM ni el agregado v3 directamente. Tampoco transforma un CHANGE en alerta, tarjeta adulta o actividad infantil.

Se habilita con `ANALYTICS_HISTORICAL_ENABLED=true`, `ANALYTICS_HISTORICAL_CONFIG_PATH` y `ANALYTICS_HISTORICAL_REPOSITORY_PATH`. El perfil va en solo lectura y el repositorio en un volumen persistente. Hay un único escritor por repositorio; no escalar réplicas sobre el mismo volumen. La plantilla Compose está incluida y hay que incorporarla a la red del backend; no define por sí sola AWS.

El perfil `smoke-only-not-calibrated` sirve exclusivamente para pruebas. Todavía falta justificar los parámetros de C1 para uso real; no conviene adoptar los números de ese fixture como configuración de las familias.

**Puente F12 y responsabilidades del backend**

Añadí un preparador Python offline que reutiliza los adaptadores existentes y produce la solicitud completa de v2. No envía HTTP ni guarda el histórico. Trabaja con una proyección documentada de los registros y resúmenes del collector, no con cualquier JSON/CSV Android sin adaptación.

La propuesta separa las series por perfil, dispositivo, asignación, zona horaria y versión de medición. El backend conserva esa asociación y autoriza el perfil. Los eventos de pantalla no permiten comprobar quién usó el dispositivo: en un teléfono compartido, los minutos siguen describiendo al aparato.

Calcula días locales cerrados y convierte sus límites a UTC; distingue captura incompleta de cero observado y conserva cobertura no cuantificada. Los reinicios que impiden demostrar continuidad quedan como faltante, sin inventar minutos.

Del lado del backend necesitamos guardar el payload inmutable antes de enviarlo y ordenar los días dentro de cada serie. Ante timeout o 503 se reintenta ese mismo payload; no se vuelve a consultar/reconstruir el día con datos nuevos. Una corrección de evidencia de un día ya procesado queda para revisión explícita.

Para decidir la conexión concreta necesito confirmar qué IDs tenés hoy para perfil, dispositivo y asignación, y dónde podría correr este preparador. Si tu backend no usa Python, podemos acordar un job separado o un adaptador equivalente probado contra los fixtures; no hay que duplicar fórmulas sin verificar paridad.

**Formulario de condiciones y actividades**

Revisé las 18 consignas y las opciones que propusiste. “Ninguna” explícita se puede distinguir de no respondido. Pero movilidad, visual, auditiva y sensibilidad sensorial, por sí solas, todavía no permiten determinar qué actividades son factibles para cada persona: faltan tareas concretas, apoyos o variantes del catálogo. Por ejemplo, una actividad tranquila puede requerir dibujo y una social puede ser un juego con demandas no especificadas.

En esta ampliacion, la propuesta incorpora `POST /v1/activities/eligibility`, con el mismo token. Acepta Ninguna, una opción de movilidad y combinaciones con visual/auditiva/sensorial. Ninguna es exclusiva; no respondido se mantiene desconocido. Cuando falta el mapeo funcional devuelve `eligibility_state: unknown`, sin filtros, y los temas que necesitamos resolver. Después el backend arma el cuerpo del selector existente; si el estado consolidado sigue desconocido, el selector se abstiene.

Eso evita interpretar un campo omitido como “Ninguna”. No significa que ya esté aprobado el filtro por esas etiquetas. Podemos conservarlas como declaración general y cerrar los seguimientos, o simplificar el formulario hacia restricciones prácticas sobre tareas del catálogo ya revisadas. Mi recomendación es esta segunda opción cuando tengamos esa revisión, sin deducir capacidades de una condición ni declarar seguras las actividades restantes.

**Qué comprobamos y qué falta**

La base histórica pasó 236 pruebas de `tests/` y una omisión prevista de POSIX, otras 15 pruebas de la raíz y seis scripts heredados. También pasó HTTP, recuperación tras terminar el proceso, Docker con persistencia y reinicio, usuario 10001 y healthcheck.

La ampliacion paso en Linux 258 casos de tests/, otras 15 pruebas de la raiz y HTTP real con preparacion F12. En Windows paso 257 casos y una omision prevista de POSIX, otras 15 pruebas y seis scripts heredados. Tambien aprobaron HTTP, reinicios, Docker, persistencia y healthcheck. Son datos ficticios y un perfil no calibrado; falta comprobar conjuntamente tu backend, la captura en un telefono fisico y luego AWS.

PMUM conserva su endpoint experimental y el ZIP externo entregado antes; no lo usamos para decidir actividades, frecuencia o alertas. Tampoco incorporé el agregado v3, ofertas automáticas ni la tarjeta adulta.

Con esto podemos revisar primero los IDs/asignaciones, el lugar del preparador y el formulario funcional, mientras avanzás con la conexión al histórico usando el perfil de prueba. La configuración real de C1 y la revisión profesional siguen siendo pendientes del equipo, no decisiones que debas resolver solamente desde la infraestructura.
