# F16: revisión profesional del catálogo infantil (instrumento pendiente de aplicar)

## Propósito y alcance

Este documento prepara la revisión de las 18 actividades actualmente presentes
en `recommendations.py` para niños de 6 a 12 años. El catálogo y las reglas
de elegibilidad son **provisionales**. Su presencia en el código no significa
que una persona profesional haya elegido, aprobado o validado las actividades.

La revisión busca decidir qué conservar, adaptar, retirar o agregar y en qué
condiciones podría ofrecerse cada actividad. No pretende demostrar eficacia,
diagnosticar uso problemático ni reemplazar una evaluación de producto con
niños y familias. Se puede realizar primero mediante una revisión de escritorio
con profesionales, sin desplegar la app durante un mes en familias.

## Registro de la revisión

Completar por cada profesional y ronda. Guardar la versión del catálogo
revisada y el material de respuesta, con permiso para citar su devolución.

| Campo | Respuesta |
| --- | --- |
| Fecha y modalidad | Pendiente |
| Rol/especialidad y experiencia pertinente | Pendiente |
| Versión examinada | `phase14-integration` en `6db2e01`; actualizar si cambia |
| Actividades y textos efectivamente recibidos | Pendiente |
| Alcance de su revisión y límites declarados | Pendiente |
| Autorización para atribuir o citar la devolución | Pendiente |

Si distintas personas revisan desarrollo infantil, accesibilidad, sueño o
actividad física, registrar sus juicios por separado. Una opinión sobre un área
no se presenta como validación de las demás.

## Preguntas comunes para cada actividad

1. ¿La propuesta y su redacción son apropiadas para 6 a 12 años? Indicar si
   requiere variantes por edad o por nivel de lectura y comprensión.
2. ¿Es voluntaria, factible en el hogar y comprensible sin inducir culpa o
   presión? ¿Qué materiales, espacio, tiempo o acompañamiento requiere?
3. ¿Qué capacidades funcionales presupone? ¿Qué variantes equivalentes
   propondría para limitaciones permanentes o transitorias? Si no existe una
   variante adecuada, ¿en qué contexto debería abstenerse el sistema?
4. ¿Es razonable ofrecerla antes de dormir? Revisar por separado las etiquetas
   `bedtime_suitable` y `activity_level`, sin asumir que ya están validadas.
5. ¿La etiqueta de dispositivo u otra persona es correcta? ¿El texto necesita
   condiciones de seguridad, disponibilidad o acompañamiento más explícitas?
6. Decisión por actividad: **conservar / adaptar / retirar / pendiente**.
   Registrar texto alternativo, condiciones, motivo y evidencia o criterio
   profesional. Dejar `pendiente` cuando no pueda evaluarse con lo entregado.

## Catálogo que debe examinarse

La columna de foco plantea preguntas de auditoría del equipo; **no constituye
un dictamen profesional**. Los títulos e identificadores corresponden al código
en `6db2e01`; entregar también las descripciones completas de
`recommendations.py` al profesional.

| ID | Actividad | Contextos actuales | Foco para la revisión |
| --- | --- | --- | --- |
| `movement_dance_01` | Bailá una canción | Voluntario, general | Música y posible uso del dispositivo; variantes de movimiento |
| `movement_sequence_01` | Armá una secuencia de movimientos | Voluntario, general | Saltar, girar o agacharse como ejemplos; espacio y alternativas accesibles |
| `movement_ball_01` | Jugá con una pelota | Voluntario, general | Disponibilidad de pelota, espacio seguro y adaptación motriz |
| `creative_character_01` | Inventá un personaje | Voluntario, general, descanso | Dibujo, materiales y variantes de expresión |
| `creative_animal_01` | Creá un animal imaginario | Voluntario, general, descanso | Dibujo y materiales; adecuación por edad |
| `creative_favorite_01` | Dibujá algo que te guste | Voluntario, general, descanso | Libertad de elección y alternativas al dibujo |
| `creative_story_01` | Inventá una historia | Voluntario, general, descanso | Escritura/dibujo, comprensión lectora y variantes orales |
| `reading_choose_01` | Elegí algo para leer | Voluntario, general, descanso | Disponibilidad de lectura, nivel lector y variantes accesibles |
| `reading_favorite_01` | Volvé a una historia que te guste | Voluntario, general, descanso | Material conocido, nivel lector y adecuación al descanso |
| `free_play_nearby_01` | Jugá con algo que tengas cerca | Voluntario, general | Materiales disponibles y juego autónomo |
| `free_play_build_01` | Construí algo | Voluntario, general | Piezas disponibles, manipulación y seguridad según edad |
| `free_play_story_01` | Creá una historia con tus juguetes | Voluntario, general | Disponibilidad de juguetes y otras formas de narrar |
| `social_play_01` | Jugá con alguien | Voluntario, general | Disponibilidad y voluntad de otra persona de confianza |
| `social_talk_01` | Contá algo de tu día | Voluntario, general, descanso | Privacidad, voluntad del niño y persona disponible |
| `social_help_01` | Ayudá con algo | Voluntario, general | Riesgo de convertir una pausa voluntaria en obligación doméstica |
| `social_story_01` | Escuchá una historia | Voluntario, general, descanso | Persona disponible y variantes sin lectura o pantalla |
| `quiet_prepare_01` | Prepará algo para mañana | General, descanso | Adecuación a la rutina familiar y carga de tarea antes de dormir |
| `quiet_draw_01` | Hacé un dibujo tranquilo | Descanso | Materiales, variantes accesibles y adecuación al descanso |

## Plantilla de dictamen por actividad

Duplicar este bloque para cada ID. No reemplazar un dictamen concreto por una
aprobación general del catálogo.

| Campo | Registro |
| --- | --- |
| ID, título y versión del texto revisado | Pendiente |
| Decisión: conservar / adaptar / retirar / pendiente | Pendiente |
| Edades y contextos en que se aplicaría | Pendiente |
| Capacidades, materiales, apoyo y condiciones necesarios | Pendiente |
| Variante accesible o condición de abstención | Pendiente |
| Texto o metadatos propuestos | Pendiente |
| Fundamento y límites de la recomendación | Pendiente |
| Profesional, fecha y ronda | Pendiente |

## Revisión de reglas transversales

Pedir además una devolución diferenciada sobre: la solicitud voluntaria; la
transición previa al descanso; la opción de no ofrecer ninguna actividad; los
filtros funcionales; la variedad de categorías; y el refuerzo provisional por
elecciones repetidas. Una elección registrada no demuestra realización ni
beneficio. Una oferta generada no demuestra que el niño la vio.

El profesional puede recomendar otra estructura de catálogo o descartar la
ponderación actual. Tras recibir sus observaciones, registrar una matriz
`versión inicial → observación → decisión → cambio de requisito/catálogo/código`
con responsables y pruebas. Solo entonces actualizar textos y condiciones,
conservar identificadores históricos o versionarlos explícitamente, y preparar
la evidencia para la entrega académica. No atribuir aprobación profesional
antes de completar y conservar esas respuestas.
