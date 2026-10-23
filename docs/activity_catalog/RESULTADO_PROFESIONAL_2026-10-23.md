# Resultado de la revisión profesional incorporada

La entrega parte de `1445056ad13728fba5aaabec6a61aa9bbd1730c3`. El código y las
pruebas comprobados corresponden al árbol conservado en
`93a507cf09e8060154c381c803e404cd45eef524`. Los commits posteriores de entrega
solo agregan documentación y evidencia. Las huellas del código comprobado se
conservan en `evidence/2026-10-23/RESULTADOS.json`.

## Cambios y comprobaciones

| Comprobación | Resultado |
| --- | --- |
| Catálogo | 16 actividades activas, dos fusiones con IDs nuevos y las variantes de dibujo por contexto conservadas. |
| Revisión profesional | Segunda devolución recibida el 22/10 e incorporada con decisiones editoriales y técnicas registradas. Originales identificados por SHA-256 y transcripción con colores conservada. |
| Pruebas focalizadas Linux | 167 aprobadas y 45 subtests. |
| Regresión completa Linux | 536 aprobadas y 192 subtests, sin fallas finales. |
| Consignas por HTTP interno | Las 16 respuestas coinciden con título, descripción completa y esquema conservado. Se exporta una copia legible mediante el nuevo verificador. |
| Exclusiones anteriores | Las cuatro exclusiones de predecesores también bloquean la propuesta fusionada, tanto en selección directa como HTTP y reconciliación del coordinador. |
| Actualización desde 1445056 | 15 almacenes ficticios generados por el código original: ofertas pendientes, entregadas y respondidas de los cuatro IDs fusionados y una actividad conservada. Se reabrieron y recuperaron recibos originales sin alterar contenido persistido. |
| Historial anterior a 1445056 | Se conservan las comprobaciones con recibos de `04f1e3a`, incluida respuesta a IDs ya retirados. |
| HTTP nativo y proceso reiniciado | PASS con datos ficticios: ofertas, entrega, selección, mensajes adultos, C1 técnico, recibos originales y ausencia de duplicados. |
| Alcance de producción | 44 archivos de núcleo histórico, servicios analíticos, modelos experimentales, Docker y configuración comparados byte a byte con la base, sin cambios. El selector y el esquema de actividad conservan su código. |

La primera regresión detectó un dato obsoleto en una prueba: intentaba crear una
oferta nueva con `creative_story_01`, ahora retirado. Se actualizó ese caso para
usar un ID vigente. No se permitió crear ofertas nuevas con actividades retiradas.
La ejecución fallida inicial y la ejecución corregida se conservan separadas.

Las pruebas heredadas agregaron ocho filas ficticias a
`data/intervention_history.jsonl`. Se conservaron esas filas como evidencia y se
restauró únicamente ese archivo al contenido original, sin borrar resultados.

El reporte JUnit incluye los subtests como casos adicionales: 212 casos en el
focalizado y 728 en el completo. No deben confundirse con 212 o 728 pruebas
principales más los subtests. Los recuentos principales son 167 y 536.

## Versiones y límites

- Catálogo: `provisional-sha256:976271d8f060d4fb9c1cc09ea1f2210d0726f0b391da64ed745e0fe1bed7ccd4`.
- Selector: `published-selector-sha256:f0c44edc74e0dff72163c593ea56298ce56050cf9aca2fd77c9a3ac6be6f5ace`.
- Compatibilidad de exclusiones: `explicit-exclusions-merged-activities-v1`.
- Linux y Python 3.12. No se ejecutó Windows aquí.
- Docker no está disponible en este entorno. No se atribuye a esta versión la
  comprobación Docker de `1445056` ni un despliegue en AWS o Android.
- La configuración de PMUM y C1 de AWS sigue siendo la de la integración real.
  Este cambio no los habilita. El ensayo local de C1 conserva SMOKE_ONLY.
- Se conserva la advertencia de deprecación de Starlette/httpx ya existente.
  No se cambiaron dependencias para esta revisión.
- El mapeo de restricciones del formulario del backend continúa separado. La
  revisión profesional de contenido no convierte una etiqueta en autorización
  automática ni acredita eficacia con niños.

No se publicaron ramas, hicieron merges, entrenaron modelos, ejecutaron nuevos
benchmarks ni modificaron el PDF, la presentación, backend o Android de Juanma.
La incorporación a esos componentes debe documentarse una vez realizada.
