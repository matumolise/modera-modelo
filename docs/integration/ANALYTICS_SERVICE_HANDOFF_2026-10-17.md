# Entrega del servicio analítico para integración

Fecha: 17/10/2026. Rama `analytics-service-integration-candidate`.
Base local verificada: `8dbbc803d67e63fdd3b52b2151fa97b7f2d32807`.
Base publicada consultada: `adult-messages-bounded-audit-candidate`,
`7b7d0f50aa419d0ee8642bf825f6db8330422797`.

Esta entrega permite integrar un servicio Python con el backend de Juanma. No es
una APK ni toda la aplicación. No modifica el PDF entregado, backend o Android.
El bundle contiene los cierres posteriores al publicado y esta rama. El hash
exacto de entrega se obtiene con `git bundle list-heads` y `git rev-parse HEAD`.
No se publicó, hizo merge ni desplegó esta rama.

## Qué está disponible

| Función | Interfaz y alcance |
| --- | --- |
| Actividades voluntarias | `/v1/activities/eligibility` y `/v1/activities/select`, sin cambios. Conservar la integración existente de Juanma. |
| Histórico C1 | `/v1/historical/evaluate`, representación preparada `daily_use_duration_minutes_v2`, persistencia y recibos originales. |
| Mensajes adultos | `/v1/adult-messages/evaluate` e historial por perfil, sin cambiar reglas o parámetros. |
| Coordinador automático | Nuevos POST `/v1/child-offers/evaluate`, `/v1/child-offers/events` y GET `/v1/child-offers/profiles/{profile_id}/history`. |
| Preparación F12 | Adaptador y CLI existentes, separados del servidor HTTP. No hay endpoint de recepción de exports originales. |
| PMUM | Contrato experimental interno conservado. Deshabilitado en la configuración de integración. No bloquea estas funciones. |

El contrato nuevo está en `CHILD_OFFERS_HTTP_V1_2026-10-17.md`, en esta carpeta.
Las políticas originales continúan en `docs/own_closure` y
`docs/adult_messages/CONTRACT_AND_HANDOFF.md`.

## Importar en Windows desde la terminal PowerShell de VS Code

Usar una carpeta nueva. No ejecutar en una carpeta vieja suponiendo que ya tiene
los archivos nuevos. El bundle requiere la base publicada `7b7d0f5`.

```powershell
$serviceBundle = Join-Path $env:USERPROFILE 'Downloads\MODERA_ANALYTICS_INTEGRACION_2026-10-17.bundle'
git -C C:\tesis_modelo bundle verify "$serviceBundle"
if ($LASTEXITCODE -ne 0) { throw 'No se verificó el bundle. Revisar primero la base requerida.' }
git -C C:\tesis_modelo bundle list-heads "$serviceBundle"
git -C C:\tesis_modelo fetch "$serviceBundle" HEAD:refs/heads/analytics-service-integration-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se importó la rama. No forzar una rama existente.' }
git -C C:\tesis_modelo worktree add --detach C:\tesis_analytics_integracion_v1 analytics-service-integration-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se creó la carpeta nueva.' }
Set-Location C:\tesis_analytics_integracion_v1
git rev-parse HEAD
git merge-base --is-ancestor 8dbbc803d67e63fdd3b52b2151fa97b7f2d32807 HEAD
if ($LASTEXITCODE -ne 0) { throw 'La versión no contiene el cierre propio verificado.' }
```

Si falta la base publicada, puede recuperarse con `git fetch origin
7b7d0f50aa419d0ee8642bf825f6db8330422797` desde el repositorio, y repetir la
verificación. No publicar la rama ni modificar otras ramas para importarla.

## Comprobar en Windows sin Docker

Puede reutilizarse el entorno Python 3.10 existente, instalando las dependencias
fijadas. El ensayo HTTP crea un proceso local independiente y datos ficticios
en una carpeta nueva. No se conecta al teléfono ni al backend real.

```powershell
$servicePython = 'C:\tesis_mensajes_adulto_v1\.venv\Scripts\python.exe'
& $servicePython -m pip install -r requirements-integration-tools.txt pytest==9.1.1
if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación de dependencias.' }
& $servicePython -m pytest -q tests/test_child_offer_api.py tests/test_child_offer_coordinator.py tests/test_analytics_api.py tests/test_integration_closure.py::ConditionsCombinationsTests::test_review_matrix_covers_exact_catalog_without_implying_approval --junitxml=analytics_integracion_focal_windows.xml
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas focalizadas.' }
$serviceEvidence = Join-Path $PWD ('ensayo_servicio_ficticio_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
& $servicePython tools/validation/verify_analytics_service_integration.py --output-dir "$serviceEvidence"
if ($LASTEXITCODE -ne 0) { throw 'Falló el ensayo HTTP nativo.' }
```

Ejecutar también la regresión de la nueva versión antes de atribuirle validación
Windows. No se heredan resultados de `8dbbc80` ni de los candidatos anteriores.

```powershell
& $servicePython -m pytest -q tests test_intervention_history.py test_intervention_service.py test_intervention_engine.py test_intervention_history_reader.py test_recommendations.py test_child_choice_signals.py test_weekly_analysis.py test_inference.py --junitxml=analytics_integracion_completa_windows.xml
if ($LASTEXITCODE -ne 0) { throw 'Falló la regresión Windows.' }
```

## Levantar Docker para integrar

La plantilla está en `deploy/compose.analytics.integration.yml`. No publica
puertos al host. Solo el backend de la misma red debe acceder a
`http://analytics:8765`. El backend autentica al adulto y autoriza el perfil.
Android no conoce el token de este servicio ni llama directamente a su API.

El token debe tener al menos 16 caracteres ASCII sin espacios. Generarlo en la
sesión de PowerShell evita dejar un literal secreto en el historial. Conservarlo
en el gestor privado de secretos del entorno para reutilizarlo y configurarlo en
el backend. No copiarlo en Git, informes o capturas.

```powershell
$serviceRandom = New-Object byte[] 32
$serviceRng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$serviceRng.GetBytes($serviceRandom)
$serviceRng.Dispose()
$env:ANALYTICS_SERVICE_TOKEN = [Convert]::ToBase64String($serviceRandom)
$env:ANALYTICS_NETWORK = 'modera-integration'
$serviceCompose = @('-f', 'deploy/compose.analytics.integration.yml')
docker compose @serviceCompose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Configuración Compose inválida.' }
docker compose @serviceCompose build
if ($LASTEXITCODE -ne 0) { throw 'No se construyó la imagen.' }
docker compose @serviceCompose run --rm --no-deps initialize-child-offers
if ($LASTEXITCODE -ne 0) { throw 'No se pudo inicializar o validar el coordinador. No borrar su base.' }
docker compose @serviceCompose up -d analytics
if ($LASTEXITCODE -ne 0) { throw 'No se inició el servicio.' }
docker compose @serviceCompose exec -T analytics python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=5).read().decode())"
if ($LASTEXITCODE -ne 0) { throw 'El servicio no está disponible.' }
```

La red `modera-integration` se crea con esta plantilla. El Compose del backend
puede utilizarla como red externa con ese mismo nombre. Este paquete no modifica
su Compose. La imagen funciona con UID/GID `10001:10001`, raíz de solo lectura y
volumen en `/var/lib/modera`. No usar `down -v`, borrar bases o marcas para resolver
un error de arranque. En Linux, los bind mounts alternativos necesitan permisos
compatibles con ese UID. Conservar volumen y versión al actualizar.

La inicialización del coordinador es explícita. Si una base ya utilizada falta,
no utilizar la inicialización para ocultar su pérdida. Restaurar el estado y los
recibos. El histórico y los mensajes mantienen sus controles existentes de
repositorio inicializado. Copias y restauraciones deben incluir sus archivos y
marcas asociadas y realizarse con el servicio detenido o un mecanismo consistente.

El contenedor contiene el servicio HTTP, no las herramientas de preparación ni
los originales PMUM. El job F12 existente se ejecuta por separado con
`requirements-integration-tools.txt`, conservando originales, cabecera y payload.
No se introdujo un scheduler ni se supone que el preparador ya recibe Android.

## Qué comprobar juntos antes de AWS

1. Construcción, arranque y salud del contenedor en el entorno de Juanma.
2. Acceso desde su backend con el token y IDs autorizados, sin exponer el puerto
   del servicio analítico a Internet.
3. Evaluación, acuse de entrega, respuesta e historial usando una serie ficticia
   separada. Mismo `offer_id`, sin doble contador y sin confundir replay con permiso
   para mostrar. Los flags deben provenir de datos verificables, no de constantes
   para habilitar ofertas.
4. Persistencia del contenedor: registrar una operación ficticia, reiniciar,
   repetir exactamente la petición y comparar IDs, recibos e historial. El ensayo
   nativo entregado no reemplaza esta comprobación dentro de Docker.
5. Incorporar una muestra del export Android actual y contrastarla con
   `F12_EXPORT_ADAPTER_2026-10-12.md` antes de conectar el preparador. Mantener los
   agregados del panel separados de la representación histórica.
6. En AWS, comprobar red privada, secretos, permisos, volumen, reinicio y
   recuperación del despliegue concreto. No se ejecutó ese despliegue aquí.

## Límites de la entrega

- C1 usa el archivo `tests/fixtures/historical_c1_smoke_only.json`. Es un perfil
  de ensayo, no calibración infantil ni configuración aprobada de producto.
- Catálogo provisional, sin dictamen profesional atribuido. PMUM deshabilitado.
- Los mensajes adultos conservan su evaluación semanal y no dependen del score
  PMUM ni de un evento C1 para abrir una tarjeta.
- La nueva API no demuestra permisos de overlay/notificaciones, captura continua,
  autorización integral, comprensión de consejos o realización de actividades.
- Revocación, desvinculación, eliminación de derivados y política operativa de
  conservación continúan bajo la integración de privacidad, sin certificación legal.
- Las traducciones modifican solo comentarios `#`. Se preservaron identificadores,
  cadenas funcionales, docstrings, licencias y directivas. Dos comentarios en inglés
  dentro de `recommend_activities` se conservaron porque `inspect.getsource` participa
  de `SELECTOR_VERSION` y de la semilla. Cambiarlos alteraría el contrato observable.
- No se actualizó el PDF entregado ni se atribuyeron estas pruebas a ese documento.

Los resultados de esta versión están en `ANALYTICS_SERVICE_RESULTS_2026-10-17.md`.
