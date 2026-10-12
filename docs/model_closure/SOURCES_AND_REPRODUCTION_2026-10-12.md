# Fuentes, archivos y reproducción

Estado: instrucciones del candidato y del paquete revisado. La reauditoría final reprodujo nuevamente PMUM OOF y C2 completos, contrastó conteos por SAV, leyó pasajes específicos del PDF y comprobó fuentes primarias dentro del alcance indicado. La carga del HU original y el recorrido Windows/Docker fueron ejecutados por Matías con PASS; el resumen recibido y su procedencia están en [cierre Windows/Docker](WINDOWS_DOCKER_CLOSURE_2026-10-12.md). No se declara ejecución Windows desde Linux ni validación externa científica.

## Fuentes primarias y alcance de lectura

- Domoff et al., artículo original PMUM: https://sarahdomoff.com/wp-content/uploads/2019/12/Development_and_validation_of_.pdf . Se leyó la copia de autora recuperada. Describe una medida parental y su desarrollo, no valida el modelo HU v1.
- NIST CUSUM: https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm . Se leyó la sección sobre referencia y parámetros; no se trasladan sus propiedades al candidato sin justificar supuestos.
- Baselines: https://scikit-learn.org/1.7/modules/generated/sklearn.dummy.DummyRegressor.html .
- Registro HU previsto: https://zenodo.org/records/21802447 . Su consulta web actual estuvo bloqueada; se utilizó el ZIP proporcionado con hash, no una licencia/metadatos del registro recién comprobados.
- E50: PDF accesible SHA861169…; secciones seleccionadas descritas en el informe. No se afirma haber leído las 147 páginas completas.
- Antecedentes HU/DE y auditoría 07/10 leídos completos; no constituyen nuevas aprobaciones.

En la reauditoría del 12/10 se abrieron de nuevo la copia de autora PMUM y las secciones NIST y DummyRegressor enlazadas. El artículo original describe evaluación parental, nueve ítems de la forma corta, edades 4–11 y límites de validación clínica/cortes; no valida la regresión HU ni su alcance argentino. La página NIST describe un diseño CUSUM con referencia y supuestos especificados; no avala la adaptación mediana/MAD del candidato. Zenodo volvió a fallar al consultarse: no se adjudican autores/licencia nuevos al ZIP por ese intento.

El paquete revisado entregado no redistribuye microdatos HU/CSV, binarios joblib ni PDFs originales. Conserva resultados agregados y trazabilidad. Se excluye api.zip. El inventario de blobs comprobado identifica el alcance parcial de archivos recuperados.

## Reproducir evaluación (optativo, fuente necesaria)

Con las dependencias del candidato:
```powershell
.\.venv-historical\Scripts\python.exe tools/validation/audit_pmum_methodology.py --source-zip RUTA_ZIP_HU --output NUEVO_PMUM_OOF.json
```
La fuente debe tener el SHA registrado. Ajusta modelos de evaluación en memoria dentro de los pliegues y compara media, mediana, alpha fijo y selección interna. No guarda ni reemplaza un artefacto entrenado. outer=KFold(5, shuffle=True, seed1027); inner=KFold(4, shuffle=True, seed20261007+fold); alpha=[1,10,100]. La selección interna usa MAE sin clip; la evaluación externa aplica clip 1–5, conforme al análisis anterior. Los resultados describen ese diseño, no una validación independiente nueva.

Las huellas de índices corresponden a posiciones de los 806 registros completos devueltos por el loader y a su orden; no son identificadores de personas ni hashes del archivo bruto por fila. El reporte conserva runtime científico 1.7.2/2.2.6/1.15.3/1.5.3. El antecedente del 07/10 usó scikit-learn 1.8.0; las condiciones de esta reproducción quedan registradas explícitamente.

Para reproducir C2 con la fuente correspondiente, desde la raíz del worktree:
```powershell
.\.venv-historical\Scripts\python.exe -m tools.f12.run_f12c_semisynthetic RUTA_MEDIATICINO_CSV --output NUEVO_C2.json
```
Se usa invocación como módulo para resolver el paquete historical. La fecha base del runner es artificial y los offsets cuentan registros. En la reauditoría final ambos JSON nuevos coincidieron exactamente con sus antecedentes; no se guardó un modelo entrenado de entrega.

## Verificar originales HU v1 (ejecutado; comando disponible para reproducción)

```powershell
.\.venv-historical\Scripts\python.exe tools/validation/verify_pmum_artifact_v1.py --model-dir "$env:USERPROFILE\Documents\modera_pmum_experimental" --output NUEVO_ARTEFACTO_AUDIT.json
```
El aplicador del paquete crea un worktree/rama nuevos y comprueba las cinco ramas. El validador incorpora la comprobación de originales cuando existen ambos, con el hash registrado antes de joblib. Conserva modelo/manifiesto y registra warnings, versiones, categorías y dominio numérico. Al construir CachedPmum verifica indirectamente 2.6959; HTTP lo comprueba por separado en Windows y, cuando Docker se ejecuta, montando ambos originales en sólo lectura. Si faltan ambos, registra PENDING; si hay sólo uno o no coinciden, falla sin entrenar. No reemplaza el modelo ni instala versiones alternativas para ocultar incompatibilidades.

## Auditar C1

Usar `audit_c1_repository.py` contra snapshot estable y perfil correspondiente, con salida nueva. Reconstruye mediana/MAD, evaluación, estado y emisor con IDs/fechas anteriores; compara y no escribe fuentes. Los archivos HTTP recuperados son ficticios. El resumen Windows recibido registra PASS para windows_c1_snapshot_audit y docker_c1_snapshot_audit con los cambios nuevos. Registra también el snapshot posterior al recorrido PMUM y la conservación de bytes históricos. Los snapshots/logs completos permanecen en el entorno de Matías; no se afirma haberlos inspeccionado individualmente aquí.

## Pruebas disponibles

```powershell
.\.venv-historical\Scripts\python.exe -m unittest discover -s tests -t .
.\.venv-historical\Scripts\python.exe -m unittest test_child_choice_signals test_intervention_history_reader
```
El validador prepara un entorno separado y ejecuta seis scripts heredados aislados, HTTP nativo, reinicio/replay, auditoría C1 y Docker. Los scripts no se suman a casos unitarios. Conserva evidencia y volumen sin crear commits/push. Si falta el original o se omite Docker, su resumen indica PASS_WITH_PENDING_EVIDENCE, no cierre total; historical_fixture_only permanece true aunque se cargue HU real. Esta descripción no acredita ejecución Windows/Docker desde el entorno Linux de la reauditoría.
