# Mensaje completo para Juanma — borrador, no enviado

Juanma, te paso el estado de integración y una ampliación para conectar el export diagnóstico Android F12 con el preparador histórico. Separé lo publicado de lo que todavía estamos validando, para que puedas avanzar sin interpretar las pruebas técnicas como aprobación de uso real.

**Código publicado y nuevo candidato**

La última entrega publicada es [analytics-integration-handoff-candidate](https://github.com/matumolise/modera-modelo/tree/analytics-integration-handoff-candidate), commit `61e31ce`. Incluye API compartida, histórico persistente, preparador F12 y resolución candidata del formulario. Las entregas anteriores siguen intactas: `analytics-api-candidate` en `6b0c55d` y `analytics-historical-candidate` en `26654b6`. No hice merge en `phase14-integration`.

Guías publicadas:

- [Contrato backend–F12–C1](https://github.com/matumolise/modera-modelo/blob/61e31ceaaa7a81c775d143415a00a3fd9bf55721/docs/integration/BACKEND_F12_C1_CONTRACT_2026-10-12.md).
- [API histórica y configuración](https://github.com/matumolise/modera-modelo/blob/61e31ceaaa7a81c775d143415a00a3fd9bf55721/docs/integration/HISTORICAL_API_CANDIDATE_2026-10-11.md).
- [Matriz de condiciones y catálogo provisional](https://github.com/matumolise/modera-modelo/blob/61e31ceaaa7a81c775d143415a00a3fd9bf55721/docs/integration/CONDITIONS_MAPPING_2026-10-12.md).

El bloque nuevo del export está preparado como parche sobre `61e31ce` para una rama separada `f12-export-integration-candidate`; todavía no está publicado ni probado en Windows/Docker o teléfono. Sus documentos son `F12_EXPORT_ADAPTER_2026-10-12.md`, `F12_PHONE_PARITY_PROTOCOL_2026-10-12.md` y `F12_EXPORT_REVIEW_2026-10-12.md`, incluidos en el paquete de revisión. Hasta confirmar una nueva publicación, los enlaces anteriores apuntan a la entrega existente, no a este parche. Para la rama publicada usá el código directamente, sin volver a aplicar los parches anteriores.

**Servicio compartido y red**

El entrypoint es `analytics_api.py`, con un worker. `Dockerfile.analytics` usa Python 3.10-slim, escucha en `0.0.0.0:8765` dentro del contenedor y usa UID/GID 10001. Backend y analytics pueden compartir una red Compose; si el servicio se llama `analytics`, el backend llama a `http://analytics:8765`. `localhost` dentro del backend apunta a ese propio contenedor. No hace falta publicar analytics al exterior para esta comunicación.

Las variables las pasa Compose/el entorno; el servicio no carga automáticamente `.env`. `requirements-analytics.txt` corresponde al servicio; `requirements-integration-tools.txt` al preparador y sus pruebas, incluida tzdata fijada. El preparador es offline y corre fuera del proceso HTTP actual; no hay un nuevo endpoint que reciba exports.

Los POST requieren `Authorization: Bearer <token>` y `Content-Type: application/json`. El token de servicio debe cumplir el contrato —ASCII sin espacios, al menos 16 caracteres— y ser propio del entorno. No usar las credenciales locales de ensayo. Tu backend sigue autenticando al usuario y autorizando el perfil: Android llama al backend, y el backend a analytics.

Para empezar, actividades pueden habilitarse sin PMUM ni histórico. El histórico requiere `ANALYTICS_HISTORICAL_ENABLED=true`, `ANALYTICS_HISTORICAL_CONFIG_PATH` y `ANALYTICS_HISTORICAL_REPOSITORY_PATH`. El perfil se monta en solo lectura y el repositorio en volumen persistente; la plantilla Compose está incluida. Hay un único escritor por repositorio: no escalar réplicas sobre el mismo archivo/volumen. No borrar `.writer.lock` ni `.initialized` para resolver reintentos.

`GET /health/live` comprueba el proceso; `GET /health` informa capacidades/disponibilidad. Funcionan sin token; health puede devolver 503 si una capacidad habilitada no está disponible.

**Conexión F12 y formato comprobado**

Revisé el collector/exportador Kotlin: escribe un par `summary_<run>.json` y `events_<run>.jsonl` por consulta. El resumen tiene nueve claves camelCase y cada evento catorce, incluyendo package/class y metadatos Android. Ese exportador no produce CSV. La UI actual consulta la última hora y no exporta errores; eso no permite dar por validado un día completo.

El parche nuevo agrega un adaptador para esos pares existentes. Comprueba UUID, conteos de todas las filas, asociación de límites/timestamps, orden y ordinales, nombres/códigos según API y estados de captura. Conserva los originales byte por byte en un paquete con huellas y produce la proyección interna, v2 y el payload HTTP final. No filtra el crudo a solo eventos de pantalla antes de validar sus conteos.

El backend proporciona una cabecera explícita con `request_id`, día local, `computed_at` y los campos de serie `profile_id`, `device_id`, `assignment_id`, `time_zone` y `measurement_version`. Son campos del contrato de preparación propuesto, no campos encontrados dentro del export. Los IDs deben estar aislados por cuenta/tenant y pueden ser opacos. Necesitamos confirmar cómo se corresponden con tus IDs actuales y dónde conservar esa asociación.

El UUID identifica una consulta; fabricante/modelo y paquetes no identifican al niño ni verifican el aparato. Una pantalla interactiva tampoco atribuye uso exclusivo a un perfil. En un teléfono compartido medimos el dispositivo, hasta contar con evidencia de atribución. La zona IANA se declara desde el backend; no se toma del PC ni se inventa a partir de epoch ms.

El preparador trabaja con días cerrados, medianoche local a la siguiente, convierte ambos límites a UTC y contempla días de 23/25 horas. Exige un estado de pantalla previo y consultas exitosas continuas desde ese estado hasta el cierre. Cuando falta evidencia mantiene `MISSING`, nunca cero: consultas vacías sin estado previo, permiso ausente, gaps o reinicios del tramo necesario no se completan por inferencia. `OBSERVED_ZERO` requiere evidencia de estado/cobertura operacional. La cobertura cuantificada sigue `null`; éxito de consulta no prueba exhaustividad física del sistema.

Se conservan consultas solapadas y eventos repetidos sin sumar dos veces los mismos tramos; estados opuestos al mismo timestamp se rechazan. Los metadatos incoherentes también se rechazan, sin pretender que dos teléfonos iguales se distingan por su modelo.

El fingerprint nuevo incluye las huellas de los exports completos. Guardamos `request.json` antes de enviarlo y lo reusamos en reintentos. Reconsultar Android o reescribir los archivos puede cambiar la procedencia y generar un 409 para un record ya procesado. El adaptador no reemplaza recibos de la vía antigua: si ya tenés series guardadas, acordamos una transición explícita.

Si no hay export, el backend puede declararlo explícitamente con `--no-export`: produce MISSING sin inventar una consulta. No se usa automáticamente ante un archivo perdido o corrupto. Tenemos que distinguir ausencia de captura de una transferencia todavía pendiente antes de fijar el payload diario; no definí un plazo arbitrario. Una nueva captura después de guardar MISSING sería una corrección de evidencia, no un reintento del mismo payload.

También corregí la aceptación de mensajes de error vacíos que Kotlin puede exportar y preparé una defensa ante truncamiento silencioso del iterador del collector, usando su error de consulta existente. Esa corrección Kotlin y el harness añadido siguen pendientes de compilación/ensayo Android.

**API histórica y C1**

`POST /v1/historical/evaluate` recibe únicamente `daily_use_duration_minutes_v2` ya preparada. No recibe exports, cabecera de serie, raw, PMUM ni v3. Procesa el día con un perfil C1 explícito y guarda representación, estado y recibo original de manera coordinada.

Si se pierde la respuesta, el mismo payload recupera el mismo resultado, incluidos IDs y fechas, después de reiniciar. HTTP 200 `processed` reconoce una entrada persistida, aunque el análisis diga `ABSTAIN`: no repetir hasta conseguir CHANGE. Conflictos de contenido, procedencia u orden devuelven 409; no crear IDs nuevos para eludirlos. El backend conserva una cola durable/payload y ordena por serie; esa persistencia de tu backend todavía debemos probarla juntos.

SMOKE_ONLY es un perfil ficticio para comprobar conexión y recuperación, no calibración ni configuración de producto. No cambié parámetros C1 ni su política de referencia, y no incorporé automáticamente v3. Un CHANGE técnico no activa alertas, actividades, ofertas ni tarjetas.

**Formulario, actividades y PMUM**

`POST /v1/activities/eligibility` distingue “Ninguna” explícita de desconocido. Acepta una opción de movilidad —brazos/manos, piernas o ambas— y combinaciones con visual, auditiva y sensorial. Ninguna es exclusiva. Cuando las etiquetas no permiten resolver demandas concretas del catálogo devuelve `eligibility_state: unknown`, sin filtros inventados, y los temas funcionales que faltan.

Después el backend arma el cuerpo de `POST /v1/activities/select`: hasta tres actividades, contextos voluntary/general/bedtime, intereses, IDs recientes y filtros operativos. Si el estado consolidado es desconocido, se abstiene. `eligibility: {}` con estado conocido declara ausencia de exclusiones operativas; no reemplaza datos faltantes.

Las 18 actividades siguen siendo provisionales. Falta revisión funcional/profesional y, cuando corresponda, consignas adaptadas; no atribuimos seguridad clínica a las etiquetas. El selector no crea `offer_id`, guarda historial de ofertas ni registra entrega/elección/realización. Este bloque no implementa esos flujos.

PMUM conserva `/experimental/pmum-estimate` y los archivos externos del ZIP preparado anteriormente. Necesita habilitarse, montajes de modelo/manifiesto en solo lectura y SHA configurada; sigue `experimental: true` / `internal_research_only`. No se volvió a cargar el artefacto real en este bloque ni se usa para actividades, frecuencia o alertas. No está aprobado para mostrarlo a familias.

**Qué se probó y qué queda**

La entrega publicada `61e31ce` pasó previamente Windows/Docker con 257 pruebas de `tests/` y una omisión esperada de POSIX, otras 15 de la raíz y seis scripts heredados; HTTP, persistencia, reinicios y healthcheck también pasaron. Esos resultados pertenecen a esa entrega, no se transfieren al parche nuevo.

En esta ampliación se ejecutaron en Linux 288 pruebas de `tests/`, incluidas 30 nuevas, las 15 de la raíz y los seis scripts heredados. También pasó HTTP real export ficticio → preparador → v2 → histórico → persistencia, con terminación abrupta del proceso, reinicio y recuperación exacta de recibos. El perfil fue ficticio/no calibrado y PMUM estuvo deshabilitado. Los reportes de prueba del verificador de teléfono son simulados, no evidencia de ejecución Kotlin.

Falta validar el parche en Windows y reconstruir/probar la imagen, compilar los APKs, ejecutar el protocolo en un teléfono y probar tu backend. El protocolo conserva originales, reporte Kotlin, zona/clock, bitácora física y recibos; separa igualdad de reconstrucción de fidelidad real de captura. AWS sigue pendiente de integración conjunta, sin despliegue en este trabajo.

Para avanzar juntos necesitamos cerrar primero tus IDs y asignación/namespace, dónde corre el preparador con conservación durable de payloads, y la transición de fuente si ya persististe registros del puente anterior. Recomiendo un job Python junto al backend para reutilizar el preparador probado, antes que reimplementar fórmulas en otro lenguaje. La configuración real C1 y el mapeo profesional del catálogo siguen como decisiones del equipo; no tenés que resolverlos solo desde infraestructura.
