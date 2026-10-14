# Importar y comprobar desde la terminal PowerShell de VS Code

Descargar `MODERA_COORDINADOR_INFANTIL_2026-10-14.bundle` en Descargas. No abrir
CMD; ejecutar en la terminal PowerShell. Conserva las carpetas anteriores y crea
otra. El bundle requiere e43695a, ya importado en `C:\tesis_modelo`.

```powershell
$childBundle = Join-Path $env:USERPROFILE 'Downloads\MODERA_COORDINADOR_INFANTIL_2026-10-14.bundle'
git -C C:\tesis_modelo bundle verify "$childBundle"
if ($LASTEXITCODE -ne 0) { throw 'Bundle no verificado.' }
git -C C:\tesis_modelo bundle list-heads "$childBundle"
git -C C:\tesis_modelo fetch "$childBundle" HEAD:refs/heads/child-offer-coordinator-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se importó el candidato.' }
git -C C:\tesis_modelo worktree add --detach C:\tesis_coordinador_infantil_v1 child-offer-coordinator-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se creó la carpeta nueva.' }
Set-Location C:\tesis_coordinador_infantil_v1
git rev-parse HEAD
git merge-base --is-ancestor 0d806c21e57ec3153031a78e721a2d2a13113114 HEAD
if ($LASTEXITCODE -ne 0) { throw 'No contiene el código comprobado.' }
$childPython = 'C:\tesis_mensajes_adulto_v1\.venv\Scripts\python.exe'
& $childPython -m pytest -q tests/test_child_offer_coordinator.py tests/test_integration_closure.py::ConditionsCombinationsTests::test_review_matrix_covers_exact_catalog_without_implying_approval
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas focalizadas.' }
& $childPython tools/validation/verify_child_offer_coordinator.py --output coordinador_infantil_ficticio_windows.json
if ($LASTEXITCODE -ne 0) { throw 'Falló el ensayo ficticio.' }
```

La prueba focalizada debe aprobar 46 casos. El ensayo anuncia cinco escenarios
ficticios. El JSON no se sobrescribe: si ya existe de una corrida anterior, usar
un nombre nuevo para conservar la evidencia.

Después, comprobar regresión del candidato, sin publicarlo:

```powershell
& $childPython -m pytest -q tests test_intervention_history.py test_intervention_service.py test_intervention_engine.py test_intervention_history_reader.py test_recommendations.py test_child_choice_signals.py test_weekly_analysis.py test_inference.py --junitxml=coordinador_infantil_windows.xml
```

El caso omitido previamente en Windows puede seguir omitido; no asumir que su
conteo debe coincidir exactamente con Linux. Conservar la salida y el XML. La
advertencia heredada Starlette/httpx no convierte un PASS en fallo. No actualizar
dependencias sólo para ocultarla.
