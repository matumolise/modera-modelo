# Resultado de la entrega de integración analítica

Fecha: 17/10/2026.
Rama nueva: `analytics-service-integration-candidate`.
Base: `8dbbc803d67e63fdd3b52b2151fa97b7f2d32807`.
Primer cierre API: `5fa04ef`.
Runtime comprobado: `8b138f0167fabbeb58de61e946fd92835fe4ee50`.
Herramienta HTTP final y mismo runtime: `f619c4f8c1adb3816e84c31643ea1c8aee7cf051`.
Los cambios de cierre posteriores a ese commit son evidencia y documentación.
El hash final del bundle identifica la entrega completa, no una nueva corrida.

## Cambios

- Se conectaron evaluación, eventos e historial del coordinador con la API interna.
  Se reutilizan sus transacciones, selección y DTO. `POLICY` no cambió.
- Se distinguieron errores de petición, conflicto y almacenamiento mediante
  subtipos compatibles con `ValueError`. Se conservan los mensajes de error de
  la biblioteca, los recibos y el estado almacenado.
- La capacidad se habilita explícitamente y exige una base previamente inicializada.
  La pérdida de una base no provoca su recreación automática.
- Se añadió CLI de inicialización, configuración de integración y exclusión de
  datos, modelos y secretos del contexto de construcción Docker.
- Se añadió al runtime la misma versión `tzdata==2026.5` ya fijada para preparar
  F12. Permite disponer de la base IANA también en Windows. No se cambiaron
  versiones de las dependencias científicas ni se entrenó un modelo.
- Se tradujeron comentarios `#` en nueve archivos. Se comparó su AST antes y
  después. Docstrings, identificadores, cadenas funcionales y directivas se
  conservaron. La fuente de `recommend_activities` se mantuvo para no cambiar
  su huella ni semilla. Dos comentarios internos en inglés son una excepción
  documentada, no una traducción pendiente que deba hacerse mecánicamente.
- No se modificaron el catálogo, PMUM, C1, las reglas adultas, Android, backend
  de Juanma ni el PDF entregado.

## Comprobaciones ejecutadas

Entorno: Linux, Python 3.12.14, pytest 9.1.1 y dependencias fijadas.
La evidencia es ficticia y controlada. No corresponde a observación de familias.

| Comprobación | Resultado | Evidencia |
| --- | --- | --- |
| API infantil, coordinador y API previa, más comprobación UTF-8 del catálogo | 104 pruebas y 43 subtests aprobados, 2,10 s | `pytest_focused_linux.xml` |
| Regresión completa, incluidos los lectores de historial de raíz | 481 pruebas y 192 subtests aprobados, 17,14 s | `pytest_full_linux.xml` |
| API/coordinador y comprobación UTF-8, con `LC_ALL=C`, `PYTHONUTF8=0`, `PYTHONCOERCECLOCALE=0` y `-X utf8=0` | 76 pruebas aprobadas, 1,31 s | Salida de consola conservada en el registro de trabajo de este bloque |
| HTTP nativo, proceso Uvicorn real | PASS | `http_process_fictitious_report.json` |
| Inicialización CLI | Crea una base nueva. Reabrir conserva sus bytes. Base vacía y ruta relativa se rechazan | Comprobación local con archivos temporales ficticios |
| Sintaxis de módulos | `compileall` satisfactorio | Comprobación local |
| Compose | YAML válido y estructura estática revisada | No equivale a ejecutar `docker compose config` |
| AST de las traducciones | Sin cambios funcionales en los nueve archivos | `comment_translation_ast_audit.json` |
| Núcleo del coordinador | AST equivalente a la base al normalizar únicamente los nuevos subtipos de `ValueError` y excluir sus declaraciones | Comprobación local |

Los XML de pytest 9.1.1 representan también los subtests como casos JUnit:
673 entradas en la regresión equivalen al registro de 481 pruebas y 192 subtests.
No se informa que existan 673 pruebas independientes. Análogamente, 147 entradas
JUnit de la corrida focal corresponden a 104 pruebas y 43 subtests.

La advertencia heredada Starlette/httpx permanece. No produjo fallos y no se
cambió la dependencia para ocultarla. Los tests escribieron cuatro registros
ficticios en el JSONL legado de la copia de trabajo. Se restauró ese archivo a
su contenido de la base antes de guardar la entrega. No se incluyen datos de
ejecución en ese historial.

### Alcance del ensayo HTTP nativo

Se inicia un proceso nuevo con PMUM deshabilitado y un perfil C1 SMOKE_ONLY.
Se comprueban autenticación, generación infantil, entrega, selección e historial,
procesamiento histórico y tarjetas de aumento/disminución. Se termina el proceso
sin limpiar las bases. Un segundo proceso recupera los recibos originales con
`replayed: true`, sin duplicar ofertas, eventos o versiones adultas. El archivo del estado C1
conserva también sus bytes después del reinicio y replay. Se comprueba
un conflicto y el retorno del aviso adulto.

El oráculo de la evidencia procede del fixture: identidad, continuidad y calidad
están construidas de forma controlada. No se deducen del éxito del preparador ni
se convierte cobertura desconocida en completa. El ensayo no abre el artefacto
PMUM real ni consulta Android o el backend de Juanma.

Los archivos de evidencia y las fuentes del runtime están identificados mediante
SHA-256 en `evidence/analytics_service_2026-10-17/source_and_evidence_sha256.json`.
Los reportes JSON y XML se conservan en esa misma carpeta. Los archivos SQLite
temporales y los tokens de ensayo no se incorporan a Git ni al bundle.

## No ejecutado en este entorno

- Docker no está instalado. No se construyó la imagen, no se ejecutó Compose
  ni se acreditaron reinicio o permisos dentro de un contenedor.
- Windows de esta versión, teléfono, backend de Juanma y AWS no ejecutados aquí.
  Los resultados Windows anteriores pertenecen a sus versiones anteriores.
- Compatibilidad del export Android actual pendiente de recibir una muestra.
- Sin calibración C1 de producto, dictamen profesional nuevo del catálogo,
  validación con usuarios, demostración de eficacia o certificación legal.

## Estado del candidato

Listo para importar y comenzar la integración de las APIs en un entorno de prueba.
No se anuncia como despliegue productivo validado ni como integración completa
Android → backend → preparador → Analytics → panel.
Los pasos Windows, Docker y aceptación conjunta están en
`ANALYTICS_SERVICE_HANDOFF_2026-10-17.md`. No se publicó, hizo merge ni desplegó.
