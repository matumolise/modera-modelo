# Contrato de integración backend–analytics–panel adulto

Código de referencia: `1fd977c8d03409778ea8ae67ca1cfc5fc842aba5`.
Complementa [CONTRACT_AND_HANDOFF](../adult_messages/CONTRACT_AND_HANDOFF.md).
No agrega endpoints, tablas del backend, scheduler ni ACK de Android.
Los requisitos de payload/resultado describen código existente; la coordinación
y recepción visual descritas son trabajo de integración de Juanma/equipo.

## Servicio, acceso y configuración

Android llama al backend autenticado; el backend llama a analytics con
`Authorization: Bearer <credencial de servicio>` y JSON UTF-8. El token no va
en Android y no reemplaza la autorización del padre sobre el perfil.
Analytics es un servicio interno, puerto predeterminado 8765. Un worker y un
escritor C1 por volumen; no escalar réplicas sobre el mismo repositorio.

| Ruta | Contrato actual |
|---|---|
| POST `/experimental/pmum-estimate` | Seis campos del contrato parental; experimento HU independiente |
| POST `/v1/historical/evaluate` | Sólo `request_id` y `representation` v2; no export crudo ni score PMUM |
| POST `/v1/adult-messages/evaluate` | Evaluación semanal y revisiones; cuerpo completo especificado abajo |
| GET `/v1/adult-messages/profiles/{profile_id}/history` | `{"versions":[{"version":n,"card":{...}}]}`; acceso interno autenticado |
| GET `/health/live`, GET `/health` | Liveness y capacidades/readiness; no prueban calidad o calibración |

Mensajes está deshabilitado por defecto. La plantilla Compose existente habilita
C1/actividades, **no mensajes**. Juanma debe añadir configuración y comprobar el
volumen escribible en su integración. Ejemplo de variables, sin cambiar el perfil:

```text
ANALYTICS_ADULT_MESSAGES_ENABLED=true
ANALYTICS_ADULT_MESSAGES_REPOSITORY_PATH=/var/lib/modera/historical/adult-messages.sqlite3
```

La ruta absoluta SQLite debe ser distinta de la del JSON C1, y persistir aunque
se reinicie el servicio. Perfil C1 y originales HU se montan en sólo lectura;
los almacenes de estado requieren escritura. `/health` incluye `adult_messages`
sólo al habilitarlo. Un store existente incompleto no se recrea vacío para
declarar READY; recuperar la evidencia/almacén, no borrar archivos o marcas.
El paquete no incluye el binario HU ni define un perfil C1 de producto.

## Preparación diaria e identidad

El binding del preparador aporta `profile_id`, `device_id`, `assignment_id`,
`time_zone`, `measurement_version`, fecha local y reloj de preparación. Es
información autorizada del backend, no campos identificatorios deducidos de
fabricante/modelo o del UUID del export. Usar IDs opacos y un namespace que no
mezcle cuentas. Preservar la asociación reversible con sus IDs reales.

Para series nuevas, usar en mensajes el `representation.subject_id` generado
por el preparador, tal como en el ensayo integrado. El backend verifica que
corresponda al perfil declarado. Serie distinta ante cambio real de dispositivo,
asignación, zona o versión de medición/puente/tzdata; no inventarla para evadir
un conflicto. No trasladar CUSUM. Mantener una serie activa seleccionada por
perfil para mensajes: intercalar dos series no equivale a combinarlas; puede
terminar el episodio previo como SERIES_CHANGED.

| Campo hacia mensajes | Procedencia |
|---|---|
| `profile_id` | Binding/asignación autorizada del backend |
| `series_id` | `representation.subject_id` y asociación persistida del preparador |
| `time_zone` | Zona IANA del binding; no zona del PC ni UTC deducido de epoch |
| `days[].date` | `binding.local_date`, cotejada con los límites de la representación |
| `days[].minutes` | `representation.value`, sin redondear antes de decidir |
| `days[].observed` | OBSERVED/OBSERVED_ZERO → true; ausencia/no aplicable → false y minutes=null |
| `days[].revision` | Revisión explícita del backend, empieza en 1 y aumenta al corregir |
| `days[].quality_verified` | Decisión respaldada de calidad del cierre diario; no automática por prepare/HTTP 200 |
| `c1_evidence_ids` | `result.evaluation.evaluation_id` de recibos originales de la misma serie |

`quality_flags` y `coverage` de v2 no son el booleano de calidad de mensajes.
Cobertura desconocida permanece `null`: ni éxito de consulta ni OBSERVED prueban
exhaustividad física. En los ejemplos, calidad y asignación verdaderas se
justifican **sólo por el fixture controlado**. Para reales, guardar la base de esa
decisión por separado. Si no está verificada, enviar false; no forzar apertura.

El preparador trabaja sobre días locales cerrados y distingue cero observado de
MISSING. Respetar límites UTC derivados de la zona, incluidos días 23/25 h;
no añadir otras pantallas registradas manualmente a la duración v2 del teléfono.
EXPORT_PENDING espera; ABSENCE_CONFIRMED no significa cero. Se mantiene el
[preflight de cierre](DAILY_EVIDENCE_CLOSURE_2026-10-12.md); es offline y no una cola.

## Entrada exacta de mensajes

Todos los campos siguientes son obligatorios, sin extras:

| Campo | Tipo / restricción |
|---|---|
| `request_id`, `profile_id`, `series_id` | String no vacío, sin espacios extremos, máximo 128 caracteres; IDs estables controlados por backend |
| `time_zone` | Zona IANA reconocida; no reutilizar serie con otra zona |
| `evaluation_date` | YYYY-MM-DD canónico, lunes, no futuro en esa zona |
| `assignment_verified`, `shared_phone`, `context_declared` | Booleanos explícitos; no strings, null o valores inferidos por defecto |
| `days` | Lista de 0..366 registros; fechas únicas y anteriores a evaluation_date |
| `c1_evidence_ids` | Lista de 0..366 identificadores; `[]` válido. Se deduplica/ordena, no decide la tarjeta |

Cada registro diario tiene exactamente `date`, `revision`, `minutes`, `observed`,
`quality_verified`. Revision es entero >=1, no booleano. Observed/quality son
booleanos; minutes es número finito no negativo dentro de la duración real del
día si observed=true, o null si observed=false. Nunca convertir ausencia en 0.

Primera apertura requiere los 28 días locales completos anteriores al lunes,
todos observados y verificados. Envíos posteriores pueden traer sólo días nuevos
o corregidos: SQLite conserva las ventanas y revisiones anteriores. No reenviar
todo el histórico indefinidamente. El límite HTTP predeterminado sigue en 16384
bytes, adicional al límite de 366 elementos; medir el cuerpo UTF-8 serializado.
El backend debe acotar los lotes y referencias conservando la trazabilidad.
No aumentar límites o omitir datos necesarios para forzar aceptación.

El job semanal corresponde al backend: analytics valida el lunes pero no lo
programa ni garantiza que se ejecutó. Serializar evaluaciones por perfil y
enviar fechas sin retroceder; la misma fecha admite una revisión posterior.

Los cuerpos completos ficticios están en
`examples/adult_messages_2026-10-13/`: petición/respuesta de apertura, respuesta
de retorno e historial. No son solicitudes para una familia real ni referencias
a un repositorio C1 de Juanma. No agregar su metadata ficticia al payload HTTP.

## Reglas ya implementadas

14 contra 14 días; pesos 5/7 hábiles y 2/7 fin de semana. Apertura con diferencia
>=20 min/día en la dirección, resistente a retirar cualquier día de cualquiera
de las dos ventanas, y al menos diez días en esa dirección frente a la referencia
por tipo de día. Disminución usa la regla simétrica.

Una tarjeta/episodio conserva las fechas de referencia. Dejar de cumplir la
apertura no implica retorno: puede quedar INCONCLUSIVE. Retorno exige ventana
reciente sin solapar la de apertura y margen unilateral de 5 min/día, con su
comprobación por exclusión. Máximo 56 días desde apertura, espera de 14 días
desde terminación y una nueva tarjeta por 28 días por perfil, ambas direcciones
compartidas. Las retiradas también cuentan como creadas. Son políticas del
candidato, no umbrales clínicos ni números acreditados por este fixture.

C1 conserva su perfil/referencia; CHANGE no dispara la tarjeta. PMUM no aparece
en este payload ni determina reglas/texto. No quitar mensajes o recomendaciones
del panel por mantener esas separaciones.

## Persistencia, retry y corrección

Hay dos almacenes y dos operaciones independientes: recibo C1 y evaluación de
mensajes. No existe transacción distribuida entre ambos. El backend conserva
durablemente originales, binding, payload congelado y estado de envío **antes**
del HTTP; después enlaza respuesta, configuración, evaluation_id, card_id/version.
Usar el mismo cuerpo original al perder una respuesta. La traza propuesta no
obliga a una tabla o stack que ya exista en el backend.

| Situación | Conducta actual / integración |
|---|---|
| Mismo request de mensajes y mismo contenido | Recibo original, `replayed=true`; no avanza ni duplica |
| Mismo request y contenido cambiado | 409. Una corrección es nueva solicitud/revisión, no retry |
| Contenido equivalente con otro request_id | Replay; no genera tarjeta nueva. Preferir conservar request original |
| Revisión diaria menor o mismo número con contenido distinto | 409; no eludir cambiando IDs o inventando serie |
| Corrección legítima en mensajes | Nuevo request, misma serie/fecha del día y revision mayor; evaluación sin retroceder |
| Apertura invalidada por corrección | Nueva versión WITHDRAWN, conservando originales |
| Tarjeta terminada afectada | Nueva versión WITHDRAWN o CORRECTED_HISTORY; no reapertura retroactiva |
| Evidencia tardía que afecta C1 procesado | Conservar recibo original e incidencia/enlace de revisión. No hay API para sobrescribirlo o reconstruirlo automáticamente |

Una corrección adulta usa las mismas fechas de referencia con sus revisiones
vigentes; «congelada» no quiere decir que se descarten correcciones. Si afecta
C1, el recibo adulto conserva `c1_correction_warning_since` por serie. Los IDs
C1 siguen apuntando a resultados anteriores, no a resultados recalculados.
El backend debe comprobar que existan y correspondan a la serie: el motor
adulto no accede al repositorio C1 ni autentica esos vínculos por sí solo.

Un replay puede devolver una tarjeta antigua ACTIVE aunque ya exista RESOLVED
o WITHDRAWN. Es correcto para auditoría; no usarlo para retroceder el panel.
Consultar history y seleccionar la mayor `version` por `card_id`. Procesar
también `historical_card_corrections`, aunque la respuesta principal no traiga
una tarjeta nueva. No hay que reenviar hasta obtener CREATE o CHANGE.

Una corrección archivada puede conservar `evaluation_date` de la tarjeta
original y añadir `updated_date` de la revisión. Mostrar la fecha de actualización
cuando exista, sin reinterpretarla como otra evaluación original.

## Salida y presentación al adulto

Recibo: `status`, `action` (CREATE/UPDATE/NONE), `evaluation_id`, `card_version`,
`card`, `replayed`, configuración, IDs C1 y campos de corrección. Card incluye
`card_id`, perfil/serie/zona, dirección, estado, `title`, `text`, `recommendation`,
fechas de apertura/comparación, `statistics`, measurement/detail y configuración.
No reducirlo a un semáforo sin explicación/consejo.

| Estado | Presentación coherente |
|---|---|
| ACTIVE / INCREASE o DECREASE | Mensaje de más/menos uso registrado del teléfono, explicación y consejo existentes |
| INCONCLUSIVE | Actualización: seguimos observando; no afirmar recuperación |
| INSUFFICIENT_DATA / CONTEXT_REVIEW | Con card, mostrar su actualización de incertidumbre; sin card, no inventar alerta |
| RESOLVED | Cierre por retorno comparado contra la referencia; no atribuir mejora a Moderá |
| EXPIRED | Fin del seguimiento; no significa resuelto |
| SERIES_CHANGED | Aviso de medición anterior que no puede seguir comparándose |
| WITHDRAWN / CORRECTED_HISTORY | Mostrar última corrección y preservar las versiones auditables |
| NO_CARD / COOLDOWN / CARD_LIMIT | No generar tarjeta adicional; mantener historial vigente |

La vista corta usa título, texto, consejo y fecha; puede ampliar períodos,
cifras y detalle de medición. No presentar minutos del aparato como total de
pantallas ni afirmar diagnóstico, causalidad o felicitación por eficacia.

`delivery_status=CANDIDATE_NOT_DELIVERED` y `push_notification=false` indican que
analytics produjo un DTO, no que el adulto lo leyó. El backend/panel puede mostrar
la tarjeta al integrarse y registrar entrega/lectura en su propia capa. No
reescribir el recibo ni inventar un endpoint ACK/push en analytics. La bandeja
del padre no necesita un push para mostrar sus mensajes persistidos.

## Respuestas HTTP y prueba de aceptación de Juanma

| Respuesta | Acción |
|---|---|
| 200 histórico, incluso ABSTAIN | Guardar recibo; no reintentar buscando CHANGE |
| 200 mensajes, incluso NONE/insuficiente/replay | Guardar evaluación; no tratarlo como pérdida técnica ni publicar tarjeta inexistente |
| 400 | Revisar contrato/preparación. Mensajes: invalid_adult_message_request; no alterar recibos aceptados |
| 401 | Revisar credencial de servicio; autorización familiar es una comprobación adicional del backend |
| 409 | Conciliar identidad, orden, revisión o contenido; no regenerar IDs para saltarlo |
| 413 | Revisar tamaño serializado/lote; el máximo de elementos no garantiza caber en bytes |
| 503 o respuesta perdida | Conservar trabajo y payload; investigar disponibilidad/reintentar de forma durable sin duplicar |

No se fija aquí backoff, deadline de cierre ni migración de datos reales.
Para integrar, acreditar: aislamiento entre padres/perfiles, serie y calendario;
originales/payload durables; pérdida de respuesta y reinicio del backend; una
tarjeta con sus versiones, corrección de archivadas y panel que no retrocede por
replay; y faltantes/calidad desconocida sin tarjeta falsa. Añadir la comprobación
física F12 con su propio protocolo. Esto es aceptación pendiente del backend/UI,
no una afirmación de que Juanma ya la implementó o de eficacia con familias.
