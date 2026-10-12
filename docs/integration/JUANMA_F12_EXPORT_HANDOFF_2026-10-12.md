# Mensaje completo para Juanma — borrador, no enviado

Juanma, te paso el estado de integración y una ampliación para conectar el export diagnóstico Android F12 con el preparador histórico. Separé lo publicado de lo que todavía estamos validando, para que puedas avanzar sin interpretar las pruebas técnicas como aprobación de uso real.

**Código publicado y nuevo candidato**

La última entrega publicada es [f12-export-integration-candidate](https://github.com/matumolise/modera-modelo/tree/f12-export-integration-candidate), commit `94ff3a8`. Incluye export JSON/JSONL, preparador v2 y API histórica persistente. Se conservan intactas `analytics-api-candidate` (`6b0c55d`), `analytics-historical-candidate` (`26654b6`) y `analytics-integration-handoff-candidate` (`61e31ce`). No hice merge en phase14-integration.

Documentos del commit publicado:

- [Contrato backend–F12–C1](https://github.com/matumolise/modera-modelo/blob/94ff3a82ad3581e74cb6f97449adda264972c61b/docs/integration/BACKEND_F12_C1_CONTRACT_2026-10-12.md).
- [Export y preparador](https://github.com/matumolise/modera-modelo/blob/94ff3a82ad3581e74cb6f97449adda264972c61b/docs/integration/F12_EXPORT_ADAPTER_2026-10-12.md).
- [Protocolo de teléfono](https://github.com/matumolise/modera-modelo/blob/94ff3a82ad3581e74cb6f97449adda264972c61b/docs/integration/F12_PHONE_PARITY_PROTOCOL_2026-10-12.md).

Hay además una auditoría nueva preparada para otra rama, `integration-audit-closure-candidate`, todavía sin publicación ni validación Windows/Docker. Corrige guardas de intervalo y coherencia de queries solapadas, refuerza verificación del paquete y añade un preflight offline del plan diario. Sus contratos y backlog están en el paquete de revisión. Los enlaces anteriores apuntan a 94ff3a8, no a esa ampliación. Usá el código publicado directamente sin reaplicar parches anteriores; la ampliación tiene un parche aparte sobre 94 para un worktree nuevo.

**Servicio compartido y red**

El entrypoint es `analytics_api.py`, con un worker. `Dockerfile.analytics` usa Python 3.10-slim, escucha en `0.0.0.0:8765` dentro del contenedor y usa UID/GID 10001. Backend y analytics pueden compartir una red Compose; si el servicio se llama `analytics`, el backend llama a `http://analytics:8765`. `localhost` dentro del backend apunta a ese propio contenedor. No hace falta publicar analytics al exterior para esta comunicación.

Las variables las pasa Compose/el entorno; el servicio no carga automáticamente `.env`. `requirements-analytics.txt` corresponde al servicio; `requirements-integration-tools.txt` al preparador y sus pruebas, incluida tzdata fijada. El preparador es offline y corre fuera del proceso HTTP actual; no hay un nuevo endpoint que reciba exports.

Los POST requieren `Authorization: Bearer <token>` y `Content-Type: application/json`. El token de servicio debe cumplir el contrato —ASCII sin espacios, al menos 16 caracteres— y ser propio del entorno. No usar las credenciales locales de ensayo. Tu backend sigue autenticando al usuario y autorizando el perfil: Android llama al backend, y el backend a analytics.

Para empezar, actividades pueden habilitarse sin PMUM ni histórico. El histórico requiere `ANALYTICS_HISTORICAL_ENABLED=true`, `ANALYTICS_HISTORICAL_CONFIG_PATH` y `ANALYTICS_HISTORICAL_REPOSITORY_PATH`. El perfil se monta en solo lectura y el repositorio en volumen persistente; la plantilla Compose está incluida. Hay un único escritor por repositorio: no escalar réplicas sobre el mismo archivo/volumen. No borrar `.writer.lock` ni `.initialized` para resolver reintentos.

`GET /health/live` comprueba el proceso; `GET /health` informa capacidades/disponibilidad. Funcionan sin token; health puede devolver 503 si una capacidad habilitada no está disponible.

**Conexión F12 y formato comprobado**

Revisé el collector/exportador Kotlin: escribe un par `summary_<run>.json` y `events_<run>.jsonl` por consulta. El resumen tiene nueve claves camelCase y cada evento catorce, incluyendo package/class y metadatos Android. Ese exportador no produce CSV. La UI actual consulta la última hora y no exporta errores; eso no permite dar por validado un día completo.

El commit publicado 94ff3a8 agrega un adaptador para esos pares existentes. Comprueba UUID, conteos de todas las filas, asociación de límites/timestamps, orden y ordinales, nombres/códigos según API y estados de captura. Conserva los originales byte por byte en un paquete con huellas y produce la proyección interna, v2 y el payload HTTP final. No filtra el crudo a solo eventos de pantalla antes de validar sus conteos.

El backend proporciona una cabecera explícita con `request_id`, día local, `computed_at` y los campos de serie `profile_id`, `device_id`, `assignment_id`, `time_zone` y `measurement_version`. Son campos del contrato de preparación propuesto, no campos encontrados dentro del export. Los IDs deben estar aislados por cuenta/tenant y pueden ser opacos. Necesitamos confirmar cómo se corresponden con tus IDs actuales y dónde conservar esa asociación.

El UUID identifica una consulta; fabricante/modelo y paquetes no identifican al niño ni verifican el aparato. Una pantalla interactiva tampoco atribuye uso exclusivo a un perfil. En un teléfono compartido medimos el dispositivo, hasta contar con evidencia de atribución. La zona IANA se declara desde el backend; no se toma del PC ni se inventa a partir de epoch ms.

El preparador trabaja con días cerrados, medianoche local a la siguiente, convierte ambos límites a UTC y contempla días de 23/25 horas. Exige un estado de pantalla previo y consultas exitosas continuas desde ese estado hasta el cierre. Cuando falta evidencia mantiene `MISSING`, nunca cero: consultas vacías sin estado previo, permiso ausente, gaps o reinicios del tramo necesario no se completan por inferencia. `OBSERVED_ZERO` requiere evidencia de estado/cobertura operacional. La cobertura cuantificada sigue `null`; éxito de consulta no prueba exhaustividad física del sistema.

Se conservan consultas solapadas y eventos repetidos sin sumar dos veces los mismos tramos; estados opuestos al mismo timestamp se rechazan. Los metadatos incoherentes también se rechazan, sin pretender que dos teléfonos iguales se distingan por su modelo.

El fingerprint nuevo incluye las huellas de los exports completos. El CLI conserva `request.json` en el paquete preparado; el backend deberá fijarlo de manera durable antes de enviarlo y reusarlo en reintentos. Reconsultar Android o reescribir los archivos puede cambiar la procedencia y generar un 409 para un record ya procesado. El adaptador no reemplaza recibos de la vía antigua: si ya tenés series guardadas, acordamos una transición explícita.

Si no hay export, el backend puede declararlo explícitamente con `--no-export`: produce MISSING sin inventar una consulta. No se usa automáticamente ante un archivo perdido o corrupto. Tenemos que distinguir ausencia de captura de una transferencia todavía pendiente antes de fijar el payload diario; no definí un plazo arbitrario. Una nueva captura después de guardar MISSING sería una corrección de evidencia, no un reintento del mismo payload.

En 94ff3a8 se corrigió la aceptación de mensajes de error vacíos que Kotlin puede exportar y preparé una defensa ante truncamiento silencioso del iterador del collector, usando su error de consulta existente. Esa corrección Kotlin y el harness añadido siguen pendientes de compilación/ensayo Android; pasar los tests Python no los compila.

**API histórica y C1**

`POST /v1/historical/evaluate` recibe únicamente `daily_use_duration_minutes_v2` ya preparada. No recibe exports, cabecera de serie, raw, PMUM ni v3. Procesa el día con un perfil C1 explícito y guarda representación, estado y recibo original de manera coordinada.

Si se pierde la respuesta, el mismo payload recupera el mismo resultado, incluidos IDs y fechas, después de reiniciar. HTTP 200 `processed` reconoce una entrada persistida, aunque el análisis diga `ABSTAIN`: no repetir hasta conseguir CHANGE. Conflictos de contenido, procedencia u orden devuelven 409; no crear IDs nuevos para eludirlos. El backend conserva una cola durable/payload y ordena por serie; esa persistencia de tu backend todavía debemos probarla juntos.

SMOKE_ONLY es un perfil ficticio para comprobar conexión y recuperación, no calibración ni configuración de producto. No cambié parámetros C1 ni su política de referencia, y no incorporé automáticamente v3. Un CHANGE técnico no activa alertas, actividades, ofertas ni tarjetas.

**Formulario, actividades y PMUM**

`POST /v1/activities/eligibility` distingue “Ninguna” explícita de desconocido. Acepta una opción de movilidad —brazos/manos, piernas o ambas— y combinaciones con visual, auditiva y sensorial. Ninguna es exclusiva. Cuando las etiquetas no permiten resolver demandas concretas del catálogo devuelve `eligibility_state: unknown`, sin filtros inventados, y los temas funcionales que faltan.

Después el backend arma el cuerpo de `POST /v1/activities/select`: hasta tres actividades, contextos voluntary/general/bedtime, intereses, IDs recientes y filtros operativos. Si el estado consolidado es desconocido, se abstiene. `eligibility: {}` con estado conocido declara ausencia de exclusiones operativas; no reemplaza datos faltantes.

Las 18 actividades siguen siendo provisionales. Falta revisión funcional/profesional y, cuando corresponda, consignas adaptadas; no atribuimos seguridad clínica a las etiquetas. El selector no crea `offer_id`, no guarda historial de ofertas ni registra entrega/elección/realización. Este bloque no implementa esos flujos.

PMUM conserva `/experimental/pmum-estimate` y los archivos externos del ZIP preparado anteriormente. Necesita habilitarse, montajes de modelo/manifiesto en solo lectura y SHA configurada; sigue `experimental: true` / `internal_research_only`. No se volvió a cargar el artefacto real en este bloque ni se usa para actividades, frecuencia o alertas. No está aprobado para mostrarlo a familias.

**Qué se probó y qué queda**

94ff3a8 pasó Windows/Python3.10 y Docker con 288 casos de tests/ —287 aprobados y una omisión esperada exclusiva de POSIX—, 15 pruebas de raíz y seis scripts heredados. También pasaron HTTP Windows, terminación/reinicio/replay, Docker con volumen/restart/replay, identidad y healthcheck. El modelo HU real se verificó en la entrega API anterior, no en el recorrido del export/histórico. Son fixtures y perfil no calibrado; no es validación física ni de tu backend.

La auditoría nueva encontró casos que esa suite no cubría: duración imposible mayor que el intervalo; computed_at anterior al cierre; relatos incompatibles de dos consultas exitosas en el mismo tramo; y verificación incompleta del paquete intermedio. El candidato nuevo pasó 305 casos en Linux, 15 pruebas de raíz, seis scripts heredados y HTTP con recuperación de 11 recibos tras reinicio, usando datos ficticios y PMUM deshabilitado. Las guardas nuevas tienen regresiones; Windows/Docker del candidato nuevo tambi?n pasaron: 305 casos (304 aprobados y una omisi?n), 15 pruebas de ra?z, seis scripts heredados y recorridos HTTP con persistencia/reinicio, con datos ficticios y perfil no calibrado. No cambiaron parámetros, referencia C1 ni formato de recibos. Los resultados anteriores no se trasladan a una versión distinta por herencia.

También preparé un preflight del plan backend: EXPORT_PENDING espera sin crear MISSING; EXPORT_READY y ABSENCE_CONFIRMED validan el payload y pueden quedar READY_TO_FREEZE, mientras un pendiente anterior declarado bloquea los siguientes. Es un contrato nuevo propuesto, no campos encontrados en tu backend ni otro endpoint analytics. No persiste una cola ni decide un plazo de cierre. Necesitamos acordar quién fija la evidencia diaria y cómo se conserva el payload/reserva de envío antes de HTTP.

Evidencia nueva después de un recibo no es retry: mantendríamos el original y abriríamos una revisión pendiente. Un replay técnico versionado en repositorio aislado sería una opción a diseñar, no reparación automática. No generaríamos una asignación o ID ficticio para eludir 409. La API actual no ofrece revisiones ni corrección de tarjetas.

La matriz funcional nueva reexamina las 18 consignas, combinaciones y acceso a instrucciones. Contrasta título y descripción completos: Escuchá una historia explicita escucha, pero no acredita apoyos o una variante adaptada disponible. La lectura no fija formato visual ni el dibujo miembros o apoyos; la modalidad necesita confirmación. Tampoco Ninguna demuestra persona/materiales disponibles o accesibilidad global. Proponemos preguntar por tareas que convenga evitar/adaptar y revisar variantes, antes de mapear condiciones a filtros. El catálogo continúa provisional y sin dictamen profesional recibido.

Falta build/harness/teléfono, integración/autorización/cola de tu backend, decisiones reales C1 y catálogo, y después el entorno AWS. No implementé ofertas diurnas/coordinador global ni tarjetas adultas: las propuestas de topes/esperas y 7 contra 7 no se adoptaron como contratos aprobados. El motor legado sí tiene voluntaria/descanso y registros de oferta/respuesta, pero eso no acredita entrega visual ni la misma durabilidad del repositorio C1.

Para destrabar nuestra conexión, propongo cerrar primero IDs/asignación/namespace y calendario de días esperados; un job Python reutilizando el preparador; almacenamiento durable y envío serial por serie; quién fija evidencia y distingue copia pendiente de export ausente; y cómo registrar una corrección sin sobreescribir recibos. Podemos probar esos contratos con la serie ficticia mientras avanzamos con la validación física. La revisión profesional, aprobación de producto y configuración C1 siguen como decisiones del equipo, no responsabilidades tuyas solo por infraestructura.
