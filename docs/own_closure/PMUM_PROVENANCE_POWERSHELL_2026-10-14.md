# Incorporar cierre PMUM desde PowerShell de VS Code

Este paquete contiene documentación, evidencia y una herramienta offline de
lectura. No cambia modelo o código runtime. **No hace falta reentrenar ni repetir
las suites o el verificador HU que ya pasó en Windows.**

Descargar `MODERA_PMUM_TRAZABILIDAD_2026-10-14.bundle` en Descargas y ejecutar:

```powershell
$pmumClosureBundle = Join-Path $env:USERPROFILE 'Downloads\MODERA_PMUM_TRAZABILIDAD_2026-10-14.bundle'
git -C C:\tesis_modelo bundle verify "$pmumClosureBundle"
if ($LASTEXITCODE -ne 0) { throw 'Bundle no verificado.' }
git -C C:\tesis_modelo bundle list-heads "$pmumClosureBundle"
git -C C:\tesis_modelo fetch "$pmumClosureBundle" HEAD:refs/heads/pmum-provenance-closure-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se importó el cierre.' }
git -C C:\tesis_modelo worktree add --detach C:\tesis_pmum_trazabilidad_v1 pmum-provenance-closure-candidate
if ($LASTEXITCODE -ne 0) { throw 'No se creó la carpeta nueva.' }
Set-Location C:\tesis_pmum_trazabilidad_v1
git rev-parse HEAD
$recoveredManifest = Get-FileHash .\docs\own_closure\evidence\pmum_2026-10-14\original_manifest_recovered.json -Algorithm SHA256
if ($recoveredManifest.Hash.ToLowerInvariant() -ne '98f2952c2bf0c2e4565fe86cadd0fe28faeae4ef4600a0d36c09983779495b09') { throw 'Manifiesto recuperado con bytes distintos.' }
$savedEvaluation = Get-FileHash .\docs\own_closure\evidence\pmum_2026-10-14\PMUM_OOF_HIGH_REAUDIT_original.json -Algorithm SHA256
if ($savedEvaluation.Hash.ToLowerInvariant() -ne 'f0eb942342857259651dc17ae7d728689eb75329cc3b1403df2f59352e1630f9') { throw 'Evaluación histórica con bytes distintos.' }
```

Los dos hashes comprueban que Git conservó los bytes originales en Windows.
No sobrescribir originales HU de Documents con estos archivos ni publicar aún.
Abrir `docs/own_closure/PMUM_PROVENANCE_CLOSURE_2026-10-14.md` para el estado vigente.

La herramienta offline requiere el ZIP fuente registrado, el paquete revisado
12/10 y pyreadstat1.3.6 para inspeccionar SAV. Su comando/alcance están en el propio
script; ya se ejecutó aquí. No es otro benchmark ni una instrucción de fit.
