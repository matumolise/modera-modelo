# Analytics: candidato técnico para integración con Juanma

Fecha: 11/10/2026. Base de los archivos modificados: e736500.
Este parche añade infraestructura y adaptadores; no cierra F16 ni habilita histórico, tarjetas o coordinador de ofertas.

## Aplicación del parche

Se preparó contra dos archivos publicados en e736500 y añade archivos nuevos.
La rama f12-interactive-duration-v3 también contiene esa base. No modificar un árbol con cambios locales sin revisarlos.

Desde C:\tesis_modelo en PowerShell, con el parche descargado:

```powershell
git status --short
git branch --show-current
git rev-parse --short HEAD
git apply --check "$env:USERPROFILE\Downloads\modera_analytics_candidate_2026-10-11.patch"
```

El check debe hacerse contra la rama/estado real; esta revisión no leyó la computadora Windows. Si informa conflictos, conservar la salida y comparar los archivos; no forzar la aplicación.

Luego aplicar en una rama aislada basada en la rama HU o v3 correspondiente:

```powershell
git switch -c analytics-api-candidate
git apply "$env:USERPROFILE\Downloads\modera_analytics_candidate_2026-10-11.patch"
```

No se hizo commit, push o merge al repositorio remoto en esta revisión.

## Ejecución y pruebas

```powershell
.\.venv-analytics\Scripts\python.exe -m pip install -r requirements-analytics-test.txt
.\.venv-analytics\Scripts\python.exe -m unittest discover -s tests -p test_analytics_api.py -v
$env:ANALYTICS_SERVICE_TOKEN = "<credencial propia de 16+ caracteres ASCII sin espacios>"
$env:ANALYTICS_PMUM_ENABLED = "false"
$env:ANALYTICS_ACTIVITIES_ENABLED = "true"
.\.venv-analytics\Scripts\python.exe analytics_api.py
```

Usar un entorno aislado para probar estas dependencias; no reemplazar inadvertidamente el entorno de entrenamiento. analytics.env.example documenta variables; el entrypoint no carga archivos .env automáticamente.

API: 127.0.0.1:8765 por defecto. Host/puerto configurables por entorno.
Uvicorn ejecuta un único worker, sin access log ni confianza en cabeceras de proxy. Se eligió ASGI para la infraestructura compartida, en vez de ampliar ThreadingHTTPServer. FastAPI carga el modelo durante lifespan, antes de atender solicitudes.

El timeout de 10 segundos es una decisión operativa inicial para recibir el cuerpo de solicitud; no garantiza cancelar un predictor bloqueado. limit_concurrency=32 es un límite provisional de conexiones/tareas del servidor; no es un parámetro conductual.

## Endpoints

| Ruta | Comportamiento |
|---|---|
| GET /health/live | Proceso accesible; sin credencial |
| GET /health | Readiness por capacidades; sin credencial, sin datos personales |
| POST /experimental/pmum-estimate | Contrato experimental publicado, con modelo cargado una vez |
| POST /v1/activities/select | Selección pura del catálogo publicado provisional |
| POST /v1/historical/evaluate | 503 historical_not_implemented; no procesa ni persiste |

Todas las rutas salvo GET de salud requieren Authorization: Bearer CREDENCIAL. Backend de Juanma hace autorización por perfil; la app no llama directamente a analytics. Usar red interna y TLS cuando la conexión atraviese una frontera de red. No publicar el puerto automáticamente mediante Compose.

Cada capacidad habilitada es requerida para readiness. Si PMUM no carga, el arranque falla. Si una inferencia falla después, PMUM pasa a UNAVAILABLE y /health devuelve 503; la selección puede seguir funcionando. Reiniciar tras resolver el problema. Una capacidad deshabilitada aparece DISABLED y no bloquea readiness. Si ambas están deshabilitadas, /health devuelve 503.

## PMUM v1

Para activarlo: ANALYTICS_PMUM_ENABLED=true, MODEL_PATH, MODEL_MANIFEST_PATH y MODEL_SHA256 explícitos. El hash esperado debe provenir de Matías/una entrega confiable; calcular el hash de cualquier archivo recibido no autentica su origen. Se verifica antes de deserializar y se cargan los bytes ya comprobados.

Artefacto y manifiesto quedan fuera de Git y de la imagen. El hash documentado del archivo Windows v1 es 56c991f40e56d2241196dc6f9efc1c9027c079e98a1b67549f48b10292e371e0; confirmar que el archivo entregado sea ese. Un reentrenamiento exige registrar otra huella y verificar el artefacto, no copiar ese hash.

Se comprueban versión, fuente, entradas, 803 casos, sex_codes, target y predicción de referencia 2.6959. Son controles técnicos, no validación clínica o externa. No se redistribuye el artefacto en este paquete.

```json
{"age":9,"sex_code":1,"weekday_category":2,"weekend_category":3,"respondent":"parent_or_caregiver","reference_days":30}
```

Se conserva el contrato parental anterior: estimated/unavailable, motivos y salida internal_research_only. Edad debe capturarse en años cumplidos; el adaptador conserva su validación numérica publicada. sex_code=1 corresponde a varón y 2 a mujer; null no se transforma en otro código. PMUM v2 sin sexo no está activado.

El módulo antiguo estimate(path,request) y el CLI del candidato siguen disponibles. La refactorización añade estimate_with_predictor para reutilizar las mismas abstenciones con el estimador en memoria, sin alterar entrenamiento ni parámetros del modelo.

## Actividades y elegibilidad

```json
{
  "request_id":"req-demo-01",
  "context":"voluntary",
  "eligibility_state":"known",
  "eligibility":{},
  "interests":["drawing"],
  "recently_shown_ids":[]
}
```

known exige filtros explícitos. Un objeto vacío significa que el backend declara que no hay exclusiones operativas conocidas; no acredita revisión profesional ni adaptación clínica.

Si el formulario fue omitido o todavía no puede mapearse:

```json
{"request_id":"req-demo-02","context":"voluntary","eligibility_state":"unknown"}
```

Devuelve 200, status=unavailable, reason=eligibility_unknown y activities=[]. No agregar eligibility en ese caso. Este es un ajuste nuevo para preservar omisión distinta de “Ninguna”, no una regla de interfaz previamente implementada.

Filtros admitidos: excluded_activity_ids, excluded_categories, allowed_activity_levels, allow_requires_other_person y allow_may_require_device_interaction. Listas con vocabularios explícitos y booleanos reales; no strings como "false". contexts: voluntary/general/bedtime. Con condiciones como visual/movilidad/sensibilidad sensorial aún sin mapear, no declarar known por defecto.

El catálogo usado es el código publicado, no la propuesta para Cecilia. catalog_version es una huella SHA-256 de todos sus campos; catalog_status=PROVISIONAL. Una modificación del contenido cambia la huella.

La selección puede devolver 1..3 actividades o cero con no_eligible_activities. No escribe historial, no crea offer_id ni acredita presentación. El score y selected_activity_counts no son entradas admitidas. La app/backend debe usar el contrato de oferta/entrega por separado. selector_version identifica por huella el código del selector publicado; una modificación de ese código cambia la versión y la huella de selección.

Reproducibilidad: igual request_id + entrada normalizada + catálogo y selector producen igual selección dentro del runtime comprobado. selection_fingerprint incluye la entrada normalizada y ambas versiones. Cambiar parámetros con el mismo request_id produce otra huella, no un conflicto 409. Esto no constituye idempotencia de ofertas ni garantía entre versiones del adaptador/runtime. El backend conserva la respuesta que efectivamente vincula a una oferta y su versión de API/catálogo/selector.

## Errores

400: esquema de selección, JSON no válido/no finito/duplicado, cuerpo incoherente.
401: credencial ausente o incorrecta.
404/405: ruta/método no admitido.
408: venció recepción del cuerpo.
413: cuerpo mayor de 16384 bytes.
415: Content-Type distinto de application/json.
503: capacidad deshabilitada/no implementada o modelo que dejó de funcionar.
500: fallo interno no esperado; sin traza/payload al cliente.

Una abstención PMUM válida y elegibilidad desconocida siguen siendo 200 con estado explícito. No confundirlas con fallos técnicos. Las respuestas de éxito y error se marcan no-store.

## Docker

Dockerfile.analytics propone Python 3.10 para acercarse al entorno del artefacto documentado. Las dependencias instaladas declaran soporte para 3.10, pero en esta revisión se ejecutaron con Python 3.12.14. No hay Docker disponible aquí: build, healthcheck de imagen y carga del artefacto Windows en Linux/3.10 quedan pendientes.

```text
docker build -f Dockerfile.analytics -t modera-analytics:candidate .
```

La imagen copia únicamente el wrapper, el selector y los módulos HU necesarios. Se ejecuta con UID/GID 10001. El archivo de exclusión específico evita incluir modelos, datos, secretos y cachés en el contexto. No se crea almacenamiento histórico porque el endpoint todavía no lo usa.

Para Compose, Juanma puede añadir un servicio interno analytics, puerto de contenedor 8765, ANALYTICS_HOST=0.0.0.0, token por entorno/secreto y, si activa PMUM, montajes de artefacto/manifiesto de solo lectura. No usar el ejemplo local con 127.0.0.1 dentro de Compose si el backend está en otro contenedor.

## Verificación realizada y pendiente

Pruebas de contrato con fixtures artificiales: autenticación, salud, carga única, hash previo a deserialización, archivo/metadata inválidos, abstenciones, error de inferencia, elección vacía, filtros, unknown, reproducibilidad y límites HTTP. Se ejecutó smoke por HTTP en proceso Uvicorn real.

El artefacto real se verifico posteriormente en Windows, como se documenta abajo. Docker, AWS, backend y Android siguen pendientes. La suite nueva no reemplaza las pruebas globales del proyecto tras aplicar el parche. No se añade configuración C1, persistencia histórica, política de ofertas, revisión profesional ni tarjeta semanal.

Aplicacion aislada y comprobacion del artefacto confiable completadas en Windows. Después integrar histórico con configuración C1 y exclusión mutua; no enviar el agregado v3 a C1 por adelantado.

Referencias primarias de infraestructura:
- https://fastapi.tiangolo.com/advanced/events/
- https://www.uvicorn.org/settings/
- https://docs.docker.com/build/building/context/#dockerignore-files

## Validacion local Windows posterior

Fecha: 2026-10-11. Resultados ejecutados por Matias y revisados mediante
las salidas de consola compartidas.

- Worktree: C:\tesis_modelo_analytics; rama analytics-api-candidate; base e736500.
- Entorno separado .venv-analytics creado desde Python 3.10.0 de C:\tesis_modelo\.venv.
- Suite del candidato: 28 pruebas aprobadas.
- Uvicorn accesible por HTTP en 127.0.0.1:8765.
- Actividades: seleccion de tres; abstencion con eligibility_unknown.
- Textos HTTP comprobados mediante decodificacion UTF-8.
- Solicitud sin credencial: 401. Historico no implementado: 503.
- Artefacto HU v1: SHA-256 coincide con la huella registrada.
- PMUM y actividades READY en el mismo proceso.
- Caso PMUM de referencia: estimated, 2.6959, internal_research_only.
- Edad 5 y sex_code null: unavailable, invalid_feature_value.
- Misma seleccion y huella de actividades al habilitar PMUM.

Esta verificacion es tecnica y local. El modelo mantiene su condicion
experimental, sin aprobacion para integrar en la app ni validacion externa;
el catalogo mantiene su condicion provisional. No se verificaron Docker,
AWS, backend ni Android. Suite global: 194 pruebas aprobadas.

Los comandos de ejecucion requieren crear previamente .venv-analytics.
La aplicacion realizada utilizo un worktree independiente para conservar
los archivos locales sin seguimiento de C:\tesis_modelo.


## Resultado de la suite global Windows

2026-10-11: 194 pruebas en 9.454 segundos; OK. Comando: python -m unittest discover -s tests -t . -v. pandas==2.3.3 instalado solo en el entorno separado, respetando las restricciones del candidato.
