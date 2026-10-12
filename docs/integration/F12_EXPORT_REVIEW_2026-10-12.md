# Auditoría final y entrega revisable — export F12

## Resultado y alcance

Conexión implementada y probada con fixtures fieles al formato comprobado:
export JSON/JSONL → adaptador → preparador → v2 → API histórica → persistencia
→ recuperación/reintentos tras reinicio. No se ejecutó una captura nueva de
teléfono ni se compiló Kotlin. La prueba de formatos parte del código real;
la prueba del recorrido usa datos ficticios, no exports físicos.

Base GitHub `61e31ceaaa7a81c775d143415a00a3fd9bf55721`. Se trabajó en un snapshot
acotado de 133 archivos verificados contra sus blobs publicados, no en un clon completo del proyecto.
El commit local del snapshot no representa un nuevo commit publicado de Moderá.
Entrega como patch para un worktree/branch nuevos; sin merge/push/AWS.
Las referencias remotas se reconsultaron al cierre y siguen:

| Rama preservada | Commit |
|---|---|
| analytics-api-candidate | 6b0c55d0e43b27e8364aea90f60bad3f0a14e59b |
| analytics-historical-candidate | 26654b64c88a8034d8dc5f86d724c0af299bc546 |
| analytics-integration-handoff-candidate | 61e31ceaaa7a81c775d143415a00a3fd9bf55721 |

No se recuperaron aquí todos los mensajes originales de Juanma ni su backend.
Se usan el contexto visible y contratos/antecedentes publicados, sin afirmar
que cada decisión propuesta haya sido solicitada o aprobada por él. `api.zip`
quedó fuera de la búsqueda y del trabajo.

## Cambios concretos

| Cambio | Propósito | Verificación disponible |
|---|---|---|
| f12_export.py | Validar pares reales de 9/14 campos camelCase; proyectar y vincular hashes de bytes | Tests estrictos de asociación, tipos, conteos, orden, estados y procedencia |
| CLI desde export | Archivar originales, cabecera, proyección, payload y lineage, sin HTTP/overwrite; no-export explícito | Bytes idénticos, checksums, rechazo de salida existente/entrada inválida; ausencia declarada → MISSING sin query inventada |
| f12_bridge.py | Admitir errorMessage vacío que Kotlin puede emitir | Fixture de QUERY_RUNTIME_EXCEPTION con mensaje vacío → MISSING |
| Guard del collector | No declarar éxito si getNextEvent falla después de hasNextEvent | Auditada la ruta a RuntimeException; compilación y ejecución nativa pendientes |
| CollectorExportParityTest.kt | Consulta explícita, export fallido incluido, referencia Kotlin independiente | Código preparado; NO compilado/ejecutado en este entorno |
| Capturador ADB | Elegir serial, ejecutar harness, recuperar originales/log incluso ante fallo de paridad | Orquestación probada con respuestas ficticias; sin aparato |
| Verificador teléfono | Reconstruir desde bytes y comparar reporte/limites/estado/duración | Reportes simulados prueban aceptación y rechazo; no son ejecución Kotlin |
| Smoke de payload preparado | Ensayo local de recibo, perfil SMOKE_ONLY y replay | Guardas contra backend externo/perfil producto y recorrido HTTP local |
| Smoke/runner Windows | Agregar pares ficticios al seed/replay nativo y Docker; base exacta61 | Ejecución Linux del smoke; Windows y nueva imagen pendientes |

Los adapters matemáticos v2, parámetros/perfil C1, política de referencia,
writer lease y formato persistente no se modifican. No se conecta v3, PMUM a
actividades/alertas, ofertas automáticas ni tarjetas adultas.

## Pruebas ejecutadas en este bloque

Linux Python 3.12.14, dependencias fijadas del entorno de auditoría:

- `python -m unittest discover -s tests -t .`: **288 casos, todos PASS**, 9.874 s
  en la ejecución final; 30 casos nuevos respecto de la base 258.
- `python -m unittest test_child_choice_signals test_intervention_history_reader`:
  **15 pruebas PASS**, 0.013 s. No sumar seis scripts como si fueran unit tests.
- Seis scripts raíz ejecutados correctamente, cada uno con stdout/stderr
  archivados y modelo del repositorio en directorio de prueba aislado:
  inference, intervention_engine, intervention_history, intervention_service,
  recommendations y weekly_analysis.
- `pip check`: sin incompatibilidades.
- Uvicorn HTTP real: 5 días canónicos de fixture más 5 series aisladas de export
  ficticio —observado, vacío, permiso ausente, query-null y ausencia de export declarada—; persistencia de los
  diez recibos, kill del proceso, nuevo proceso y replay exacto de resultados,
  fechas y estado. También 409 de conflicto y 401 sin credencial.
- El smoke de paquete archivado también se ejecutó con HTTP real, usando el
  paquete ficticio generado por el CLI, kill/reinicio y recuperación de un
  recibo adicional. No se usó un paquete de teléfono.
- Paquete preparado de ejemplo generado con el CLI real; originales y huellas
  comprobados por tests. Está etiquetado como ficticio, no físico.
- Patch y formato revisados; la entrega incluye evidencia y manifiestos SHA.

Casos cubiertos por los tests nuevos: error/permisos/null, estados imposibles,
consulta vacía frente a cero con evidencia, counts/ordinales truncados o
duplicados, nombres/códigos por API, timestamps/relojes/asociación, orden no
reparado, tipos exactos/JSON estricto, metadatos mezclados, gaps, solapamientos,
eventos repetidos, estados simultáneos opuestos, startup/shutdown, límites
exclusivos, días de 23/25 horas, cabecera/identidad, cambio de bytes/procedencia,
archivo original archivado y no sobrescrito, persistencia/reinicio/retry,
verificador de teléfono y guardas del ensayo local.

El aviso de deprecación Starlette/httpx existente sigue apareciendo; las
dependencias se conservaron para no mezclar una actualización de stack con
este bloque. No es un fallo de las suites ni prueba de futuras compatibilidades.

## Lo no probado y responsabilidades externas

| Pendiente | Quién/entorno | Paso necesario |
|---|---|---|
| Windows Python3.10 y nueva imagen Docker | Matías | Aplicador aislado + runner; conservar validation_summary.json/logs |
| Compilación collector/harness | Windows/Android SDK | assembleDebug + assembleDebugAndroidTest; preservar log de fallo si ocurre |
| Captura y paridad física | Teléfono + Matías | Protocolo F12_PHONE_PARITY; originals/reporte/bitácora/recibos |
| Identidad y cola durable | Backend de Juanma | Validar autorización, IDs/namespace/asignación, conservación de payload y orden |
| Configuración C1 producto | Equipo | Continúa abierta; no inferida de SMOKE_ONLY |
| Mapeo funcional/profesional catálogo | Equipo | Antecedente previo; no resuelto por este adaptador |

Aquí no hay Docker, adb, SDK Android ni compilador Kotlin disponibles; sí hay
Java17, que no basta para declarar un build Android. Los resultados anteriores
Windows/Docker de61 son antecedentes; no se transfieren a este nuevo código.
No se cargó el modelo HU real en este recorrido; PMUM deshabilitado.

## Preguntas resueltas y decisiones indispensables

Resuelto: el formato existente es JSON/JSONL, no CSV ni la proyección fabricada
del preparador; son14 campos de evento y9 de resumen. Hay una vía ejecutable
para convertirlo y conservar procedencia. No hace falta pedir un nuevo formato
Android solo para iniciar esta prueba. Se sabe por qué el botón de última hora
y la falta de export de errores no cerraban la validación de un día.

Resuelto: consultas exitosas/contadas no cuantifican exhaustividad; metadatos de
modelo no autentican aparato; el export no trae zona/perfil/asignación. Estas
ausencias quedan explícitas, sin inventar un valor. Un reintento conserva el
payload ya preparado; reconsultar no sustituye su recibo.

Las decisiones que la evidencia no permite tomar son:

| Decisión | Alternativas | Recomendación |
|---|---|---|
| IDs y asignación backend | Mapear IDs globales existentes; crear tabla de asignación/versionada | Reutilizar IDs existentes si son únicos/aislados y representan realmente aparato→perfil; agregar asignación si falta |
| Ejecución del preparador | Job Python junto al backend; reimplementación en su stack | Job Python con cola durable/payload guardado: reduce divergencia y reutiliza las pruebas |
| Series ya procesadas por puente antiguo | Mantener recibos/versiones; migración explícita a una serie nueva | No sobreescribir ni fingir retry; mantener lo previo y acordar transición solo si ya se usó |
| Aparato compartido/zona cambiante | Serie del dispositivo; atribución individual demostrada; nueva asignación/zona | Mantener semántica de dispositivo y cambios explícitos, sin atribuir automáticamente al niño |
| Cierre de evidencia diaria | Export ya recibido; export pendiente; ausencia declarada por backend | No fabricar query ni convertir demoras en cero; fijar payload solo con estado decidido y conservarlo; cualquier corrección posterior necesita política explícita |

No son bloqueos para ejecutar los tests locales ficticios ni para probar el
formato. Sí impiden declarar integración de producto/captura física cerrada.
Las decisiones de C1 y catálogo permanecen pendientes del equipo, sin agregar
ahora una política de alertas, ofertas o tarjetas.

## Feedback acumulativo y cautelas corregidas

Se corrigió el conteo inicial de campos —14, no15— antes de definir el adaptador.
Se distinguió prueba del parser de prueba Kotlin/Android; un reporte simulado
nunca se rotula como validación física. Se preservó el resultado original en
retries y se ligaron también los campos extra del export a su procedencia.
Se evitó aceptar silenciosamente un query truncado, ordenar un export inválido,
deduplicar crudo o convertir permiso/ausencia en cero.
El mensaje actualizado para Juanma distingue publicado/nuevo pendiente, con
enlaces al commit existente y sin inventar URL/commit de la ampliación.

## Validacion posterior Windows y Docker ? 2026-10-12

Ejecucion realizada por Matias y revisada mediante las salidas de consola y validation_summary.json compartidos. Este bloque actualiza los pendientes Windows/Docker indicados en las secciones anteriores; Android y telefono siguen pendientes.

- Rama: f12-export-integration-candidate; base 61e31ce.
- Python 3.10.0; entorno separado; pip check aprobado.
- tests/: 288 casos en 26.989 segundos; 287 aprobados y una omision consistente con la prueba exclusiva de POSIX.
- Raiz: 15 pruebas aprobadas en 0.237 segundos.
- Seis scripts heredados ejecutados correctamente.
- HTTP Windows: seed y recuperacion tras terminar/reiniciar el proceso, aprobados.
- Docker: Compose, build, volumen persistente, seed, reinicio, replay, identidad y healthcheck aprobados.
- Archivos del manifiesto comprobados antes de esta actualizacion.
- Datos ficticios, perfil no calibrado y PMUM deshabilitado.

Evidencia local: `C:\Users\matum\Documents\modera_historical_smoke_20261012-095702-48d0e029`.

Manifiesto probado: `13066a14cd3a28b8be8ace121df7a65966faef5c8673e795e65f7790cfb9f6de`.

Imagen comprobada: `sha256:8a8dac4da99f67488166b1ce13fade44e4fce1b6303c450838154ef4d3910362`.

Volumen conservado: `modera-historical-smoke-20261012-095702-48d0e029`.

No se compilo ni ejecuto Android; no se verificaron telefono fisico, backend de Juanma ni AWS. No se calibro C1.
