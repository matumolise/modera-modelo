# Auditoría acumulativa y cierre técnico resoluble

Base verificada: 94ff3a82ad3581e74cb6f97449adda264972c61b, publicada en
f12-export-integration-candidate. Se verificaron 155 archivos usados contra sus
blobs; snapshot parcial, no clon completo. Rama nueva local del trabajo:
integration-audit-closure-candidate. No merge, cambios a ramas entregadas ni AWS.

## Feedback acumulativo: errores reales encontrados

Antes de cambiar código se ejecutaron tres contraejemplos contra la base:

| Contraejemplo | Base 94ff3a8 | Candidato nuevo |
|---|---|---|
|1500 min en un intervalo de 24 h | parse_historical_request acepta | Rechaza por duración mayor al intervalo, HTTP 400 sin escribir |
| computed_at anterior al final representado | Acepta | Rechaza intervalo no cerrado al preparar, HTTP 400 sin afectar readiness |
| Dos consultas exitosas solapadas: una omite OFF que sí reporta la otra | Preparador devuelve OBSERVED | Rechaza snapshots incompatibles, conserva originals |

Son validaciones del contrato, no parámetros C1. Se calcula el máximo por la
duración real UTC del intervalo, incluidos 23/25 h, sin fijar 1440 para todos los
días. No se comprueba sincronización física de relojes por esta regla: el backend
declara computed_at, y sigue siendo responsable de un reloj fiable.

La validación de overlap compara el multiconjunto de eventos en la intersección
de consultas exitosas, ignorando metadatos propios de la consulta/ordinal pero
preservando multiplicidad. La clave observable no se declara identidad única.
Ni deduplica ni reordena los originales. Fallas de consulta no se comparan como
snapshots vacíos exitosos; no borran evidencia independiente. Un disagreement
puede venir de retención/consulta/transferencia: no se elige un snapshot ganador
ni se afirma cuál refleja lo ocurrido físicamente. Se rechaza el lote para
investigar; nunca se transforma automáticamente en cero/cobertura completa.

Usa búsqueda binaria sobre tiempos ordenados y un presupuesto técnico de 100000
comparaciones de pares. Excederlo falla sin truncar; no es umbral de salud/C1.

## Integridad del paquete: suposición de un test corregida

El verificador original comprobaba raw/request/lineage pero no preparation.json
ni el manifiesto completo. Su fixture de reporte creaba un paquete incompleto
que no era el que escribe el CLI. Se ajustó ese test a un paquete real del CLI,
incluyendo preparation y SHA256SUMS, sin presentarlo como export físico.

load_packet ahora exige inventario/huellas completas, rechaza entradas duplicadas,
traversal/symlinks, UUID no canónico/v4 y cambios en la preparación intermedia.
Reconstruye el request/audit/preparation y compara JSON canónico, distinguiendo
bool de entero, incluso si alguien recalcula los hashes después de alterarlo.
Los bytes que usa al reconstruir se comparan contra el manifiesto ya leído:
una modificación entre verificación y lectura se rechaza. No vuelve inmutable
el filesystem ni sustituye la transacción/fijación del backend.
Límites técnicos de archivo de manifiesto 4 MiB y paquete 256 MiB; no parámetros C1.
Las huellas no autentican aparato/persona ni resisten a un actor que sustituya
coherentemente TODOS los datos: el backend debe autorizar y preservar origen.

Paquetes válidos generados por 94 conservan sus payloads/fingerprints. Un lote
previamente aceptado que ahora evidencia discrepancia no se reescribe: se guarda
la evidencia/recibo previo y se abre revisión. Un repositorio con una
representación imposible o un computed_at no cerrado falla de forma explícita
al validarse; no se repara/borran datos automáticamente. Recomendación: ensayar
con repo nuevo y revisar cualquier histórico previo real antes de adoptar.

## Decisiones que se precisaron sin inventar política

[DAILY_EVIDENCE_CLOSURE_2026-10-12.md](DAILY_EVIDENCE_CLOSURE_2026-10-12.md) define
plan backend propuesto, preflight offline y frontera de la API inmutable.
EXPORT_PENDING no recibe payload definitivo; un pendiente bloquea días
posteriores declarados. EXPORT_READY o ABSENCE_CONFIRMED pueden quedar
READY_TO_FREEZE, que todavía no persiste/envía nada. Sin deadline, cola real,
revisión automática ni creación de días omitidos. El preflight no acredita
autorización ni disponibilidad de materiales/personas.

Corregir después de procesar no es reintentar: ni payload cambiado ni recordID
nuevo ni asignación ficticia sustituyen recibos. Replay aislado/versionado queda
como alternativa a diseñar, no una política adoptada. C1 referencia sigue
all_prior_usable_records_v1; no se mezcla con 7 contra 7 ni con v3.

## Catálogo y dependencias recuperadas

La matriz funcional enlazada mantiene 18 actividades sin mapping automático ni
aprobación profesional. Se descartó una corrección inicialmente propuesta: mirar solo la descripción
de social_story_01 omitía su título Escuchá una historia, que sí explicita escucha.
Se verifican ahora título/descripcion y sus hashes, sin inferir apoyos disponibles. No se convierte eso en aprobación por condición.
En el feedback final se corrigió también una inferencia de modalidad: lectura
no fija formato visual y dibujo/escritura/construcción no fija miembros o apoyos.
Sus dominios quedan V; los movimientos de ejemplo tampoco son obligatorios.
La regresión comprueba esas abstenciones de inferencia, sin modificar el catálogo.
Las 31 combinaciones no vacías de etiquetas admitidas siguen absteniéndose.
Ninguna no acredita disponibilidad/materiales/acceso global: hay consolidación
operativa pendiente del backend/UI, no solo una pregunta general.

El backlog recupera pendientes omitidos en la lista corta: trazabilidad versus
entrega real, escritura JSONL de ofertas sin las garantías del repo C1, aprendizaje
de preferencias, reglas adultas/revisión, dataset sintético y RF-10/CU-04.
La propuesta del 10/10 describe conceptos/casos que no son hoy endpoints ni tablas:
no se adoptaron topes/esperas/números por estar en ese texto. El motor legado
voluntario/descanso existe, pero el coordinador diurno/global no está implementado.

## Evidencia de pruebas

Ver EVIDENCE/validation_summary.json y logs en la entrega. En Linux/Python 3.12.14
pasaron 305 casos, incluidos 17 casos nuevos; 15 pruebas de
raíz y seis scripts heredados también pasaron. El recorrido HTTP recuperó
11 recibos después de terminar y reiniciar el proceso. Se comprobaron CLI
offline, HTTP 400 ante entradas inválidas y un paquete válido de la base 94. Fixtures íntegramente
ficticias, perfil SMOKE_ONLY no calibrado, PMUM deshabilitado. No se carga HU real.

La base 94 pasó en Windows 288 casos —287 PASS y 1 omisión—, 15 raíz y 6 scripts más HTTP,
Docker/persistencia/restart/health según consola/summary compartidos. Eso no
valida Windows/Docker de los cambios nuevos. Android/harness sigue sin build o
teléfono nuevo; no se transfieren los antecedentes de emulador a validación física.

No se modificaron núcleo historical/, sus parámetros/perfil, catálogo/selector,
PMUM, generador, ofertas ni tarjetas. La base del backend de Juanma no se leyó;
se prueban adaptadores del repositorio y un contrato propuesto, no su aplicación.

## Auditoría final y entrega

Patch contra 94ff3a8, checksums, manifiesto de fuentes, ejemplos y aplicador
Windows separado. El aplicador protege las cuatro ramas y crea otra carpeta;
no hace commit/push. Documentos antiguos quedan como antecedentes con un enlace
al estado vigente; el mensaje completo corrige publicación/validación de 94 sin
atribuir las pruebas nuevas a ese commit.

Pendientes externos agrupados: nuevo Windows/Docker; build/harness/teléfono;
IDs/asignación/calendario/outbox/cierre/correcciones del backend; revisión
profesional/configuración de producto. Alternativas y criterios están en
MODERA_BACKLOG y DAILY_EVIDENCE_CLOSURE. No se requiere que el usuario ejecute
comandos intermedios para completar este bloque autónomo.

## Validacion posterior Windows y Docker - 2026-10-12

Ejecucion realizada por Matias; resultados revisados mediante consola y validation_summary.json compartidos. Este bloque actualiza el pendiente Windows/Docker indicado anteriormente.

- Python 3.10.0; entorno separado; pip check aprobado.
- tests/: 305 casos en 24.896 segundos; 304 aprobados y una omision.
- Raiz: 15 pruebas aprobadas en 0.163 segundos.
- Seis scripts heredados ejecutados correctamente.
- HTTP Windows: seed y recuperacion tras terminar/reiniciar aprobados.
- Docker: Compose, build, volumen, seed, reinicio, replay, identidad y healthcheck aprobados.
- Archivos probados verificados antes de actualizar documentos.
- Datos ficticios; perfil no calibrado; PMUM deshabilitado.

Evidencia local: `C:\Users\matum\Documents\modera_historical_smoke_20261012-112015-5c410aed`.

Manifiesto probado: `6d9305d2e173231546632d8500d04508a8120f658b64599d328fb96f37f8155b`.

Imagen comprobada: `sha256:2c4dc05b987954ea6ef18e927b971d353e981585a2b1986962b02e5575f848aa`.

Volumen conservado: `modera-historical-smoke-20261012-112015-5c410aed`.

Siguen pendientes compilacion Android, telefono fisico, backend real y AWS. No se calibro C1 ni se aprobo el catalogo.
