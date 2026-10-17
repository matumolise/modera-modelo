# Coordinador infantil: interfaz HTTP v1

Fecha: 17/10/2026. Complementa `docs/own_closure/CHILD_COORDINATOR_CONTRACT_2026-10-14.md`.
Se añade transporte al coordinador existente, sin modificar `POLICY`, catálogo,
selector, cálculo de cupos o persistencia. Los nuevos subtipos de `ValueError`
permiten distinguir conflictos y almacenes no disponibles. Los mensajes de las
excepciones existentes se conservan.

## Capacidad y almacenamiento

Por defecto la capacidad está deshabilitada. Para habilitarla:

```text
ANALYTICS_CHILD_OFFERS_ENABLED=true
ANALYTICS_CHILD_OFFERS_REPOSITORY_PATH=/ruta/absoluta/coordinator.sqlite
```

Inicializar una base nueva es una operación explícita, anterior al servidor:

```text
python -m analytics_service.initialize_child_offers --path /ruta/absoluta/coordinator.sqlite
```

La misma operación valida una base existente sin reiniciarla. Una base existente
vacía, incompleta o incompatible se rechaza. No ejecutar este comando
automáticamente en cada arranque ni utilizarlo para sustituir una base perdida.
Ante pérdida, restaurar la evidencia y sus dependencias mediante recuperación
explícita. El servidor reabre con `create=False` y falla al arrancar si falta la base.

El archivo debe ser independiente del histórico, mensajes, configuración y
artefactos de modelo. La configuración rechaza rutas idénticas. El operador debe
evitar también alias, enlaces duros y montajes que hagan coincidir los soportes.
El contenedor utiliza un volumen persistente y un único proceso del servicio.
No se acredita recuperación ante corrupción arbitraria o pérdida del volumen.

## Confianza, privacidad y formatos

- API interna para backend autorizado. Todas las rutas siguientes requieren
  `Authorization: Bearer <token>` y los POST `Content-Type: application/json`.
- El token de servicio no se entrega a Android ni sustituye la autorización de
  cuenta/perfil. El backend resuelve pertenencia, asignación, contexto y permisos.
- IDs ASCII globalmente delimitados por cuenta: letras, números, `_`, `-` o `.`,
  de 1 a 128 caracteres. Un `profile_id` entero legado no acredita aislamiento.
- La captura, el juego y la escuela no se infieren aquí. El adaptador confiable
  aporta los hechos. Si no puede verificarlos, no inventa valores para habilitar
  una oferta. `capture_verified` no significa solamente que una consulta terminó.
- Se conservan las restricciones de transporte previas: autenticación antes de
  leer el cuerpo, JSON estricto, máximo 16 KiB y plazo de recepción de 10 segundos.
  Las respuestas incluyen `Cache-Control: no-store`.
- Datos del almacén pseudonimizados, no anónimos. Restringir acceso, retención,
  respaldo y eliminación conforme al contrato de privacidad del componente.

## 1. Evaluar una oportunidad

`POST /v1/child-offers/evaluate`

```json
{
  "request_id": "fictitious-evaluation-001",
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
  }
}
```

Ejemplo enteramente ficticio. La fixture ejecutable está en
`tests/fixtures/integration/child_offer_evaluation_fictitious.json`.
El sobre exige exactamente `request_id` y `evidence`. La evidencia exige los
campos del contrato `OfferEvidence`, salvo `interests` y `eligibility`, que
conservan sus valores predeterminados. No se admiten campos adicionales.

Para elegibilidad `known`, los filtros deben ser explícitos y válidos mediante
el selector existente. `{}` declara ausencia conocida de exclusiones operativas,
no aprobación profesional del catálogo. Para `unknown`, omitir `eligibility` o
usar `null`: el coordinador se abstiene. No enviar `{}` para ocultar desconocimiento.
`interests`, cuando aparece, es una lista JSON con el vocabulario del selector.

Los tiempos tienen offset y no se sustituyen por la zona del servidor.
`bedtime_at` es el próximo instante de descanso ya resuelto por el llamador.
La integración resuelve la zona, los cambios de hora y el calendario escolar.
`interval_id` conserva el inicio de un intervalo continuo verificado. Un
reinicio, cambio de canal o petición nueva no inicia otro intervalo.

Una respuesta HTTP 200 puede contener `status: offer` o `status: suppressed` y
su motivo. En el primer caso incluye `offer`, `channel`, `policy_version` y
`replayed`. La oferta contiene ID, lista, selección, contexto, fechas, estado,
canales y evidencia conforme al DTO de la biblioteca. No se reformatea ni se
eliminan campos respecto de ese DTO. La generación no acredita entrega.

## 2. Registrar entrega o respuesta

`POST /v1/child-offers/events`

```json
{
  "request_id": "fictitious-delivery-001",
  "profile_id": "fictitious-account.child-001",
  "offer_id": "REEMPLAZAR_POR_EL_ID_RECIBIDO",
  "event": "delivered",
  "occurred_at": "2026-10-16T10:00:00-03:00",
  "now": "2026-10-16T10:00:00-03:00",
  "channel": "overlay"
}
```

Es un ejemplo ficticio con un marcador que debe reemplazarse. Los seis primeros
campos son obligatorios. `channel` y `selected_activity_id` son opcionales.
No se aceptan otros campos.

Eventos de la biblioteca: `delivered`, `delivery_failed`, `selected`, `rejected`,
`postponed`, `dismissed`. `delivered` requiere `channel: notification` u `overlay`.
Los otros eventos no admiten canal distinto de `null`. `selected` exige una
actividad de la lista ofrecida en `selected_activity_id`. Los demás no admiten
un ID de actividad distinto de `null`.

`occurred_at` representa el momento real declarado del evento, mientras que
`now` corresponde a su procesamiento. No se inventa una entrega para habilitar
selección. Los eventos tardíos se validan con las reglas originales. El
resultado HTTP 200 conserva `status: recorded`, oferta y recibo.

La selección automática no se escribe también en el JSONL legado. El backend
debe evitar duplicarla en su contador voluntario o en otro almacén sin una
coordinación explícita. El evento de selección no acredita actividad completada.

## 3. Consultar historial

`GET /v1/child-offers/profiles/{profile_id}/history`

Devuelve el DTO actual de la biblioteca: `offers` y `events`. Un perfil aún
ausente devuelve ambas listas vacías y no crea un perfil. La consulta no avanza
el reloj ni vence ofertas. No es una orden de mostrar automáticamente la oferta
que aparezca en el historial.

## Reintento, presentación y estados HTTP

El `request_id` es único en todo el almacén, incluidos los dos POST y todos los
perfiles. Un retry conserva todos sus campos, especialmente `now`. Devuelve el
recibo original más `replayed: true`, sin volver a generar ni escribir eventos.
Un nuevo ID representa otra operación, no una forma de eludir conflictos.

Un recibo reproducido puede describir una oferta antigua. Antes de mostrar una
oferta se necesita evaluación fresca, mismo `offer_id`, vigencia y deduplicación
por canal. No inferir permiso de presentación de una respuesta histórica.

| Estado | Significado y tratamiento |
| --- | --- |
| 200 | Operación registrada o supresión válida. No garantiza entrega ni realización. |
| 400 | Forma o valores inválidos. Corregir la petición, sin completar datos por inferencia. |
| 401 | Credencial de servicio ausente o incorrecta. |
| 409 | Identidad, cronología, pertenencia o transición incompatibles. Conservar la petición y conciliar. |
| 413 / 415 | Cuerpo excesivo o tipo de contenido incorrecto. |
| 503 | Capacidad deshabilitada o almacenamiento no disponible. No inicializar otra base para continuar. |

Las operaciones reutilizan excepciones compatibles con `ValueError`, ahora
distinguidas como `CoordinatorConflict` y `CoordinatorUnavailable`. Los errores
HTTP son códigos estables, sin divulgar rutas internas ni detalles de otro perfil.

`GET /health` incluye `child_offers` solo cuando se habilita, con versión HTTP
`child-offers-http-v1`, versión de política y catálogo provisional. La comprobación
de disponibilidad no crea recibos. `/health/live` informa únicamente que el
proceso sigue vivo. Estas rutas no acreditan captura Android, acceso por familia,
entrega visual o aprobación profesional.
