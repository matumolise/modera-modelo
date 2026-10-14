# Incorporar cierre documental de privacidad

Desde PowerShell de VS Code, con el bundle descargado en Descargas. No hay cambio
runtime ni hace falta repetir suites, benchmark, entrenamiento o Docker.

```powershell
$privacyBundle = Join-Path $env:USERPROFILE 'Downloads\MODERA_PRIVACIDAD_CIERRE_PROPIO_2026-10-14.bundle'
git -C C:\tesis_modelo bundle verify "$privacyBundle"
if ($LASTEXITCODE -ne 0) { throw 'Bundle no verificado.' }
git -C C:\tesis_modelo bundle list-heads "$privacyBundle"
git -C C:\tesis_modelo fetch "$privacyBundle" HEAD:refs/heads/privacy-own-scope-closure-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se importó el cierre de privacidad.' }
git -C C:\tesis_modelo worktree add --detach C:\tesis_privacidad_cierre_v1 privacy-own-scope-closure-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se creó la carpeta nueva.' }
Set-Location C:\tesis_privacidad_cierre_v1
git rev-parse HEAD
git status --short
```

Abrir `docs/own_closure/PRIVACY_SCOPE_CLOSURE_2026-10-14.md` y
`docs/own_closure/CURRENT_CLOSURE_MATRIX_2026-10-14.md`. Las carpetas/ramas anteriores
se conservan. No hay comandos de borrado o purga, ni se publica esta rama.
