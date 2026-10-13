# Mensajes al adulto: candidato implementado v1

13/10/2026. Base e090bd4; rama nueva adult-messages-v1-candidate. Este documento
reemplaza las decisiones pendientes del contrato propuesto anterior para este
candidato interno. No equivale a eficacia demostrada ni configuración clínica.

## Decisiones cerradas en esta implementación

| Decisión | Implementación |
|---|---|
| Ventanas y cadencia | 14 contra14, lunes, últimos28 días locales completos |
| Cobertura | Todos los días de ambas ventanas observados y verificados; cero observado válido |
| Atribución | Backend declara explícitamente assignment_verified; serie incorpora identidad/asignación/medición |
| Contexto | Shared_phone y context_declared explícitos; true o atribución no verificada inhiben apertura/retorno |
| Apertura | Diferencia absoluta>=20 min/día, resistente a excluir cualquier día de ambas ventanas, al menos10 días en la dirección |
| Retorno | Margen5 min/día, exclusión en contra; unilateral y simétrico para disminución; ventana reciente sin solapar apertura |
| Episodio | Una tarjeta, referencia congelada por fechas; actualizaciones/estado inconcluso/datos insuficientes |
| Vigencia | Máximo56 días desde apertura; vencido no significa resuelto |
| Espera/tope | 14 días desde terminación; una tarjeta nueva por28 días por perfil en ambas direcciones |
| Qué se cuenta | Tarjetas creadas, incluso retiradas; no “vistas” o “entregadas” sin ACK |
| Correcciones activas | Revisión creciente, apertura recalculada; retiro si se invalida; referencia por mismas fechas con última revisión |
| Correcciones de tarjetas terminadas | Nueva versión WITHDRAWN si apertura se invalida; en otro caso CORRECTED_HISTORY sin cifras obsoletas ni reapertura retroactiva |
| Idempotencia | Mismo request con mismo contenido=replay; otro contenido=409; contenido equivalente con nuevo request=replay |
| Orden | Evaluaciones por perfil no retroceden; admite revisión de la misma fecha; BEGIN IMMEDIATE serializa |
| C1 | Evidencia complementaria con IDs; sin gate, reset, reentrenamiento ni sobrescritura. Correcciones marcan advertencia desde la fecha más temprana de esa serie |
| PMUM | Sin efecto sobre tarjetas o actividades; preserva alcance existente |
| Persistencia | SQLite propio: entradas, recibos, estado, revisiones diarias y versiones de tarjetas en una transacción |

20/10/5 son decisiones iniciales de ingeniería: magnitud interpretable,
mayoría de días y separación apertura/retorno. No se derivaron de un umbral
de salud ni se eligieron por maximizar este experimento. 14/56/28 son políticas
operacionales de cadencia y volumen. Para un perfil futuro diferente se necesita
versión nueva y base separada/migración explícita, no cambio silencioso.

Se simplificó el retorno eliminando K_r: mide el promedio y su sensibilidad,
sin afirmar que todos los días volvieron. El agregado y la exclusión usan pesos
5/7 lunes–viernes y2/7 fin de semana; el conteo usa la referencia original. No se
aceptan ventanas incompletas, por lo que no se infiere un período faltante.

## Integración con analytics

Variables nuevas (deshabilitado por defecto para preservar despliegues existentes):

```
ANALYTICS_ADULT_MESSAGES_ENABLED=true
ANALYTICS_ADULT_MESSAGES_REPOSITORY_PATH=/data/adult-messages.sqlite3
```

Montar /data en almacenamiento persistente. Ruta absoluta diferente del repositorio
C1. No requiere nuevas dependencias. Conserva autenticación y límites de la API
existente; no se expone token a Android. Endpoint de servicio para el backend:

- POST /v1/adult-messages/evaluate
- GET /v1/adult-messages/profiles/{profile_id}/history

El backend autentica al padre y verifica su acceso al perfil antes de consultar
esta API interna. No se traslada el token de servicio al frontend.

La capacidad adult_messages aparece en /health sólo si fue habilitada, para no
cambiar el contrato anterior por defecto. Ausencia/corrupción de su repositorio
da indisponibilidad, no una decisión de ausencia de cambios.

## Entrada

Todos los campos son obligatorios, sin campos adicionales:

```
request_id, profile_id, series_id, time_zone, evaluation_date,
assignment_verified, shared_phone, context_declared, days, c1_evidence_ids
```

evaluation_date es el lunes posterior a los días comparados; no una fecha futura.
series_id es estable para la misma asignación, dispositivo, perfil, zona y versión
de medición. No se debe reutilizar al cambiar cualquiera de esas dimensiones.
Reutilizar series_id con otra time_zone produce409, incluso sin episodio activo.
Una serie nueva permite terminar el aviso anterior por cambio de medición.

Cada elemento de days:

```
date: YYYY-MM-DD
revision: entero >=1, creciente ante corrección
minutes: número finito no negativo; null si no observado
observed: booleano explícito
quality_verified: booleano explícito
```

No se toma quality_verified de un simple “llegó el lote”. Lo decide el cierre
diario del backend con evidencia de captura. F12 actual puede tener cobertura
desconocida: eso no autoriza a poner true por defecto. Se validan minutos contra
la duración real del día local, incluidos DST23/25 horas.

Primer envío: al menos28 días verificados para poder abrir. Envíos siguientes
pueden incluir sólo días nuevos/corregidos: el almacén conserva el historial.
Límite:366 registros por request y el límite de bytes existente; enviar lotes
menores si es necesario. Las revisiones del mismo día no se duplican en un lote.
Un MISSING previamente recibido sólo pasa a observado mediante revisión nueva.

c1_evidence_ids son referencias de recibos de la misma serie, que el backend
debe comprobar. El servicio los conserva para trazabilidad: no pretende verificar
su autenticidad sin acceso al repositorio C1. Pueden estar vacíos y no habilitan
ni vetan una tarjeta. Un C1 afectado por corrección se informa como evidencia
anterior; nunca se finge que se recalculó.

## Salida para la vista del padre

status, action (CREATE/UPDATE/NONE), evaluation_id, card_version, replayed y card.
La tarjeta contiene título, explicación, recomendación, fechas, dirección,
estado, cifras y detalle de qué se midió. La versión y huella de configuración
quedan para trazabilidad. Estos metadatos no necesitan aparecer en la vista corta.

delivery_status=CANDIDATE_NOT_DELIVERED y push_notification=false. El servicio
crea/persiste el DTO; no afirma que Android lo renderizó. Al presentar historial,
agrupar por card_id y mostrar la última versión; conservar anteriores en auditoría.
historical_card_corrections avisa qué tarjetas archivadas recibieron una versión.
Un retry exacto devuelve su resultado original, aunque hoy la tarjeta tenga
otras versiones; obtener la vista actual mediante history.

Al reiniciar se distingue un archivo nuevo de un repositorio existente incompleto.
Si falta alguna tabla requerida, no se recrea vacía ni se declara READY: se informa
indisponibilidad y se requiere recuperar el store. Los estados privados anteriores
con advertencia global C1 se convierten a advertencias por serie usando los recibos
guardados, sin reescribirlos ni cambiar el perfil numérico.

Sin nuevas candidatas ante falta de datos/contexto. Una tarjeta existente puede
informar incertidumbre sin llamar recuperación a un faltante. Texto de consejo
genérico inicial, sin diagnósticos o atribución del resultado a Moderá.

## Validación y entrega restante

Implementado/probado: motor, estados, textos iniciales, persistencia, revisiones,
replay, serialización concurrente y transporte HTTP interno. C1/HU/actividades
no se modifican. Hay demo ejecutable y evaluación simulada con perfil fijo.

Juanma conecta: cierre diario y atribución reales → entrada; salida → persistencia
y vista adulta del backend/frontend. El modelo todavía no verifica su código ni
el teléfono físico por estas pruebas. AWS y recorrido Android real son trabajos
de integración concretos, no decisiones matemáticas abiertas de esta política.

La revisión profesional de consejos y comprensión, y la evaluación con familias,
son evidencia externa no producida aquí. Se pueden mostrar los DTOs ficticios
para entrega/demo sin confundirlos con mensajes ya entregados a familias.
