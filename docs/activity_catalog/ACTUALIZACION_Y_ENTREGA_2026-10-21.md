# Actualización del catálogo para integración

Base: `04f1e3a9076d914bccad49d356184d8b7b45ec13`.
Rama: `activity-catalog-cecilia-review-candidate`.
Estado: catálogo provisional. Primera devolución profesional recibida y consignas
revisadas. Segunda devolución pendiente. No es aprobación clínica ni prueba de
comprensión con niños. No se modifica el PDF entregado ni código de backend o Android.

## Cambios incluidos

- Las 18 actividades usan los títulos, materiales y consignas del Word
  `MODERA_ACTIVIDADES_SEGUNDA_REVISION_2026-10-19.docx`. La correspondencia, su
  SHA-256 y el texto común están en `REVISION_2026-10-21.json` de esta carpeta.
- Se conservan 16 identificadores. Se retiran de nuevas sugerencias
  `social_help_01` (Ayudá con algo) y `quiet_prepare_01` (Prepará algo para mañana).
  Sus sustitutas son `social_create_together_01` (Inventen algo entre dos) y
  `quiet_story_ending_01` (Inventá otro final). No son alias ni equivalencias.
- Las ideas 19 y 20 siguen fuera del catálogo. La 21 también queda fuera.
- Se conserva el esquema de actividad y HTTP. Materiales y pasos están dentro de
  `description`, con saltos de línea. No se agregan campos obligatorios, endpoints,
  reproductor, temporizador, audio guiado ni registro de realización.
- La huella del catálogo cambia automáticamente. El código y la huella del selector
  permanecen iguales. Una selección nueva puede cambiar por el catálogo y la semilla
  que incluye su huella. No se ajustaron pesos para obtener mejores resultados.

## Decisiones de ingeniería

| Decisión | Motivo y alcance |
| --- | --- |
| Mantener IDs en las 16 reformulaciones | Permiten seguir identificando la misma propuesta. Los recibos conservan su texto y versión originales. No se reescribe el historial. |
| Nuevos IDs para las dos sustituciones | Evita atribuir una selección de ayuda doméstica a creación conjunta, o preparación de objetos a imaginación de otro final. |
| Aceptar IDs retirados como antecedentes y exclusiones | El coordinador y el backend pueden conservarlos. Aceptarlos no permite volver a sugerirlos. Los IDs desconocidos siguen rechazándose. |
| Conservar intereses históricos `helping`, `organization`, `writing` como entradas | Evita errores al leer preferencias previas. No se trasladan a las nuevas actividades ni se prometen coincidencias si ya no hay una actividad con esa etiqueta. |
| Actividad 7: intereses `stories`, `creative` | Ahora permite imaginar o contar. Se retiran las etiquetas `writing` y `drawing` porque no son necesarias para la consigna. |
| Actividad 15: social, creatividad, historias y dibujo | Son variantes explícitas de creación por turnos. Sigue requiriendo otra persona. |
| Actividad 17: historias y creatividad, nivel calmado | Consigna de imaginación sin materiales ni otra persona obligatoria. Disponible voluntariamente, en pausa general y antes de dormir, según la propuesta. No acredita un efecto sobre el sueño. |
| Retirar bedtime de las actividades 6 y 7 | El Word las propone solo para pausa. Se limita el contexto de nuevas sugerencias y se conserva la actividad 18 para dibujo antes de dormir. Es una decisión provisional de catálogo, no dictamen profesional. |
| Conservar niveles de movimiento y posible dispositivo en baile | Permitir estar sentado no demuestra que todas las variantes tengan baja intensidad o sean compatibles con una condición. La música puede reproducirse desde el teléfono, sin que Analytics la controle. |
| Conservar contratos y políticas | Los cambios se limitan al contenido y a compatibilidad con IDs históricos. No cambia C1, PMUM, ventanas adultas, tiempos ni cuotas del coordinador. |

Los materiales se explican al niño. No hay comprobación automática de que estén
presentes. La persona disponible tampoco se infiere por mencionar una actividad.

## Condiciones: comportamiento comprobado, sin mapeos nuevos

`/v1/activities/eligibility` sigue distinguiendo:

- `known` con `conditions: ["none"]`: elegibilidad conocida y filtros vacíos.
- `unknown`: no se interpreta como ninguna dificultad.
- Cualquier condición distinta de `none`: `eligibility_state: "unknown"`,
  `reason: "functional_mapping_required"` y preguntas de seguimiento. Estas
  etiquetas NO se convierten por sí solas en exclusiones seguras.

El selector aplica filtros explícitos que recibe. Este cambio no implementa el
mapeo profesional pendiente del formulario a esos filtros. La matriz funcional
actualizada conserva `automatic_condition_to_filter_mapping: false` y
`clinical_safety_validated: false`. No utilizar sus letras E/V/N como un mapa
clínico. Si backend ya usa un mapeo propio, hay que cotejarlo y actualizar sus
referencias a los nuevos IDs, no asumir que es equivalente al servicio.

Por eso el texto de pantalla «se usa para filtrar actividades» describe la
finalidad del dato, pero no prueba que las opciones cerradas ya resuelvan todos
los filtros. Cuando la API devuelve elegibilidad desconocida, mostrar una salida
comprensible y conservar la abstención. No sustituirla por `{}`.

## Qué necesita Juanma

1. Actualizar y reconstruir Analytics desde la versión entregada. Conservar el
   token y el volumen. No borrar datos, bases, recibos ni marcas de inicialización.
   No usar `down -v` ni inicializar otra base para ocultar errores de arranque.
2. Comprobar `/health`: catálogo nuevo provisional, PMUM aún deshabilitado y C1
   con su mismo perfil SMOKE_ONLY. Las versiones de HTTP permanecen iguales.
3. Mostrar `title` y `description` recibidos. Conservar saltos de línea. Mostrar
   materiales y pasos antes de empezar, con espacio o desplazamiento suficiente,
   y permitir volver a leer la consigna. No truncarla a una sola línea.
4. Si hay catálogo, IDs, títulos o listas de intereses fijos en backend/Android,
   actualizarlos. No sustituir IDs en selecciones ya guardadas. Calcular filtros
   de nuevas sugerencias contra el catálogo actual y revisar cualquier regla
   propia de exclusiones. Un ID retirado aceptado no es un alias de su sustituta.
5. Incorporar el texto común del Word en el recorrido infantil, sin duplicarlo en
   cada tarjeta: «Elegí algo que tengas ganas de hacer. Mirá qué necesitás y cómo
   empezar. Después dejá el celular a un lado para hacer la actividad. Si ahora
   no querés, podés seguir sin elegir».
6. Mantener la excepción de baile: puede poner música y apoyar el teléfono. No se
   requiere desarrollar reproducción musical ni guía de audio para este cambio.
7. Conservar los eventos existentes: generación, entrega y selección son distintos.
   Leer, empezar, seleccionar o cerrar una pantalla no demuestra realización.
8. Probar selección voluntaria y automática con perfiles ficticios separados,
   historial anterior, un reinicio y reintentos. No presentar la prueba como uso
   validado con niños ni como comprobación de captura real.

Una oferta previa conserva la copia de contenido que recibió. Su reintento
recupera el recibo original, aun después de actualizar. No debe usarse replay
como permiso para mostrar otra vez. Una evaluación nueva no vuelve a presentar
una oferta pendiente que contenga IDs retirados o incompatibles con su contexto
actual: devuelve `frozen_offer_no_longer_eligible`. Se conserva el tratamiento
existente de vencimiento y reconciliación, sin crear una oferta sustituta por
fuera de las reglas. Una respuesta válida a una oferta antigua ya entregada se
registra contra sus IDs originales.

El registro heredado de respuestas también acepta esos dos IDs para conservar
la respuesta a una oferta anterior. La creación de ofertas nuevas continúa
validando exclusivamente el catálogo activo. Los tests guardan la oferta previa,
registran y reintentan su respuesta y comprueban que no se alteró el original.

## Comprobación en PowerShell de VS Code

Después de importar el bundle en una carpeta nueva, desde esa carpeta:

```powershell
$catalogPython = 'C:\tesis_mensajes_adulto_v1\.venv\Scripts\python.exe'
& $catalogPython -X utf8 -m pytest -q tests/test_activity_catalog_revision.py tests/test_child_offer_api.py tests/test_child_offer_coordinator.py tests/test_analytics_api.py tests/test_integration_closure.py::ConditionsCombinationsTests test_child_choice_signals.py test_recommendations.py --junitxml=actividades_revision_focal_windows.xml
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas del catálogo.' }
& $catalogPython -X utf8 tools/validation/verify_analytics_service_integration.py --output-dir ensayo_actividades_revision_ficticio_windows
if ($LASTEXITCODE -ne 0) { throw 'Falló el ensayo HTTP ficticio.' }
```

El verificador requiere una carpeta de salida que no exista. Cambiar el nombre
si ya se utilizó. No borrar evidencia anterior para repetirlo.

Si se solicita la regresión completa de esta versión:

```powershell
& $catalogPython -X utf8 -m pytest -q tests test_intervention_history.py test_intervention_service.py test_intervention_engine.py test_intervention_history_reader.py test_recommendations.py test_child_choice_signals.py test_weekly_analysis.py test_inference.py --junitxml=actividades_revision_completa_windows.xml
if ($LASTEXITCODE -ne 0) { throw 'Falló la regresión Windows.' }
```

Los tests heredados pueden agregar registros ficticios a
`data/intervention_history.jsonl`. Revisar `git status` después de ejecutar y
conservar copia de esos registros antes de restaurar ese archivo si fuera necesario.
No eliminar cambios ajenos a esta prueba.

## Actualización Docker en el entorno ya configurado

Desde la carpeta nueva del código y reutilizando las variables privadas de la
integración anterior:

```powershell
$catalogCompose = @('-f', 'deploy/compose.analytics.integration.yml', '-p', 'modera-analytics-integration')
docker compose @catalogCompose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Configuración inválida. Revisar token y red existentes.' }
docker compose @catalogCompose build analytics
if ($LASTEXITCODE -ne 0) { throw 'No se construyó la imagen.' }
docker compose @catalogCompose up -d analytics
if ($LASTEXITCODE -ne 0) { throw 'No se actualizó el contenedor.' }
```

La actualización debe conservar el mismo nombre de proyecto y volumen, y hacerse
con una copia consistente previa del estado según el procedimiento operativo.
Juanma debe adaptar estos comandos a su Compose real de AWS. Aquí no se ejecuta
un despliegue ni se afirma haber comprobado su entorno.
