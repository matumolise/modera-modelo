# F16: evaluación de IA para actividades infantiles (decisión abierta)

## Estado comprobado en `312c1ec`

- El modelo PMU y el selector de actividades son flujos separados. No usar
  scores PMU, cambios CUSUM ni riesgo para elegir actividades infantiles.
- El selector infantil filtra contexto y elegibilidad, considera intereses,
  repetición y variedad, y admite un refuerzo provisional de elecciones
  vinculadas. Sus pesos fueron definidos como parámetros operativos: no son
  evidencia de eficacia ni constituyen por sí mismos un modelo entrenado.
- El repositorio contiene 18 actividades provisionales y un instrumento de
  revisión profesional todavía sin respuestas. El JSONL incluido tiene nueve
  respuestas legadas y ningún par nuevo de oferta-respuesta válido para
  personalización. Pruebas sintéticas verifican el software, no la utilidad
  para niños reales.
- Una oferta persistida indica generación/registro, no visualización. Una
  selección indica elección observada, no realización, agrado duradero ni
  reducción de tiempo de pantalla causada por la actividad.

## Opciones para una evaluación comparativa

| Opción | Función posible | Datos y evaluación necesarios | Decisión actual |
| --- | --- | --- | --- |
| A. Selector actual | Referencia reproducible y explicable | Revisión profesional del catálogo y prueba de elegibilidad/variedad | Mantener como línea de base |
| B. Ranking aprendido sobre catálogo aprobado | Ordenar solo actividades elegibles usando elecciones del mismo niño/contexto | Ofertas efectivamente mostradas, opciones y posiciones, selección, política que las eligió, consentimiento y volumen suficiente; comparar con A | Investigar después de instrumentar y reunir datos |
| C. IA para proponer o adaptar textos *fuera* del flujo infantil | Generar borradores que profesionales revisen, aprueben y versionen antes de incorporarlos | Conjunto de escenarios de edad/capacidad, rúbrica profesional y registro de rechazos/correcciones | Prototipo acotado a evaluación, sin publicación automática |
| D. Generación libre de actividades en tiempo real para el niño | Inventar contenido al momento | Control y revisión de seguridad, accesibilidad, privacidad, coherencia y trazabilidad de cada salida; mecanismo de abstención | No integrar en la app con la evidencia actual |

Las opciones no son etapas obligatorias. Que la tesis requiera IA no demuestra
que el motor infantil necesite un modelo generativo: documentar por separado
qué función académica cumple el modelo PMU y qué evidencia pedirían los
profesores para una eventual IA adicional en actividades.

## Condiciones antes de experimentar con ranking aprendido

1. Obtener decisiones profesionales por actividad y reglas de elegibilidad.
   Versionar textos, metadatos y las adaptaciones aprobadas; retirar o poner
   en pausa actividades pendientes cuando corresponda.
2. En la app, distinguir oferta generada de opción realmente presentada y
   selección del niño. Registrar identificador/versión de cada alternativa,
   contexto, orden mostrado y política que produjo la lista. No inferir
   visualización ni rechazo a partir del archivo actual.
3. Definir uso y conservación mínimos de datos infantiles, control de acceso
   y forma de solicitar consentimiento o autorización aplicable. Evitar
   enviar diagnósticos, métricas crudas o perfiles identificables a un modelo
   externo para este experimento.
4. Predefinir la variable objetivo y sus límites: elección de una actividad
   **entre opciones visibles**, no cumplimiento, beneficio clínico ni tiempo
   sin pantalla. Un modelo que optimiza solo elecciones podría concentrar
   repetidamente la oferta en opciones familiares.
5. Comparar A y B primero fuera de línea con separación temporal y por niño,
   sin entrenar y evaluar sobre elecciones de la misma trayectoria. Medir
   cobertura, diversidad, frecuencia de abstención, violaciones de
   elegibilidad, cambios por contexto y concentración de opciones; incluir
   casos de capacidades y apoyos distintos. Una mejora de predicción no
   sustituye aprobación profesional o evaluación con usuarios.
6. Registrar antes de experimentar qué resultado justificaría pasar de la
   línea de base a un modelo, quién revisará los casos problemáticos y cómo
   volver a la línea de base. Sin muestras reales suficientes, informar la
   limitación y mantener B como investigación, no como componente validado.

Un bandit contextual es una posibilidad de investigación posterior, no una
recomendación de implementación inmediata. Estos métodos requieren definir
acciones, feedback y política de registro; los experimentos de recuperación
de información no demuestran seguridad o eficacia en Moderá.

## Protocolo acotado para evaluar generación/adaptación

- Solicitar al profesional escenarios y restricciones funcionales relevantes,
  incluidos casos donde corresponde abstenerse. No inventar una lista de
  discapacidades a partir de métricas de uso.
- Construir prompts con datos mínimos y ejemplos aprobados. Generar borradores
  para revisión adulta fuera de la app, conservando entrada, salida, versión
  del modelo, fecha y decisiones de aprobación/rechazo.
- Pedir evaluación ciega de borradores frente a textos escritos o adaptados
  manualmente, mediante rúbrica de adecuación por edad, accesibilidad,
  factibilidad, autonomía del niño, seguridad y claridad. Registrar desacuerdos
  y motivos; no publicar salidas que sigan pendientes.
- Solo considerar una variante que supere una revisión profesional y una
  prueba técnica de abstención, mantenga el catálogo versionado y ofrezca una
  alternativa estable cuando falle. No atribuir a la IA un efecto sobre el
  tiempo de pantalla por una pausa observada.

## Fundamento y límites de las fuentes

UNICEF propone seguridad, privacidad, no discriminación, explicabilidad e
inclusión al diseñar IA para niños. La guía de la OMS aborda gobernanza de
modelos generativos en salud; sirve para plantear revisión y límites, no como
aprobación de una actividad concreta. El trabajo de Jagerman, Markov y de
Rijke estudia exploración segura en ranking de información: fundamenta por
qué conviene comparar contra una política base, pero sus resultados no se
trasladan como validación clínica o infantil de Moderá.

Referencias (formato ISO 690, consulta: 29 septiembre 2026):

- UNICEF INNOCENTI. *Guidance on AI and children*, versión 3.0 [en línea].
  Disponible en: https://www.unicef.org/innocenti/reports/policy-guidance-ai-children
- WORLD HEALTH ORGANIZATION. *Ethics and governance of artificial intelligence
  for health: Guidance on large multi-modal models* [en línea]. 2025.
  ISBN 978-92-4-008475-9. Disponible en:
  https://www.who.int/publications/i/item/9789240084759
- JAGERMAN, Rolf; MARKOV, Ilya y DE RIJKE, Maarten. *Safe Exploration for
  Optimizing Contextual Bandits* [en línea]. 2020. DOI:
  10.48550/arXiv.2002.00467. Disponible en: https://arxiv.org/abs/2002.00467
