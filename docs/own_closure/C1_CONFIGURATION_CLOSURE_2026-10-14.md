# Tarea 3: configuración y alcance C1 cerrados para la entrega documental

## Decisión y resultado

**Se conserva una configuración de ensayo identificada, no un perfil nuevo de
producto.** Para esta entrega no queda pendiente elegir otro k/h/historia mínima:
se documenta el perfil ya utilizado y su alcance experimental. No se renombran
SMOKE_ONLY, sus versiones o su scope para aparentar calibración. Se conserva la
función de análisis histórico y las tarjetas adultas con explicación/consejo.

Base local verificada `e3031a3e58cfe3dfcb7b3c7b4d09c3efe4477c77`, importada por
Matías; nueva rama `c1-configuration-closure-candidate`. No se tocaron ramas
anteriores, C1, referencia, emisor, API, parámetros, PMUM, catálogo, motor de
mensajes u ofertas. No se publicaron cambios, hizo merge, entrenó un estimador,
ejecutó otro benchmark amplio o inició redacción de tesis. Se agrega únicamente
documentación y evidencia de comprobación.

La decisión de conservar el perfil se justifica por comparabilidad y trazabilidad
con el ensayo integrado y la base estable. La grilla previa no fijó un criterio
de éxito ni seleccionó un perfil; elegir el de mejores cifras ahora sería una
selección posterior. Estos números no provienen de una recomendación clínica,
calibración con familias o aprobación profesional.

## Configuración exacta conservada

| Campo | Valor |
|---|---|
| Archivo | `tests/fixtures/historical_c1_smoke_only.json` |
| configuration_id | `smoke-only-not-calibrated` |
| schema_version / scope | 1 / `internal_technical_candidate` |
| historical_api_version | `historical-http-v1-candidate` |
| representation_spec_id | `daily_use_duration_minutes_v2` |
| reference_policy | `all_prior_usable_records_v1` |
| analysis_version | `published-c1-smoke-v1` |
| emitter_version | `published-crossing-smoke-v1` |
| k / threshold / min_history | 0.5 / 3.0 / 3 |
| configuration_fingerprint | `ced67439a2bf7c4bc4a6f4fc6bec805b404f14c662a927464d026d75d8f46466` |

La huella corresponde al payload canónico, no a saltos de línea del archivo;
se conserva entre Windows/Linux. La API exige ruta absoluta y perfil explícito,
rechaza campos extra/override por petición y liga el repositorio a esa huella.
Cambiar el perfil no permite reutilizar silenciosamente un store previo. La
carga es al iniciar: editar el JSON no cambia a escondidas una sesión activa.

`min_history=3` significa tres registros **previos admisibles**; no tres días
consecutivos, edad de maduración clínica o historia suficiente para cualquier
serie. La cuarta observación sólo puede evaluarse si la referencia es estimable.
Los gaps no se imputan ni reinician estado. k y threshold operan sobre desviaciones
estandarizadas y acumuladas; no son minutos máximos saludables ni probabilidades.

## Funcionamiento conservado y fronteras de calidad

C1 usa mediana y `1.4826*MAD` de los registros previos suministrados. La API
suministra todos los anteriores admisibles de la misma serie/especificación,
incluidos los que tuvieron CHANGE. El actual, futuro o solapado no integra la
referencia del actual. No se agregó una ventana móvil, corte mensual, epsilon,
piso de escala, reset, enfriamiento o compensación por huecos.

Para dato elegible: `z=(x-mediana)/escala`, `G+=max(0,G+ previo+z-k)`,
`G-=max(0,G- previo-z-k)` y estadístico `max(G+,G-)`. CHANGE significa que ese
máximo alcanza threshold. NO_CHANGE significa que no lo alcanza; no acredita
salud, ausencia de uso problemático o ausencia de cambios clínicos.

MISSING/NOT_APPLICABLE, historia insuficiente o referencia no estimable producen
ABSTAIN. Se conserva CUSUM y último estadístico elegible; una observación válida
de inicio puede formar historia aunque todavía no pueda evaluarse. Cero OBSERVED_ZERO
es un dato distinto de ausencia. MAD cero no se convierte en normalidad ni se
corrige agregando ruido para forzar resultados.

**Admisibilidad matemática no equivale a captura verificada.** La versión del
núcleo no excluye por umbrales de coverage o quality_flags. La API admite coverage
desconocida y conserva flags/procedencia; un valor OBSERVED finito puede alimentar
la referencia aun con coverage=null. No se afirma que C1 se abstenga por cualquier
calidad desconocida. La calidad completa del ensayo se conoce por su oráculo
controlado, no porque el preparador terminó. La política adulta exige su propio
quality_verified y puede abstenerse aunque C1 calcule CHANGE.

Para captura real debe resolverse en la integración el significado admisible de
OBSERVED, cobertura/calidad, identidad, discontinuidades y cierre del intervalo.
No se añade aquí una guarda cuantitativa o filtro no justificado al núcleo. La
captura y validación física continúan diferidas por Matías, con este criterio
registrado; no se certifican por este cierre documental.

## Resultado, evento y mensaje: decisión explícita

| Capa | Responsabilidad implementada | Relación con otras capas |
|---|---|---|
| C1 | Evidencia secuencial y recibo de cada representación | No estima PMUM ni recomienda actividades |
| Emisor C1 | EMIT sólo con estadístico elegible previo <threshold y actual >=threshold | Primera excedencia con previo None no emite; CHANGE repetido no genera un evento diario |
| Interpretación existente | Descripción del valor frente a referencia cuando hay evento | No transforma ese valor ni su dirección en diagnóstico, persistencia o consejo |
| Motor adulto | Tarjetas de aumento/disminución, actualización/retorno y consejo con regla 14/14 y guardas propias | C1 es evidencia complementaria enlazada; ni requisito ni veto |
| Coordinador infantil | Activación y coordinación diurno/descanso conforme a su contrato | Sin score PMUM o C1 como disparador |
| PMUM HU v1 | Estimación interna experimental con respuestas parentales explícitas | No modifica C1 ni la frecuencia de actividades o mensajes |

El emisor usa el máximo bilateral; el estado elevado puede persistir tras un
pico, y un cruce de un lado puede quedar enmascarado por el otro. EMIT es un evento
técnico, no duración de un episodio de aumento ni nueva tarjeta. ABSTAIN no
certifica salida. No se prometen reset/rearm/cooldown nuevos en C1: la política
de espera/cupo de tarjetas pertenece al motor adulto ya implementado.

La política adulta conserva su comparación de 14 contra 14 y evaluación prevista
cada siete días, referencias congeladas, cupos y versiones originales. No se
intercambia con la referencia expansiva de C1 ni se cambia porque C1 no emita.
Su clasificación no necesita convertir un estadístico CUSUM en promedio semanal
o mensual. Las vistas por períodos requieren observaciones originales.

La falta de un perfil C1 calibrado no elimina las tarjetas al padre. Tampoco
una aprobación del catálogo de Cecilia validaría automáticamente los parámetros
C1, las métricas PMUM o la comprensión de los mensajes.

## Evidencia acumulada cotejada

1. El benchmark exploratorio 13/10 conserva 600 series ficticias, 24 configuraciones,
   14.400 recorridos y 1.612.800 evaluaciones. Su protocolo declara que no selecciona
   perfil de producto. No se volvió a correr. Se comprobaron los seis hashes de
   salidas guardadas; sus 14 blobs del núcleo coinciden con los actuales.
2. Su auditoría independiente previa registra PASS para esas evaluaciones. Ese
   PASS no se atribuye a otra ejecución nueva de este bloque. La suma de ABSTAIN,
   NO_CHANGE y CHANGE coincide con el total; EMIT es un subconjunto, no otro grupo
   que deba sumarse como evaluación adicional.
3. S0 tiene nivel del generador fijo con ruido, no etiquetas clínicas de normalidad.
   Un pico puede emitir y dejar CHANGE durante muchos registros; patrones semanales
   pueden permanecer elevados sin nuevos eventos. No se elige una configuración
   de la grilla para minimizar emisiones ni se asigna valor clínico a esos conteos.
4. F12-B2 es descriptivo sobre trayectorias humanas; F12-C2 mide perturbaciones
   semisintéticas con referencias de fondo no perturbado. No equivale a incorporar
   datos alterados a la referencia expansiva de API. Offsets son registros, no
   necesariamente días, y sus ventanas solapadas no son muestras independientes.
   La evidencia no acredita población argentina de 6–12 ni ground truth clínico.

## Comprobaciones de este bloque

- **69 tests focalizados aprobados, 42 subtests, 17 deseleccionados**, una advertencia
  heredada, 1,52 s. Referencia, elegibilidad, detector, emisor, orquestación y casos
  de configuración/identidad/replay/coexistencia de API. No son otra suite global.
- Perfil y huella: PASS. Coincidencia de los 14 blobs del benchmark: PASS.
  Hashes de seis salidas originales guardadas: PASS, sin recalcular detector.
- **Tres casos ficticios acotados** usando servicios/adaptadores existentes:

| Caso controlado | C1 | Tarjeta adulta | Qué comprueba |
|---|---|---|---|
| Export con variabilidad determinista, 100→140 | 3 ABSTAIN, 11 NO_CHANGE, 14 CHANGE | ACTIVE | Recorrido ya existente, evidencia ligada, reinicio/replay y bytes originales conservados |
| Mismo export, calidad retenida en un día | Mismos resultados C1 | INSUFFICIENT_DATA | C1 no publica por sí solo; quality_verified del mensaje tiene efecto propio |
| Servicio canónico: 14×100 y 14×140, sin variabilidad | 28 ABSTAIN por arranque/MAD cero | ACTIVE | La tarjeta no requiere C1 elegible/EMIT; datos construidos completos, no captura real |

El primer intento de comprobación asumió erróneamente que el fixture de export
era constante. Se revisó su vector planificado, que incluye variación diaria
determinista. Se corrigió la expectativa del ensayo; **no el código, parámetros
o datos del helper**. El caso constante se construyó por separado y se identifica
como fixture de servicios canónicos, sin atribuirle el recorrido export.

Los tres casos son ficticios y sus condiciones conocidas justifican la calidad
del ensayo. Cobertura de representación continúa null; no se convirtió en uno.
El tercer caso no acredita reinicio/export físico. Los dos primeros reutilizan
el ensayo integrado, incluyendo replay original y ausencia de duplicación.

## Matriz final de afirmaciones

| Afirmación prevista | Estado / formulación defendible |
|---|---|
| Hay un analizador secuencial implementado | Sí; conserva referencia robusta, CUSUM bilateral, eventos y recibos |
| Usa una configuración concreta | Sí; el perfil de ensayo identificado arriba, conservado sin selección nueva |
| Se eligió el perfil óptimo/calibrado para niños | No; no es afirmación de esta entrega |
| Detecta siempre cambios de uso o distingue pico/escalón | No; resultados condicionados y contraejemplos registrados |
| Tiene sensibilidad/FPR clínica o ARL garantizado | No; faltan etiquetas/supuestos que permitan esas afirmaciones |
| La preparación exitosa demuestra captura completa | No; calidad verificada requiere evidencia aparte |
| C1 decide las recomendaciones al padre | No; la capa adulta implementada decide con datos y guardas propios |
| C1 carece de función porque no es gate | No; conserva evidencia secuencial, historial y trazabilidad independientes |
| PMUM controla C1/actividades/tarjetas | No; se conserva el contrato actual |
| La captura/entrega/calibración real está acreditada | No; diferida y separada de la demostración interna |

**La tarea 3 queda cerrada para esta entrega documental.** No hay defecto
demostrado del núcleo que requiera una modificación ni otro perfil interno
pendiente de seleccionar. Al retomar uso real, la selección/calibración, datos
de captura y validación deberán tratarse con objetivos y evidencia propios;
este documento no fabrica ese cierre futuro. La tarea 4 de privacidad permanece
como siguiente bloque; no se ejecutó automáticamente.
