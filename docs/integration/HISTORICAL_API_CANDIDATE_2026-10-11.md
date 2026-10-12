# Histórico C1: candidato de integración HTTP

Base exacta: `6b0c55d0e43b27e8364aea90f60bad3f0a14e59b`, la entrega publicada a Juanma.
Esta ampliación se prepara aparte. No modifica la rama publicada ni implica merge,
despliegue AWS, validación Android o parámetros de producto aprobados.

## Qué implementa y qué conserva

`analytics_api.py` sigue siendo el entrypoint; un proceso, un worker, puerto
configurable (8765 en contenedor). La versión de salud pasa a
`analytics-api-v2-historical-candidate`. Los contratos de PMUM y actividades
se conservan. El histórico queda deshabilitado por defecto y se habilita
únicamente con perfil C1 y repositorio explícitos.

`POST /v1/historical/evaluate` consume una representación canónica **v2 ya
construida** y llama al servicio C1 publicado. No recibe directamente exports
Android, eventos brutos, once features sintéticas, puntajes PMUM ni el agregado
`interactive_screen_device_minutes_v3_draft`. Los adaptadores F12 existentes
siguen siendo la capa que debe construir la representación; su conexión con
el backend y su equivalencia en un teléfono siguen pendientes.

El resultado es técnico. Un `CHANGE` o un evento de cruce no constituye por sí
solo una alerta, diagnóstico, recomendación para adultos ni intervención al niño.
No se incorpora interpretación, notificación/pop-up, reset, cooldown, rearmado,
tarjeta semanal o aprendizaje de preferencias.

## Configuración obligatoria

Variables adicionales:

| Variable | Significado |
|---|---|
| `ANALYTICS_HISTORICAL_ENABLED` | `true`/`false`; por defecto `false` |
| `ANALYTICS_HISTORICAL_CONFIG_PATH` | Ruta absoluta al perfil JSON, de solo lectura para el servicio |
| `ANALYTICS_HISTORICAL_REPOSITORY_PATH` | Ruta absoluta al archivo persistente en un directorio escribible |

También se requiere `ANALYTICS_SERVICE_TOKEN`: 16+ caracteres ASCII sin espacios.
Las rutas no llegan desde el cuerpo HTTP. `analytics.env.example` documenta
variables; el entrypoint no carga automáticamente un `.env`.

`historical.config.example.json` muestra la forma, pero tiene parámetros `null`
y **no es ejecutable**. No hay valores predeterminados de `k`, `threshold` o
`min_history`. Una configuración incompleta o un perfil incompatible impide
el arranque cuando el histórico está habilitado.

Para comprobaciones reproducibles existe únicamente este fixture:
`tests/fixtures/historical_c1_smoke_only.json`.

```json
{
  "schema_version": 1,
  "configuration_id": "smoke-only-not-calibrated",
  "scope": "internal_technical_candidate",
  "representation_spec_id": "daily_use_duration_minutes_v2",
  "reference_policy": "all_prior_usable_records_v1",
  "analysis_version": "published-c1-smoke-v1",
  "emitter_version": "published-crossing-smoke-v1",
  "detector": {"k": 0.5, "threshold": 3.0, "min_history": 3}
}
```

Esos tres números provienen de casos de prueba del núcleo publicado; no son
calibración ni recomendación de producto. No se debe conectar este fixture a
datos reales del MVP como si fuera un perfil aprobado. La elección de parámetros
reales continúa abierta y no se resuelve usando el rendimiento del smoke.

El perfil se carga una vez durante el arranque. No se acepta reemplazar parámetros
mediante una solicitud ni recargar el perfil en caliente. Su huella se calcula
sobre el contenido normalizado (incluidas versiones y política de referencia).

La política indicada conserva el servicio publicado: referencia robusta basada
en todos los registros utilizables estrictamente anteriores, mediana y MAD;
CUSUM bilateral y emisor de cruce ascendente. No se presentan esas decisiones
como una política final de producto. Cambiar la ventana o la semántica exige
versionar el contrato y resolver la transición del historial.

## Solicitud HTTP

Requiere `Authorization: Bearer CREDENCIAL` y `Content-Type: application/json`.
Solo se admiten dos campos superiores: `request_id` y `representation`.

```json
{
  "request_id": "attempt-device-test-01-20260901",
  "representation": {
    "representation_record_id": "rep-device-test-01-20260901-v2",
    "representation_spec_id": "daily_use_duration_minutes_v2",
    "subject_id": "device-test-01",
    "phenomenon": "DAILY_USE_DURATION",
    "interval_start": "2026-09-01T00:00:00Z",
    "interval_end": "2026-09-02T00:00:00Z",
    "value": 90,
    "unit": "minutes",
    "status": "OBSERVED",
    "coverage": {"value": null, "basis": null},
    "quality_flags": [],
    "provenance": {
      "source_id": "fictitious-contract-example",
      "source_version": "example-v1",
      "source_semantics": "fictitious canonical representation",
      "adapter_version": "v2",
      "input_fingerprint": "example-input-20260901"
    },
    "computed_at": "2026-09-02T01:00:00Z"
  }
}
```

El ejemplo es ficticio. La API no identifica al niño ni demuestra que una
medición corresponde a su uso personal. El backend debe autorizar al perfil y
preservar el sujeto, la fuente y el alcance de la representación upstream;
no debe relabelar el agregado v3 del dispositivo como esta v2.

Todos los campos de la representación son explícitos. Se acepta únicamente
`daily_use_duration_minutes_v2`, `DAILY_USE_DURATION`, `minutes` y adaptador `v2`.
Las fechas requieren zona horaria y se normalizan a UTC. El intervalo debe ser
creciente. Identificadores: 1..128 caracteres ASCII alfanuméricos o `_.:-`.
Textos de procedencia y flags: hasta 256 caracteres; hasta 64 flags.

Semántica de valores:

- `OBSERVED`: número finito no negativo y distinto de cero.
- `OBSERVED_ZERO`: número cero realmente observado.
- `MISSING` y `NOT_APPLICABLE`: `value: null`; se conservan diferenciados.
- Cobertura desconocida: `value: null`, no se convierte en cobertura completa.
- Flags y procedencia se conservan. No se inventan nuevos umbrales de cobertura
  ni nuevas políticas de exclusión de flags: se mantienen las del núcleo.

Se rechazan campos adicionales, parámetros C1 del cliente, valores no finitos,
duplicación de claves JSON, tipos incoherentes, valores negativos, fecha ingenua
y cualquier especificación v3. Esta validación es estructural y semántica de
contrato; no certifica la calidad o autenticidad de la captura Android.

## Respuesta y reintentos

Una operación procesada responde HTTP 200:

```json
{
  "status": "processed",
  "request_id": "attempt-device-test-01-20260901",
  "replayed": false,
  "historical_api_version": "historical-http-v1-candidate",
  "configuration_id": "smoke-only-not-calibrated",
  "configuration_fingerprint": "SHA256-del-perfil-normalizado",
  "scope": "internal_technical_candidate",
  "result": {
    "reference": "objeto completo del serializador publicado",
    "evaluation": "objeto completo del serializador publicado",
    "emission": "objeto completo del serializador publicado",
    "next_state": "objeto completo del serializador publicado"
  }
}
```

Las cadenas de `result` son marcadores de documentación, no objetos que deba
enviar un cliente. En la respuesta real son los objetos de
`historical.receipts.serialize_analysis_result`, con campos, enums y fechas
completos. `evaluation.outcome` puede ser `ABSTAIN`, `NO_CHANGE` o `CHANGE`.
`emission.decision` es `EMIT`/`NO_EMIT` y `emission.event` puede ser `null`.
Una abstención técnica se guarda con su recibo y responde 200; no es fallo HTTP.

La identidad durable es **`representation_record_id`**, global en el repositorio;
el backend debe generar identificadores estables y sin colisiones entre sujetos.
`request_id` solo identifica el intento HTTP. El servidor genera los IDs de
evaluación/evento y sus fechas de procesamiento. El cliente no los impone.

Un reintento compatible recupera `result` sin recalcular ni reescribir, incluso
después de reiniciar, conservando IDs, fechas, referencia, evento y estado
originales. `replayed` pasa a `true`; el `request_id` de la envoltura puede cambiar.
Puede variar `representation.computed_at` al reconstruir la misma entrada;
el repositorio conserva la fecha original. Los otros campos deben coincidir,
tras normalizar las fechas a UTC.

Errores principales:

| HTTP | Código JSON | Efecto |
|---|---|---|
| 400 | `invalid_historical_request` / `invalid_json` | Solicitud inválida; no escribe |
| 401 | `unauthorized` | Falta credencial válida |
| 409 | `representation_conflict` | ID existente con otra entrada; no escribe |
| 409 | `historical_order_conflict` | Entrada nueva fuera de orden o solapada; no escribe |
| 503 | `historical_disabled` | Capacidad deshabilitada |
| 503 | `historical_unavailable` | Fallo del repositorio/procesamiento; requiere resolver y reiniciar |

Siguen vigentes 408 por recepción lenta del cuerpo, 413 por superar 16384 bytes,
415 por contenido distinto de JSON y errores genéricos sin trazas al cliente.
El timeout de cuerpo no cancela una transacción que ya comenzó. Si el backend
pierde la respuesta debe reintentar con la misma identidad y entrada.

Cada sujeto debe enviarse en orden de intervalo. Se admiten huecos temporales.
No se rellena automáticamente un hueco con ceros; un registro `MISSING` debe
venir explícitamente de la capa que construye observaciones. Un dato tardío que
solapa el historial no desencadena recomputación retrospectiva automática.

## Persistencia y coordinación

Se reutiliza `FileHistoricalRepository` y `process_c1_representation` sin modificar
sus módulos. La subclase del adaptador mantiene formato 3 e incorpora
`analytics_binding`, con perfil normalizado y huella, al mismo archivo de
representaciones, streams y recibos. Ese vínculo se publica con el primer
progreso, en el mismo reemplazo atómico.

Se valida asociación de recibos/representaciones, cadena de estados, último
estado, orden y vínculo de configuración. No se recalcula el detector para
recuperar recibos. Un repositorio previo sin vínculo, un formato antiguo o un
perfil distinto impiden el arranque; no se migra, borra ni reinicia silenciosamente.
Una eventual importación de historiales anteriores requiere un trabajo separado.

Archivos gestionados:

- `history.json`: representaciones, estado, recibos y configuración vinculada.
- `history.json.writer.lock`: reserva exclusiva del escritor durante el proceso.
- `history.json.initialized`: marca de que existió un repositorio; evita que su
  desaparición se trate como un inicio nuevo. No contiene datos del niño.
- `.history.json.tmp`: temporal usado en el reemplazo; no es un historial nuevo.

Un mutex global serializa **todo el archivo**, no solamente un sujeto: lectura,
recuperación, análisis y escritura. Una reserva del sistema operativo rechaza
un segundo proceso/worker que use el mismo archivo. POSIX usa `flock`; Windows
usa `msvcrt.locking`, sin dependencia adicional.

No eliminar o reemplazar el archivo de reserva mientras el servicio corre. No
escribir desde el backend, herramientas de bajo nivel u otros procesos que no
honren esta reserva. Usar un worker y una réplica por volumen. No se promete
coordinación distribuida ni compatibilidad de bloqueos entre Windows y Linux
sobre una carpeta compartida. Preferir volumen local del daemon Docker; NFS/SMB
o volúmenes distribuidos requieren validación específica y otra arquitectura.

El reemplazo conserva el `fsync` del archivo del núcleo; el adaptador agrega
sincronización del directorio en POSIX. No promete protección contra todos los
fallos físicos. Mantener backups consistentes del volumen con el servicio detenido.
Este backend valida y reescribe un documento completo; su costo crece con el
historial total y las solicitudes se serializan. Es un candidato de archivo para
comprobación/piloto, no una demostración de capacidad para alto volumen o réplicas.
No se recorta historial automáticamente para ocultar ese límite. Si el despliegue
requiere otra escala, debe diseñarse y probarse un backend transaccional adecuado.
Eliminar todo el volumen o su contenido no es una operación que esta API pueda
revertir; la marca evita únicamente reiniciar cuando desaparece el JSON y la
evidencia de inicialización sigue disponible.

Si el fallo ocurre antes de reemplazar, se conserva la versión anterior. Si el
guardado terminó y se perdió la respuesta, tras resolver/reiniciar se recupera
el recibo original. Un fallo técnico deja histórico `UNAVAILABLE`; no inventa
un estado vacío para continuar atendiendo.

## Salud

`GET /health` sigue público y no expone rutas, sujetos ni registros. Incluye
estado histórico, versión de API histórica, configuración y huella, especificación
y alcance técnico. Revisa la reserva y la integridad disponible del repositorio.
La comprobación inicial también verifica acceso y escritura en el directorio.
No garantiza por anticipado toda escritura futura; un fallo de escritura se
refleja al observarlo. Si cualquier capacidad habilitada no está disponible,
la salud general es 503; `/health/live` continúa 200 mientras el proceso sirve.
Actividades o histórico pueden seguir atendiendo si falla otra capacidad,
aunque la salud general no esté READY.

Con el histórico deshabilitado: `state=DISABLED`, `implemented=true`, perfil `null`.
Con configuración inválida, escritor ocupado o repositorio incompatible, el
arranque falla. El cambio respecto de 6b0c55d se identifica por la versión v2
de la API de salud; no debe atribuirse a la rama ya entregada.

## Windows: comprobación de este candidato

La entrega incluye un aplicador externo que verifica SHA del parche, crea un
worktree aparte sobre 6b0c55d y llama al ejecutor de este repositorio.
El ejecutor requiere el Python 3.10 del entorno original y crea `.venv-historical`;
no modifica `.venv` o `.venv-analytics` ni realiza commit, push o merge.

Después de aplicar manualmente el parche, puede ejecutarse directamente:

```powershell
& "C:\tesis_modelo\.venv\Scripts\python.exe" `
  "C:\tesis_modelo_historical\tools\validation\validate_historical_candidate_windows.py"
```

Realiza instalación, `pip check`, pruebas de `tests/`, 15 pruebas unitarias de la
raíz y seis scripts heredados en un directorio aislado. Luego levanta Uvicorn en
127.0.0.1:8767 con datos ficticios, guarda casos `ABSTAIN`/`NO_CHANGE`/evento,
termina **solo ese proceso** y verifica recuperación después de volver a iniciar.

Si Docker está disponible en modo Linux, valida `docker compose config`, construye
una imagen con tag independiente, crea un volumen de prueba y expone el contenedor
solo en 127.0.0.1:8768. Comprueba HTTP, reinicio, UID/GID 10001 y healthcheck.
Elimina solo su contenedor de prueba al terminar; conserva el volumen y la imagen.
No detiene los servicios que ya están en 8765/8766.

Los puertos pueden ajustarse con `--local-port`/`--docker-port`. `--skip-docker`
deja esa parte explícitamente pendiente. No reutiliza un entorno existente ni
sobrescribe el directorio de evidencia. Una ejecución fallida debe revisarse
antes de repetir; no borra automáticamente el worktree o el entorno parcial.

Los logs y `validation_summary.json` quedan en un directorio nuevo de Documents,
con identificadores ficticios y sin guardar la credencial temporal generada.
El perfil de smoke permanece etiquetado como no calibrado y PMUM está deshabilitado
en estas comprobaciones; la coexistencia de tres capacidades se prueba con fixture.

## Docker y Compose

`Dockerfile.analytics` añade el paquete histórico y un directorio persistente
con UID/GID 10001. El repositorio y el perfil no se copian en la imagen.
`compose.analytics-historical.candidate.yml` es una plantilla **sin backend**:
red interna, sin publicación de puertos, volumen persistente, perfil montado
en solo lectura, raíz de contenedor de solo lectura y tmpfs para temporales.

Antes de usarla, definir `ANALYTICS_SERVICE_TOKEN` y la ruta absoluta del perfil
en `ANALYTICS_HISTORICAL_CONFIG_FILE`; no confundirla con la ruta interna
`ANALYTICS_HISTORICAL_CONFIG_PATH`. La plantilla se integra a la red del backend;
no establece por sí misma la infraestructura AWS ni el enrutamiento de producción.
No escalar el servicio ni ejecutar dos despliegues sobre el mismo volumen.

Una imagen anterior probada por Matías en Windows no verifica esta nueva imagen.
Build, ownership, montajes, reserva nativa Windows y reinicio de este candidato
deben ejecutarse en su computadora con el runner antes de dar esa parte por PASS.

## Evidencia de la preparación local

Runtime: Linux, Python 3.12.14. Dependencias del servicio fijadas como en 6b0c55d;
sin nuevos paquetes de runtime. Snapshot acotado de 86 archivos fuente/test/modelo,
verificados uno por uno contra sus SHA de blob Git; no es un clon completo.

- Base antes de cambiar: 194 pruebas de `tests/`, PASS.
- Candidato: 231 pruebas de `tests/` (194 previas, con expectativas de salud
  actualizadas, más 37 nuevas), PASS.
- Raíz: 15 pruebas unitarias en dos módulos, PASS.
- Otros seis scripts de la raíz: código 0 y sin marcadores impresos de ERROR;
  algunos son demostraciones, no se cuentan como pruebas unitarias adicionales.
- HTTP real con Uvicorn: seed/replay, rechazo de segundo escritor, terminación
  abrupta y recuperación, sin reescritura de recibos, y solicitudes concurrentes.
- Coexistencia PMUM/actividades/histórico con predictor PMUM artificial, PASS.
- YAML de Compose analizado estáticamente; sin puertos públicos, una réplica,
  perfil de solo lectura y volumen. No reemplaza `docker compose config` real.
- Sintaxis de ejecutores, `pip check` y revisión del diff comprobados.

Se mantiene el aviso de deprecación de Starlette/httpx del entorno de pruebas;
no se cambian dependencias sin evidencia de fallo. Docker no está instalado en
este entorno. No se afirma ejecución Windows, Docker, AWS, Android ni carga del
artefacto HU real en **esta** ampliación. El módulo PMUM y las cuatro versiones
científicas no se modifican; la carga real fue comprobada en la entrega base.

Pendientes que requieren evidencia o decisión adicional: parámetros C1 de uso
real, política final de referencia/interpretación/intervención, migración si se
necesita conservar un repositorio previo sin vínculo, equivalencia de captura
en teléfono y contrato/backend. El mapeo de condiciones al catálogo no es parte
de este cambio. El agregado v3 permanece fuera.

Referencias primarias de infraestructura:

- https://docs.python.org/3.10/library/fcntl.html
- https://docs.python.org/3.10/library/msvcrt.html
- https://docs.docker.com/engine/storage/volumes/
# Corrección de recuperación Windows — 2026-10-12

La primera ejecución Windows aplicó el candidato sobre `6b0c55d`, creó el
entorno separado e instaló las dependencias sin incompatibilidades. La suite
terminó con 231 casos: 229 aprobados, un error al recuperar la reserva después
de terminar un proceso y una omisión esperada de una prueba exclusiva de POSIX.
La validación se detuvo antes de las comprobaciones HTTP y Docker del histórico.

Se corrige la reserva usando un descriptor sin buffering y hasta dos segundos
de reintentos breves de adquisición nativa en Windows. El plazo es técnico,
no es un umbral de C1. Un escritor vivo sigue impidiendo el arranque; nunca
se elimina el archivo de reserva ni se habilita escritura sin obtenerla.
La prueba real de terminación permanece activa, sin omitirla ni suavizarla.
Microsoft documenta que la liberación por terminación puede demorarse:
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex
Es una explicación compatible con el fallo observado, pendiente de confirmar
mediante la repetición en Windows.

El validador acepta ahora `--reuse-environment`: verifica Python 3.10 y todas
las versiones fijadas antes de reutilizar `.venv-historical`, ejecuta `pip check`
y repite la validación completa con datos y evidencia nuevos. Conserva la
evidencia anterior y no repite la creación del worktree.

Se agregan seis pruebas de regresión: liberación demorada simulada, contención
persistente, errores ajenos a la contención, descriptor sin buffering y
validación de dependencias recursivas con BOM o versiones contradictorias.
La implementación Windows nativa y Docker requieren completar la ejecución en
la computadora de Matías; las simulaciones Linux no sustituyen ese resultado.

## Validacion final Windows y Docker - 2026-10-12

Ejecucion realizada por Matias; resultados revisados mediante la salida de consola y validation_summary.json compartidos.

- Python 3.10 y dependencias verificadas; pip check aprobado.
- tests/: 237 casos en 22.401 segundos; 236 aprobados y una omision esperada exclusiva de POSIX.
- La recuperacion del bloqueo tras terminar un proceso paso en Windows.
- Raiz: 15 pruebas unitarias aprobadas en 0.235 segundos.
- Seis scripts heredados ejecutados correctamente; no se cuentan como pruebas unitarias adicionales.
- HTTP Windows: procesamiento y recuperacion de resultados originales tras terminar y reiniciar el proceso, aprobados.
- Docker: Compose validado, imagen construida, persistencia en volumen y recuperacion tras reiniciar, aprobados.
- UID/GID 10001 y healthcheck healthy comprobados; contenedor con raiz de solo lectura.
- Revision de formato del diff aprobada.

Evidencia local: `C:\Users\matum\Documents\modera_historical_smoke_20261012-005624-b0f74749`.

Imagen comprobada: `sha256:6bfeaa86f1d4d5f27cb8c17658c58f17789a06d724d9d7b31cf394f710fba0af`.

Volumen de prueba conservado: `modera-historical-smoke-20261012-005624-b0f74749`.

Esta ejecucion completa la validacion tecnica local pendiente. No calibra C1 ni valida backend, Android, AWS o uso con familias. PMUM estuvo deshabilitado en este recorrido. El agregado v3 permanece fuera de C1.
