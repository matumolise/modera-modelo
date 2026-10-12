# Protocolo ejecutable F12 en teléfono físico

Estado: preparado, **no ejecutado aquí**. No hay APK compilado ni export físico
nuevo verificado en este bloque. Las pruebas Python usan fixtures ficticias.
Este protocolo separa integridad del export, paridad de reconstrucción,
contraste físico y conexión con el backend.

## Qué se compara

1. El collector Kotlin consulta UsageEvents; el exportador existente escribe sus
   dos archivos originales. El harness verifica que filas/conteo correspondan
   al resultado en memoria y escribe un tercer archivo `parity_<run>.json`.
2. Una reconstrucción independiente Kotlin calcula estado/duración para un día
   local usando **una consulta**. No llama al preparador Python ni a C1.
3. El adaptador Python archiva esos bytes y produce v2. El verificador compara
   SHA, límites UTC, estado y duración contra el reporte Kotlin.
4. Un observador contrasta transiciones físicas y registra su incertidumbre.
   Coincidencia entre algoritmos sobre un export no demuestra que ese export
   refleje todo lo ocurrido en el aparato.
5. La API guarda el payload y recupera el recibo tras reiniciar. La vinculación
   del aparato al perfil y la cola durable del backend se verifican con Juanma.

El reporte del harness mantiene `manualCaptureValidation=PENDING` incluso si
coinciden los cálculos. Una evidencia manual posterior se guarda por separado,
sin cambiar los archivos exportados ni ese reporte.

## Preparación Windows

Aplicar primero el paquete de esta entrega en el worktree nuevo
`C:\tesis_modelo_f12_export`; conservar los anteriores. El validador prepara
`.venv-historical` e instala las dependencias fijadas. Abrir el proyecto
`tools\android-diagnostic` en Android Studio para tener el SDK/JDK y dispositivo
configurados. La base tiene compile/target SDK 37, min SDK 28, AGP 9.3.3 y wrapper
Gradle 9.5.0: se leyeron esos archivos, no se verificó aquí su descarga/build.
No bajar versiones ni modificar herramientas a ciegas si falla: guardar el log.

Con un teléfono propio de prueba desbloqueado, depuración USB autorizada y un
solo serial elegido explícitamente:

```powershell
Set-Location C:\tesis_modelo_f12_export\tools\android-diagnostic
.\gradlew.bat assembleDebug assembleDebugAndroidTest
if ($LASTEXITCODE -ne 0) { throw "No se compiló Android; conservar el log." }

# Si adb no está en PATH, usar su ruta de Android SDK platform-tools.
$adb = "adb"
& $adb devices -l
```

Anotar el serial mostrado; no seleccionar automáticamente el primer aparato.
Visualmente confirmar que es el teléfono físico de la evidencia. Instalar
solamente los dos APK diagnósticos en ese serial, sin desinstalar ni borrar datos:

```powershell
$serial = "REEMPLAZAR_SERIAL"
& $adb -s $serial install -r app\build\outputs\apk\debug\app-debug.apk
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación del APK diagnóstico." }
& $adb -s $serial install -r app\build\outputs\apk\androidTest\debug\app-debug-androidTest.apk
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación del APK de pruebas." }
```

Abrir la app y conceder Usage Access desde Ajustes para el caso habilitado;
revocarlo desde Ajustes para el caso sin permiso. El capturador no cambia
permisos, instala APKs ni realiza requests a backend. No usar un perfil familiar
real para las pruebas de extremo a extremo.

## Ventana explícita y captura

Elegir un **día local ya cerrado**, su zona IANA y un período consultado que
incluya el estado SCREEN previo al inicio. No se fija una cantidad arbitraria
de lookback. La UI de última hora no es prueba de un día completo.
Si la retención no permite obtener ese estado, el resultado debe ser MISSING;
no extender ficticiamente las consultas ni crear un evento previo.

Ejemplo para calcular los límites del día elegido, con la base IANA del
preparador (reemplazar la fecha por la del ensayo):

```powershell
Set-Location C:\tesis_modelo_f12_export
$python = ".\.venv-historical\Scripts\python.exe"
$dia = "2026-10-11"
$zona = "America/Argentina/Buenos_Aires"
& $python -c "from datetime import date,timedelta; from analytics_service.f12_bridge import _zone,_midnight; import sys; d=date.fromisoformat(sys.argv[1]); z=_zone(sys.argv[2]); print(int(_midnight(d,z).timestamp()*1000)); print(int(_midnight(d+timedelta(days=1),z).timestamp()*1000))" $dia $zona
if ($LASTEXITCODE -ne 0) { throw "Fecha/zona/límites no válidos." }
```

Guardar los dos números. Definir `$consultaInicio` a partir del período previo
que realmente se desea consultar y `$consultaFin` con el cierre del día. Ambos
son epoch ms, no segundos. Deben ser anteriores a la ejecución en el teléfono.
Un período consultado puede ser parcial en casos de prueba de gaps; no marcarlo
completo por haber finalizado la llamada.

```powershell
# Completar con los epoch ms elegidos: no usar 0/1 como ventana del ensayo.
$consultaInicio = [long](Read-Host "Epoch ms de inicio de consulta elegido")
$consultaFin = [long](Read-Host "Epoch ms del cierre elegido")
$evidencia = Join-Path $env:USERPROFILE "Documents\modera_f12_phone_caso_01"
& $python tools/validation/capture_f12_phone.py `
  --adb $adb --serial $serial `
  --query-begin $consultaInicio --query-end $consultaFin `
  --local-date $dia --time-zone $zona --output-dir $evidencia
if ($LASTEXITCODE -ne 0) { throw "Captura incompleta; conservar la evidencia, no declararla válida." }
```

El capturador exige carpeta nueva. Conserva log de instrumentación, propiedades
ADB, summary, events y parity, con SHA. No permite emulador; esa comprobación
no sustituye la confirmación visual del aparato. Si ADB no puede recuperar el
directorio privado/external files, conserva el log y tratar el caso como
pendiente; no reemplazarlo por fixtures ni redirigir bytes mediante PowerShell.

## Cabecera backend, preparación y verificador

Crear fuera de Git `binding.phone.json`, con la forma de
`tests/fixtures/f12_export/binding.synthetic.json`. Usar IDs opacos de prueba
asignados consistentemente a este aparato, zona y día del ensayo, y
`computed_at` posterior a la captura y cierre, con UTC explícito. No copiar los
IDs de fixture como vínculo real. Es responsabilidad del backend, no de Android.

La hora actual del PC puede obtenerse así; si difiere del teléfono, revisar los
relojes antes de preparar, sin agregar una tolerancia arbitraria:

```powershell
[DateTimeOffset]::UtcNow.ToString("o")
```

Preparar en otra carpeta nueva y comparar con el reporte recuperado:

```powershell
$cabecera = Join-Path $env:USERPROFILE "Documents\binding.phone.json"
$paquete = Join-Path $env:USERPROFILE "Documents\modera_f12_phone_preparado_01"
& $python tools/integration/build_historical_request_from_export.py `
  --binding $cabecera --run "$evidencia\summary.json" "$evidencia\events.jsonl" `
  --output-dir $paquete
if ($LASTEXITCODE -ne 0) { throw "No preparar/enviar una entrada inconsistente." }
& $python tools/integration/verify_f12_phone_parity.py `
  --report "$evidencia\parity.json" --packet $paquete
if ($LASTEXITCODE -ne 0) { throw "Paridad Kotlin/Python no aprobada; revisar." }
```

El verificador exige una consulta y zona del teléfono igual a la cabecera.
Si la zona de medición debe ser distinta, revisar esa política con el backend;
no silenciar la diferencia. Android y tzdata pueden tener bases IANA distintas:
una discrepancia de medianoches se registra y no se corrige cambiando los bytes.
Para lotes con consultas múltiples verificar cada par y usar el adaptador para
el lote; no usar un reporte de una consulta como prueba del conjunto.

La comparación exige misma duración a resolución de epoch ms; admite solo
0.001 ms por redondeo computacional al convertir minutos flotantes. Ese valor
es una tolerancia de cálculo, no un umbral físico, clínico ni de C1.

## Casos y criterios de aceptación

| Caso | Ejecución/evidencia | Aceptación |
|---|---|---|
| P1 Permiso ausente | Revocar Usage Access y ejecutar harness, conservar estado/log | Error `USAGE_ACCESS_NOT_GRANTED`, cero filas, MISSING, nunca cero observado |
| P2 Consulta vacía | Consultar una ventana elegida sin eventos retenidos; si no se reproduce, dejar pendiente | Conteo 0 consistente; sin estado previo, MISSING |
| P3 Pantalla ON/OFF | Anotar transiciones controladas con brackets de tiempo antes/después y luego consultar el día cerrado | Orden compatible y reconstrucción Kotlin/Python idéntica; contraste manual separado |
| P4 Cruce de medianoche | Pantalla activa antes del inicio o cierre; recuperar evento previo y límites | Recorte al día, sin sumar duración del día vecino; si falta estado/cobertura, MISSING |
| P5 Gap de consultas | Dos consultas deliberadamente separadas dentro del día, sin export que cubra el hueco | MISSING; no interpolar ni sumar solo los tramos disponibles |
| P6 Solapamiento | Dos consultas del mismo aparato con ventanas solapadas, UUID distintos | Conservar ambos pares, conteos íntegros y no doble duración; comparar contra consulta única que abarque ese tramo si está disponible |
| P7 Eventos repetidos | Reconsultar rango, conservar filas repetidas por runs; no editar originals | No doble conteo de estados; mismo run duplicado se rechaza |
| P8 Reinicio del teléfono | Anotar reinicio dentro del tramo requerido; recuperar eventos startup/shutdown cuando el SO los exponga | Si hay evidencia de lifecycle, MISSING; si el reinicio conocido no aparece, falla aceptación física, no inventar continuidad |
| P9 Reinicio de analytics | Enviar request guardado a servicio aislado, reiniciar conservando repositorio y perfil, reintentar | Mismo resultado original, IDs/fechas, `replayed=true`; sin duplicar registros |
| P10 Alteración | Copia aparte del paquete con metadato/bytes modificados; nunca editar originales | Verificador falla o API devuelve 409 para record ya recibido; no eludir con nuevo ID |
| P11 Cambio de zona/reloj | Registrar zona/offset antes/después, conservar clocks | Inconsistencia explícita; no usar zona del PC ni trasladar CUSUM entre series |
| P12 Fuente/identidad | Juanma valida instalación→aparato→asignación→perfil y namespace | Aislamiento entre perfiles y autorización; metadatos de modelo iguales no acreditan identidad |

Para P3 anotar hora inmediatamente antes y después de cada acción, método y
resolución del reloj, interacciones adicionales y cualquier demora. Comparar
los eventos con esos brackets y el orden esperado. El intervalo posible de
duración manual se obtiene de la incertidumbre registrada, no de un porcentaje
de error elegido después. Una transición ausente, extra no explicada o fuera de
los brackets obliga a investigar; una coincidencia puntual no valida todo el día.
Si no se observaron todas las transiciones del día, declarar solo validación
de esos tramos, no exhaustividad diaria ni atribución exclusiva al niño.

P2/query-null y determinadas fallas de OEM pueden no ser reproducibles de forma
natural. No provocar corrupción ni fabricar esos exports para presentarlos como
físicos: conservar los tests ficticios y marcar el ensayo físico pendiente.
Los días de 23/25 horas están probados con fixtures Python; el ensayo físico solo
puede declararse aprobado si existe evidencia real en esa zona/fecha.

## Envío y reinicio en entorno aislado

P9 usa el perfil SMOKE_ONLY **no calibrado**, PMUM deshabilitado y repositorio
nuevo. El runner Windows ya comprueba kill/restart y Docker/restart con fixtures;
eso no envía datos del teléfono. Para el payload físico, levantar por separado
el servicio con ese perfil de prueba, token propio y volumen/repo separado.
Conservar el request antes de enviarlo. Obtener el resultado, reiniciar solo ese
proceso o contenedor, con el mismo perfil/repositorio, y repetir el mismo request.
No tocar los servicios entregados ni usar la URL de producción de Juanma.

El recibo completo se guarda como JSON UTF-8; no basta una captura de pantalla de
HTTP 200. Comparar `result` íntegro y `replayed`; el request_id de transporte
puede cambiar, pero no los bytes/procedencia del día. Un 409 o 503 es una falla a
revisar, no autorización para inventar una serie/record nuevo.

Comandos para P9, **solo después de revisar el origen y los ensayos anteriores**.
Primera terminal; este proceso debe conservarse para ambos envíos:

```powershell
Set-Location C:\tesis_modelo_f12_export
$estado = Join-Path $env:USERPROFILE ("Documents\modera_f12_phone_http_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $estado -ErrorAction Stop | Out-Null
Copy-Item tests/fixtures/historical_c1_smoke_only.json "$estado\profile.json" -ErrorAction Stop
$env:ANALYTICS_SERVICE_TOKEN = "phone-parity-local-smoke-only"
$env:ANALYTICS_HOST = "127.0.0.1"
$env:ANALYTICS_PORT = "8769"
$env:ANALYTICS_PMUM_ENABLED = "false"
$env:ANALYTICS_ACTIVITIES_ENABLED = "true"
$env:ANALYTICS_HISTORICAL_ENABLED = "true"
$env:ANALYTICS_HISTORICAL_CONFIG_PATH = "$estado\profile.json"
$env:ANALYTICS_HISTORICAL_REPOSITORY_PATH = "$estado\history.json"
Write-Output "Repositorio de ensayo: $estado"
.\.venv-historical\Scripts\python.exe analytics_api.py
```

Segunda terminal: `$paquete` apunta a la carpeta preparada y `$recibo` a un archivo
nuevo cuyo directorio existe. El token de ejemplo sirve solo para este ensayo
local; no reutilizarlo en backend/Compose de entrega.

```powershell
Set-Location C:\tesis_modelo_f12_export
$env:ANALYTICS_SERVICE_TOKEN = "phone-parity-local-smoke-only"
$paquete = Join-Path $env:USERPROFILE "Documents\modera_f12_phone_preparado_01"
$recibo = Join-Path $env:USERPROFILE "Documents\modera_f12_phone_receipt_01.json"
.\.venv-historical\Scripts\python.exe tools/validation/smoke_f12_prepared_payload.py `
  --phase seed --packet $paquete --receipt-file $recibo
if ($LASTEXITCODE -ne 0) { throw "No se conservó el recibo; revisar." }
```

Luego Ctrl+C en la **primera** terminal y volver a ejecutar únicamente
`.\.venv-historical\Scripts\python.exe analytics_api.py`, con las mismas variables,
perfil y repositorio. No ejecutar nuevamente el bloque que genera otra carpeta.
En la segunda terminal:

```powershell
.\.venv-historical\Scripts\python.exe tools/validation/smoke_f12_prepared_payload.py `
  --phase replay --packet $paquete --receipt-file $recibo
if ($LASTEXITCODE -ne 0) { throw "Recuperación original no aprobada." }
```

Si se perdió la respuesta/recibo del seed, repetir seed con el mismo payload
puede recuperar el recibo persistido; `seed_response_replayed` registra ese caso.
El runner Windows prueba además una terminación abrupta con fixtures. El ensayo
físico anterior prueba un reinicio explícito; no afirmar que hubo un corte abrupto
si se hizo Ctrl+C. No retirar archivos del repositorio para simular el reintento.

## Paquete de evidencia mínimo

Commit/base y diff aplicado; log de build e instalación; serial elegido y
confirmación visual; fabricante/modelo/API/build fingerprint; zona y clocks;
ventanas consultadas; permiso observado; instrumentation.log; pares originales
y reporte Kotlin; cabecera/paquete preparado/huellas; bitácora manual con brackets;
receipts antes/después de reinicio; resultado por caso PASS/FAIL/PENDING y alcance.
Archivar fuera de Git y compartir solo lo necesario, por un canal acordado.

Para aceptar esta conexión se requieren integridad y reconstrucción aprobadas
en casos reproducibles, MISSING correcto en insuficiencia y recibo durable.
La validación física/identidad debe documentarse aparte. Cualquier discrepancia
conocida impide declarar el dato apto. Esto no calibra C1 ni aprueba uso con
familias, actividades, ofertas, tarjetas o alertas.
