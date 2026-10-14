# Incorporar cierre C1 desde PowerShell de VS Code

Sólo documentación/evidencia. No hay cambio runtime ni es necesario repetir
suite, benchmark, Docker o entrenamiento. La comprobación siguiente lee el
perfil existente; no inicia el servicio ni avanza C1.

Descargar `MODERA_C1_CONFIGURACION_CIERRE_2026-10-14.bundle` en Descargas:

```powershell
$c1ClosureBundle = Join-Path $env:USERPROFILE 'Downloads\MODERA_C1_CONFIGURACION_CIERRE_2026-10-14.bundle'
git -C C:\tesis_modelo bundle verify "$c1ClosureBundle"
if ($LASTEXITCODE -ne 0) { throw 'Bundle no verificado.' }
git -C C:\tesis_modelo bundle list-heads "$c1ClosureBundle"
git -C C:\tesis_modelo fetch "$c1ClosureBundle" HEAD:refs/heads/c1-configuration-closure-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se importó el cierre C1.' }
git -C C:\tesis_modelo worktree add --detach C:\tesis_c1_configuracion_v1 c1-configuration-closure-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se creó la carpeta nueva.' }
Set-Location C:\tesis_c1_configuracion_v1
git rev-parse HEAD
$c1Python = 'C:\tesis_mensajes_adulto_v1\.venv\Scripts\python.exe'
$c1Fingerprint = & $c1Python -c "from pathlib import Path; from analytics_service.historical_config import HistoricalProfile; print(HistoricalProfile.load(Path('tests/fixtures/historical_c1_smoke_only.json')).fingerprint)"
if ($LASTEXITCODE -ne 0) { throw 'No se pudo leer el perfil.' }
if ($c1Fingerprint -ne 'ced67439a2bf7c4bc4a6f4fc6bec805b404f14c662a927464d026d75d8f46466') { throw 'Huella C1 distinta del perfil conservado.' }
Write-Output $c1Fingerprint
```

La carpeta nueva conserva las anteriores. El perfil continúa llamándose
smoke-only-not-calibrated; no reemplazar configuraciones reales o borrar stores
para hacerlo pasar como otro perfil. No publicar todavía.

Estado vigente: `docs/own_closure/C1_CONFIGURATION_CLOSURE_2026-10-14.md`.
