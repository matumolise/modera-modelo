# Incorporación y comprobación en PowerShell de VS Code

Este bundle agrega el cambio infantil y los cierres documentales sobre el
candidato de código ya probado. Conserva las ramas anteriores. No realiza push,
merge ni despliegue. El padre requerido del bundle es `7b7d0f5`, ya importado.
No editar el checkout original con experiments/ o patches sin seguimiento.

Descargar el bundle de la entrega en Downloads. Verificar su HEAD contra el SHA
mostrado en el resultado final y avanzar sólo si coincide y cada comando termina
sin error. Carpeta y rama nuevas:

```powershell
$ownClosureBundle = Join-Path $env:USERPROFILE 'Downloads\MODERA_CIERRE_PROPIO_2026-10-14.bundle'
git -C C:\tesis_modelo bundle verify "$ownClosureBundle"
if ($LASTEXITCODE -ne 0) { throw 'Bundle no verificado.' }
git -C C:\tesis_modelo bundle list-heads "$ownClosureBundle"
git -C C:\tesis_modelo fetch "$ownClosureBundle" HEAD:refs/heads/modera-own-scope-closure-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se importó el candidato.' }
git -C C:\tesis_modelo worktree add --detach C:\tesis_cierre_propio_v1 modera-own-scope-closure-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se creó el nuevo worktree.' }
Set-Location C:\tesis_cierre_propio_v1
git rev-parse HEAD
$closurePython = 'C:\tesis_mensajes_adulto_v1\.venv\Scripts\python.exe'
& $closurePython -m pytest -q tests/test_child_offer_closure.py test_intervention_history.py test_intervention_service.py test_intervention_history_reader.py test_child_choice_signals.py --junitxml=ofertas_cierre_windows.xml
```

Si pasa, la regresión necesaria de este nuevo código:

```powershell
& $closurePython -m pytest -q tests test_intervention_history.py test_intervention_service.py test_intervention_engine.py test_intervention_history_reader.py test_recommendations.py test_child_choice_signals.py test_weekly_analysis.py test_inference.py --junitxml=cierre_propio_windows.xml
```

No hace falta repetir el benchmark ni entrenar un modelo. Los scripts de raíz
pueden generar datos ficticios en este nuevo worktree. No son datos de familias.
La reserva `.writer.lock` del escritor se conserva; no borrarla como reparación.

Si se localizan los originales HU confiables, el verificador existente sólo los
lee; este comando NO acredita entrenamiento final ni lo ejecuta:

```powershell
# Elegir la carpeta real que contiene los dos originales; no una copia sintética.
$originalHuFolder = Read-Host 'Carpeta con HU joblib y manifiesto originales'
& $closurePython tools/validation/verify_pmum_artifact_v1.py --model-dir "$originalHuFolder" --output hu_original_cotejo_20261014.json
```

Conservar el reporte y los originales; el output debe ser nuevo. Su PASS no
reemplaza el registro fuente→ajuste→artefacto que falta recuperar.
