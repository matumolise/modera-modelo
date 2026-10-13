# Cierre diario, orden y corrección de evidencia

Nota del 13/10/2026: la inmutabilidad y ausencia de API de corrección aquí
descritas siguen aplicando a C1. El servicio independiente de mensajes al adulto
sí admite revisiones diarias y versiones de tarjetas; su regla vigente es 14/14.
Ver [contrato de integración adulto](BACKEND_ADULT_MESSAGES_CONTRACT_2026-10-13.md).
No confundir esa revisión con rebuild o sobrescritura de recibos C1.

Contrato propuesto para el backend, con preflight offline implementado. No es
un nuevo formato del collector, endpoint C1 ni política de expiración.
Base publicada 94ff3a8; cambios solo en integration-audit-closure-candidate.

## Lo que hoy está fijado y lo que no

Analytics recibe v2, guarda representación/recibo/estado y mantiene resultados
inmutables. Un retry compatible recupera el original; cambios de valor,
estado, flags o procedencia para el mismo record devuelven 409. Un día nuevo
anterior/solapado al último aceptado de su serie devuelve 409. Esto no se cambia.
computed_at de representación y request_id pueden variar en un retry compatible;
el backend debe preferir conservar el payload completo para no regenerar evidencia.

No existe en este repositorio la cola durable del backend de Juanma, su modelo
de autorización ni un scheduler de ingestión. Tampoco una API de revisión,
invalidación o rebuild C1. No asumir que existen por estar documentados.

El body HTTP no incluye zona IANA/día local: analytics no puede acreditar por sí
solo que los dos instantes sean medianoches de esa zona. Esa pertenencia se
valida en preparador/preflight, con cabecera autorizada. Las guardas de duración
y computed_at no sustituyen esa vinculación ni prueban un reloj físico correcto.

| Estado explícito del backend | Qué significa | Preflight |
|---|---|---|
| EXPORT_PENDING | Evidencia todavía no fijada; incluye transferencia pendiente o consulta por resolver | request=null; WAIT_FOR_EVIDENCE |
| EXPORT_READY | El backend decidió que el lote disponible es el que pretende fijar; puede producir OBSERVED, OBSERVED_ZERO o MISSING | Payload validado; READY_TO_FREEZE si no hay un pendiente anterior declarado |
| ABSENCE_CONFIRMED | El backend declara ausencia de export para ese cierre, no ausencia de uso del teléfono | Payload MISSING; READY_TO_FREEZE bajo el mismo orden |

Se distinguen archivo ausente/corrupto, copia pendiente, fallo de captura y
ausencia confirmada de export. Un error leyendo un archivo no decide el estado.
No usar --no-export como fallback automático; no declarar cero por ningún caso
sin evidencia. No se añadió deadline ni un número de reintentos o días de espera.

EXPORT_READY tampoco demuestra exhaustividad física; no convierte coverage
desconocida en completa. El backend confirma autorización/vínculo y verifica
el paquete con load_packet antes de construir el plan. El preflight solo valida
estructura, serie/fechas, fingerprint y orden declarado, no esas pruebas externas.

## Ejemplo ejecutable y salida

`tests/fixtures/integration/daily_delivery_plan_synthetic.json` contiene una serie
ficticia: día 1 listo, día 2 pendiente, día 3 ausencia confirmada. La entrada tiene
plan_schema=f12-daily-delivery-plan-v1-candidate, series y days. Cada día contiene
local_date, evidence_state y request completo o null. Son campos NUEVOS del
plan backend propuesto; no se enviarán al endpoint histórico.

```powershell
.\.venv-historical\Scripts\python.exe tools/integration/check_daily_delivery_plan.py `
  --input tests/fixtures/integration/daily_delivery_plan_synthetic.json `
  --output "$env:USERPROFILE\Documents\modera_daily_plan_check.json"
if ($LASTEXITCODE -ne 0) { throw "Plan inválido; no fijar ni enviar payloads." }
```

La salida ordena los días y marca READY_TO_FREEZE, WAIT_FOR_EVIDENCE y
WAIT_FOR_PRECEDING_DAY, respectivamente. No inventa un día intermedio omitido
ni cambia un pendiente a MISSING. El calendario de días esperados pertenece al
backend, a partir de la asignación y calendario de medición realmente acordados.
Si el backend omite un pendiente de su plan, el preflight no puede adivinarlo.
No coordina workers ni acredita estado actual del servidor.

payload_fingerprint es SHA de JSON canónico del request, incluye request_id y
computed_at; es una referencia del plan, distinta de provenance.input_fingerprint
y de la SHA de los bytes request.json. La salida dice explícitamente que no
verifica autorización, no persiste payloads y no envía HTTP. La escritura del
reporte exige archivo nuevo; input limitado a 32 MiB, máximo 10000 días declarados.

## Protocolo de integración recomendado

1. Backend autenticado fija perfil/aparato/asignación/namespace, zona y versión.
2. Conserva originales y cabecera; valida export y paquete. Anota pendientes
   reales sin tratarlos como cero o como ausencia final.
3. Decide qué evidencia fija para el día. Ejecuta preflight con todos los días
   pendientes de esa serie que conozca. Sin políticas temporales implícitas.
4. En UNA transacción de su almacenamiento guarda payload completo, SHA de bytes,
   versión/procedencia, identificador estable y estado FROZEN/pendiente de envío.
   Un índice único por serie/día evita cierres simultáneos distintos. Estos
   nombres son un diseño propuesto, no tablas/estados encontrados en su backend.
5. Un dispatcher serial por serie envía en orden. La reserva de trabajo, retry
   y confirmación también deben ser durables; una prueba con proceso reiniciado
   debe demostrar que no se pierde ni regenera el payload.
6. HTTP 200 processed confirma receipt, incluso ABSTAIN. Guardar configuración
   y result completo. Si se pierde respuesta tras commit, reenviar el payload
   congelado recupera el recibo; no fabricar record_id o reconsultar Android.
7. HTTP 400 corrige la preparación antes de recibir un record;401 revisa credencial;
  409 exige conciliación humana/técnica de identidad, contenido u orden;
  503 conserva el trabajo pendiente y requiere investigar disponibilidad.
   No se fija aquí una política de backoff ni se anuncia envío a familias.

## Evidencia nueva después del cierre: alternativas

| Alternativa | Consecuencia y límite | Estado |
|---|---|---|
| Mantener provisional y esperar antes del primer envío | Evita cambiar recibos ya aceptados; necesita definir cuándo fijar evidencia | Recomendación operativa para datos todavía no enviados; sin plazo inventado |
| Conservar evidencia tardía y abrir incidencia de corrección | Mantiene recibos originales y no falsifica retry; no actualiza C1 por sí sola | Implementable por backend como procedimiento; pendiente de su integración |
| Replay técnico versionado en repositorio aislado desde el día afectado | Puede producir una nueva trayectoria; requiere historia/evidencia completa, perfil/versiones y linaje de revisión, comparación y decisión de reemplazo | Diseño a decidir; NO implementado ni autorizado como reparación automática |
| Pisado de record/receipt o nuevoID con mismo día para evitar 409 | Rompe inmutabilidad o produce conflicto temporal; doble historia no acredita corrección | Rechazado |
| Crear nueva asignación ficticia/serie solo para aceptar corrección | Evade identidad y cold-start; pierde continuidad y oculta revisión | Rechazado |

Cambios reales de aparato/asignación/zona/semántica sí pueden definir nueva serie,
con un hecho de origen y política documentada; no son herramientas para eludir
errores. No se trasladan estados CUSUM automáticamente. El endpoint actual no
ofrece retcon, superseded_by, revisión de emisión ni actualización de tarjetas.

La propuesta adulta del 10/10 hablaba de revisar ventanas y reconstruir desde un
día corregido; no constituye aprobación ni una función actual del histórico.
Comparación7 contra 7, regla adulta y C1 son objetos distintos. No reemplazar la
referencia all_prior_usable_records_v1 por la comparación de una tarjeta.

## Decisiones que quedan abiertas

Juanma/equipo: confirmar IDs/asignación y calendario esperado; dónde ejecuta el
job; almacenamiento transaccional/dispatcher; quién fija evidencia; tratamiento
de transferencias pendientes; proceso explícito de corrección y responsabilidad
por su aceptación. Recomendación: reutilizar preparador Python y recibos actuales,
conservar evidencia tardía como revisión pendiente y empezar con una serie de
ensayo sin migrar estados. No prometer un cierre de producto sin esas decisiones.
