# Ensayo integrado ficticio dentro de analytics

13/10/2026. Base: `adult-messages-bounded-audit-candidate`,
`7b7d0f50aa419d0ee8642bf825f6db8330422797`. Consultada mediante
`git ls-remote origin refs/heads/adult-messages-bounded-audit-candidate`:
la referencia publicada coincide. Rama nueva: `adult-messages-integrated-path-candidate`.
Las ramas anteriores se conservan. Este bloque no publica, integra ni despliega.

## Resultado y cambios

No se encontraron defectos demostrados en el recorrido revisado. Se agregaron
un ensayo reproducible y siete pruebas de aceptación; no se modificó código
de producción, parámetros, dependencias, C1, PMUM ni actividades.

El ensayo usa el productor ficticio existente `synthetic_export`,
`prepare_android_export`, el CLI `build_historical_request_from_export.py`,
`load_packet` y los endpoints reales mediante `TestClient`. No reimplementa
la reconstrucción diaria, el cálculo C1 ni las reglas de mensajes.
Un día de cada caso atraviesa también el CLI y la verificación de su manifiesto;
los restantes usan directamente el mismo adaptador publicado.

La coordinación entre endpoints y el armado del payload diario de mensajes
pertenecen al harness de prueba. Esto comprueba compatibilidad de contratos
dentro de analytics; no acredita que el backend ya coordine automáticamente
ese recorrido. Los identificadores de C1 se conservan como trazabilidad en el
recibo de mensajes; C1 no determina la apertura de la tarjeta.

## Condiciones controladas y casos

Toda la evidencia del ensayo es ficticia. Cada caso tiene perfil, dispositivo,
asignación, serie y almacenes propios. Se generan consultas cerradas en zona
Buenos Aires, con estado OFF conocido antes de la jornada y transiciones
ON/OFF exactas. Un oráculo coteja límites UTC, cantidad de eventos y duración
contra el plan del fixture antes de declarar `quality_verified` para el ensayo.
La asignación verificada y ausencia de teléfono compartido son condiciones
controladas ficticias, no verificaciones de una familia.

`coverage.value` permanece `null`; las banderas de cobertura cuantificada,
captura física e identidad física verificada permanecen falsas. Un preparador
que termine correctamente no concede calidad. El cuarto caso lo demuestra.

Plan: primer día 2026-01-05; patrón semanal de ruido en minutos
`[0, 2, -2, 4, -4, 1, -1]`, con media ponderada semanal cero.
No se cambia ningún umbral para producir estos resultados.

| Caso ficticio | Secuencia base por períodos de 14 días | Evaluaciones de mensajes | Versiones |
|---|---|---|---|
| Aumento y retorno | 100 → 140 → 100 min/día | ACTIVE → INCONCLUSIVE → RESOLVED | 1, 2, 3; una tarjeta |
| Disminución y retorno | 140 → 100 → 140 min/día | ACTIVE → INCONCLUSIVE → RESOLVED | 1, 2, 3; una tarjeta |
| Día faltante | 100 → 140; permiso ficticio ausente el 15/01 | INSUFFICIENT_DATA | Ninguna tarjeta |
| Calidad retenida | 100 → 140; registro observado del 25/01 sin calidad concedida | INSUFFICIENT_DATA | Ninguna tarjeta |

Las evaluaciones de los dos primeros casos ocurren el 02/02, 09/02 y 16/02.
Se verifica la referencia congelada 05/01–18/01 y la apertura 19/01–01/02.
Las ventanas recientes avanzan a 26/01–08/02 y 02/02–15/02, con diferencias
de `+40, +20, 0` o `-40, -20, 0` minutos frente a la misma referencia.
Las actualizaciones envían sólo los siete días nuevos: las ventanas anteriores
se recuperan del estado persistido. Cada DTO conserva serie, perfil, zona,
fecha, texto explicativo y recomendación; la entrega sigue siendo candidata.

El día faltante se representa como MISSING con valor `null`, C1 se abstiene
y conserva el estado previo. El registro sin calidad concedida sigue OBSERVED
en la representación y llega a C1, pero impide una tarjeta de mensajes.

## Reinicio, originales y trazabilidad

Se recrean la aplicación y sus runtimes antes de agregar los días 29 y 36
de ambos episodios. Se reintentan sus últimos recibos antes de continuar:
cuatro reinicios de continuidad y cuatro reintentos adicionales de cada servicio.
Después de finalizar cada caso se recrean nuevamente los runtimes y se
reintentan todos los recibos originales: 140 históricos y ocho de mensajes.

Se cotejan resultados completos, salvo `replayed=true`, bytes del repositorio
C1 y todos los registros de config, estados, recibos, evaluaciones, revisiones
y tarjetas de SQLite. Los reintentos no modifican ninguno. El historial DTO
conserva exactamente las versiones originales de las respuestas; no duplica
tarjetas ni versiones. No se ensayó reinicio del sistema operativo o caída de
un proceso ni tráfico por socket: se recrean runtimes en el mismo proceso.

Cada traza conserva binding, fecha, hashes SHA256 de los dos archivos originales,
identificador de consulta, representación, recibo C1 original y fila diaria del
mensaje. El recibo de mensajes enlaza esos `evaluation_id` y su `card_id/version`
con el historial. Se comprueba que las cuatro series y las 140 representaciones
sean distintas y que fechas, límites y valores se mantengan entre etapas.
Los UUID/fechas internas de recibos C1 pueden variar entre ejecuciones nuevas;
se exige su conservación exacta dentro de cada ejecución y su replay.

## Pruebas ejecutadas

- Linux, Python 3.12.14: suite de regresión existente y siete tests nuevos,
  **385 aprobados, 190 subtests y una advertencia** en 15,95 s.
- Focalizadas con `LC_ALL=C`, `PYTHONCOERCECLOCALE=0`, `PYTHONUTF8=0`
  y `-X utf8=0`: **48 aprobadas, 10 subtests y una advertencia**.
  Incluyen la comprobación de lectura UTF-8 del catálogo ya corregida.
- CLI del ensayo: **PASS**; 140 primeras evaluaciones históricas, ocho de
  mensajes, dos tarjetas con tres versiones cada una y dos casos sin tarjetas.

La advertencia es la deprecación ya existente de Starlette/httpx. No se cambia
la dependencia. Los subtests no se suman como tests independientes.
Estos resultados corresponden a los archivos de este bloque. Las pruebas
previas de 7b7d0f5 no se atribuyen a este candidato. Windows se comprobó después
por Matías sobre `1fd977c`: siete tests integrados, CLI PASS y regresión con
384 aprobados, uno omitido, 190 subtests y una advertencia. Se conserva su
[evidencia documental](../integration/evidence/windows_integrated_2026-10-13/validation_summary.json),
basada en consola recibida; el XML Windows no fue aportado aquí.
Los datos generados por tests de raíz se restauran
y no se incluyen en el commit.

C1 se ejecuta con el fixture existente `smoke-only-not-calibrated`, sin modificarlo.
El ensayo acredita recorrido, persistencia, contratos y reintentos con ese perfil,
no calibración, eficacia ni calidad de captura real. PMUM y actividades están
deshabilitados durante el ensayo. No se ejecutó otro benchmark amplio.

## Verificación en PowerShell de VS Code

Descargar el bundle de este bloque. Verificar su SHA mostrado en la entrega,
importarlo en una rama nueva y usar un worktree separado. Reutilizar el entorno
de pruebas existente; conservar el checkout y los archivos sin seguimiento de
`C:\tesis_modelo`. Los comandos sólo agregan la rama y el worktree indicados.

```powershell
$integratedBundle = Join-Path $env:USERPROFILE 'Downloads\MODERA_ANALYTICS_RECORRIDO_INTEGRADO_2026-10-13.bundle'
git -C C:\tesis_modelo bundle verify "$integratedBundle"
git -C C:\tesis_modelo bundle list-heads "$integratedBundle"
git -C C:\tesis_modelo fetch "$integratedBundle" HEAD:refs/heads/adult-messages-integrated-path-candidate
git -C C:\tesis_modelo worktree add --detach C:\tesis_mensajes_integrado_v1 adult-messages-integrated-path-candidate
Set-Location C:\tesis_mensajes_integrado_v1
git rev-parse HEAD
$analyticsPython = 'C:\tesis_mensajes_adulto_v1\.venv\Scripts\python.exe'
& $analyticsPython -m pytest -q tests/test_analytics_integrated_path.py tests/test_adult_messages_audit.py tests/test_adult_messages.py tests/test_integration_closure.py::ConditionsCombinationsTests::test_review_matrix_covers_exact_catalog_without_implying_approval --junitxml=recorrido_integrado_windows_focal.xml
& $analyticsPython tools/validation/verify_analytics_integrated_path.py --output-dir recorrido_integrado_ficticio_windows
```

El directorio del ensayo debe ser nuevo; se rechaza uno existente para evitar
sobrescribir evidencia. Para repetirlo, elegir otro nombre. No publicar ni hacer
merge. Si la comprobación focalizada y el CLI pasan, ejecutar la regresión:

```powershell
& $analyticsPython -m pytest -q tests test_intervention_history.py test_intervention_service.py test_intervention_engine.py test_recommendations.py test_child_choice_signals.py test_weekly_analysis.py test_inference.py --junitxml=recorrido_integrado_windows.xml
```

Queda cerrado el bloque interno dentro del alcance probado. Captura física,
asignación real, calidad de datos reales, coordinación backend y pantalla del
adulto requieren la integración y validación correspondientes; no se trabajó
en backend o Android de Juanma ni en redacción de tesis.
