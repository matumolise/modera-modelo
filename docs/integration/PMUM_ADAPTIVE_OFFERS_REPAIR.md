# Reparación de código: PMUM-SF y espera entre ofertas infantiles

Base conservada: `831d43326b94546829be2b9f7b30f58816535d11`.
Código candidato: `4659b15` en `pmum-adaptive-offers-repair-candidate`.
Este documento es una guía técnica del candidato. No modifica la tesis entregada.

## Qué se recuperó

El acuerdo recuperado del 10 de octubre establecía que una puntuación PMUM
estimada mayor redujera la espera entre ofertas automáticas, y una menor las
espaciara. No se recuperó una función numérica aprobada ni validación de sus
extremos. La versión base había implementado una espera fija de 120 minutos.

Este candidato conecta la inferencia con la coordinación. Conserva el Ridge,
sus cuatro entradas, sus transformaciones, su salida de 1 a 5 y el artefacto
original. No entrena modelos ni convierte la puntuación en clases de riesgo.
El selector del catálogo, C1 y los mensajes adultos permanecen sin cambios.

## Regla de espera propuesta e implementada

Se utiliza interpolación lineal continua:

`espera = máxima - (puntuación - 1) * (máxima - mínima) / 4`

Los dos extremos deben configurarse explícitamente. No hay extremos adaptativos
por defecto. Este candidato exige `120 <= mínima < máxima <= 1440` minutos:
conserva los 120 minutos de la versión anterior como piso operativo. Esa
restricción y la función son decisiones de ingeniería, no resultados de Ridge
ni parámetros validados por la revisión profesional de las consignas.

Ejemplo controlado usado en las pruebas, con extremos de 120 y 180 minutos:

| Puntuación estimada | Espera después de la entrega confirmada |
| --- | --- |
| 1 | 180 minutos |
| 3 | 150 minutos |
| 5 | 120 minutos |

El ejemplo no acredita que esos extremos sean óptimos ni que sean una
prescripción para cada niño. Deben fijarse expresamente antes de habilitar la
política. Los cupos pueden impedir otra oferta aun después de cumplida la espera.

La primera oportunidad diurna sigue requiriendo 45 minutos continuos verificados.
PMUM modifica la espera entre entregas, no ese primer disparador. La espera se
guarda con la oferta generada y comienza cuando se confirma su primera entrega.
Actualizar respuestas después no acorta una espera ya iniciada. La espera es
compartida por ofertas diurnas y de descanso. Permanecen las ventanas horarias,
los máximos diarios y móviles, una oportunidad por intervalo, la pausa por
rechazos y las guardas de identidad, captura, escuela y elegibilidad.

## Contrato HTTP y uso del modelo

Nueva ruta interna autenticada: `POST /v2/child-offers/evaluate`.
No se expone Analytics ni su token a Android.

```json
{
  "request_id": "fictitious-adaptive-evaluation-001",
  "evidence": {
    "profile_id": "fictitious-account.child-001",
    "series_id": "fictitious-assignment-001",
    "interval_id": "fictitious-interval-001",
    "now": "2026-10-16T10:00:00-03:00",
    "interval_started_at": "2026-10-16T09:00:00-03:00",
    "bedtime_at": "2026-10-16T21:00:00-03:00",
    "automatic_enabled": true,
    "assignment_verified": true,
    "shared_phone": false,
    "capture_verified": true,
    "screen_interactive": true,
    "game_active": false,
    "in_school_period": false,
    "eligibility_state": "known",
    "eligibility": {},
    "interests": []
  },
  "pmum_parent_answers": {
    "age": 9,
    "sex_code": 1,
    "weekday_category": 2,
    "weekend_category": 3,
    "respondent": "parent_or_caregiver",
    "reference_days": 30
  }
}
```

El ejemplo es ficticio y conserva el objeto `evidence` del fixture
`tests/fixtures/integration/child_offer_evaluation_fictitious.json`. En una
integración real debe representar las condiciones que el backend pueda
acreditar. No copiar los booleanos ficticios
como si probaran captura o identidad. Las dos categorías temporales corresponden
al reporte del adulto. No sustituirlas por minutos Android ni por los nueve
ítems del cuestionario objetivo. El backend debe resolver las entradas para el
perfil autorizado y su serie actual, sin aceptar una puntuación declarada por
Android.

Analytics ejecuta `CachedPmum.estimate` y entrega el resultado al coordinador en
una misma transacción con el recibo. Guarda puntuación, versión del modelo,
SHA-256 del artefacto, huella de entradas asociada al perfil/serie, configuración
y espera efectiva dentro de `offer.timing`. No agrega las respuestas parentales
sin procesar al historial de ofertas.

Si las entradas parentales están ausentes o fuera del dominio, no inventa una
puntuación: devuelve `suppressed / pmum_unavailable`. Un fallo técnico del
estimador devuelve 503 y revierte la transacción. Una petición idéntica ya
registrada devuelve su recibo original sin volver a inferir, incluso si falla
el estimador después. Cambiar contenido con el mismo request_id produce 409.

Se conservan las rutas v1 de eventos e historial. El servicio sin configuración
adaptativa conserva su conducta v1. Sobre una base adaptativa, las evaluaciones
v1 nuevas devuelven 400 para impedir ofertas que omitan la estimación. Los
recibos v1 exactos anteriores a la migración siguen recuperándose por v1.
La solicitud voluntaria `/v1/activities/select` permanece independiente.

## Modelo original y validación en Windows

El artefacto original no está incluido en el repositorio ni en el bundle de
reparación. No usar `models/pmu_linear_v1.joblib`, que es el antecedente sintético.

Artefacto esperado: `hu_pmum_sf_experimental_v1.joblib`.
SHA-256 original registrado:
`56c991f40e56d2241196dc6f9efc1c9027c079e98a1b67549f48b10292e371e0`.

Mantenerlo junto a `hu_pmum_sf_experimental_v1.json`. La ubicación aportada antes
por Matías fue `Documents/modera_pmum_experimental`. Corroborar que todavía sea
la carpeta correcta antes del ensayo. No se altera el manifiesto histórico para
atribuirle aprobación clínica ni integración previa.

En la carpeta del nuevo worktree, después de verificar e importar el bundle:

```powershell
$repairPython = 'C:\tesis_mensajes_adulto_v1\.venv\Scripts\python.exe'
$repairModelDir = Join-Path $env:USERPROFILE 'Documents\modera_pmum_experimental'

& $repairPython -X utf8 -m pytest -q tests/test_pmum_child_offer_adaptation.py tests/test_child_offer_api.py tests/test_child_offer_coordinator.py tests/test_analytics_api.py --junitxml=pmum_ofertas_focal_windows.xml
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las comprobaciones de código.' }

$repairOutput = Join-Path $PWD ('ensayo_pmum_original_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
& $repairPython -X utf8 tools/validation/verify_pmum_child_offer_integration.py --model-dir "$repairModelDir" --output-dir "$repairOutput" --minimum-minutes 120 --maximum-minutes 180
if ($LASTEXITCODE -ne 0) { throw 'Falló el ensayo con el modelo original.' }
```

Los extremos de este comando corresponden al ejemplo de ensayo. El programa
no entrena ni modifica el artefacto. Verifica su hash original antes de cargarlo,
ejecuta inferencias válidas, elige dos puntuaciones diferentes y comprueba en un
servidor HTTP local que generan esperas distintas. Reinicia el proceso, recupera
seis recibos y comprueba que no se dupliquen historiales. `report.json` distingue
el modelo original de los predictores controlados usados por los tests.

## Activación y conservación de datos

No hay publicación ni despliegue automático. Antes de una activación real,
Juanma debe conectar las respuestas parentales persistidas y usar la ruta v2.
El formulario que solo permite seleccionar respuestas de demostración no basta.

Variables nuevas, ambas obligatorias para seleccionar la política adaptativa:

- `ANALYTICS_CHILD_OFFERS_PMUM_MIN_MINUTES`
- `ANALYTICS_CHILD_OFFERS_PMUM_MAX_MINUTES`

También deben habilitarse PMUM y el coordinador y configurarse el artefacto,
manifiesto, hash y base persistente. `/health` informa la versión de política y
la configuración adaptativa efectiva. Si la base corresponde a otra política,
el arranque falla en lugar de cambiarla o vaciarla.

Para conservar estado v1, detener el servicio y usar el módulo
`analytics_service.migrate_child_offer_pmum`. Recibe `--source`, `--target`,
`--pmum-min-minutes` y `--pmum-max-minutes`. Las rutas deben ser absolutas y el
destino no debe existir. Copia SQLite, conserva ofertas, eventos y recibos y
registra el cambio de política en la copia. No modifica el origen. Las ofertas
v1 conservadas mantienen su espera anterior de 120 minutos.

`deploy/compose.analytics.pmum-candidate.yml` es un complemento explícito al
compose de integración, no su reemplazo. Requiere la carpeta del modelo como
montaje de solo lectura, su hash y los extremos. Utiliza una ruta SQLite nueva
dentro del mismo volumen y ofrece una operación de migración separada. No usar
la inicialización de una base vacía para sustituir una base que debe migrarse.
No ejecutar `down -v` ni borrar el volumen.

## Alcance de las comprobaciones

Los reportes en `docs/integration/evidence/pmum_adaptive_repair` registran los
ensayos Linux. Las pruebas usan un predictor ficticio identificable para
comprobar transporte, coordinación, errores y persistencia. No acreditan una
nueva ejecución del `.joblib` original ni eficacia de la adaptación.

Pendientes separados: ensayo Windows con el artefacto original, Docker en un
entorno que lo soporte, integración de respuestas y llamadas desde el backend,
recorrido Android/AWS y revisión de la tesis/presentación. La revisión profesional
de las consignas no valida la relación entre puntuación y frecuencia de oferta.
