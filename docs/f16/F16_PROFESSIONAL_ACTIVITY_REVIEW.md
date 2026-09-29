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

La búsqueda complementaria realizada antes de esta consulta no encontró una
evaluación directa del catálogo de Moderá ni de estas consignas concretas en
niños de 6 a 12 años. Es un límite de la búsqueda, no una prueba de que tales
estudios no existan ni de que las actividades sean eficaces o ineficaces.

**Resumen para quien revisa:** Moderá es un proyecto académico de una app para
niños de 6 a 12 años y sus adultos responsables. Una función infantil propone
pausas voluntarias y, en un contexto separado, opciones tranquilas durante la
transición al descanso. No bloquea el dispositivo ni deriva actividades de
un diagnóstico o de un score PMU. Queremos que usted cuestione el catálogo y
sus condiciones; una decisión `retirar` o `pendiente` es un resultado útil.
No se le pide que certifique eficacia clínica ni que avale el proyecto entero.

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
   ¿Qué información puede aportar el niño y cuál necesita confirmar un adulto?
   ¿Cómo debería actualizarse una restricción transitoria sin inferir
   capacidades a partir de un diagnóstico?
4. ¿Es razonable ofrecerla antes de dormir? Revisar por separado las etiquetas
   `bedtime_suitable` y `activity_level`, sin asumir que ya están validadas.
5. ¿La etiqueta de dispositivo u otra persona es correcta? ¿El texto necesita
   condiciones de seguridad, disponibilidad o acompañamiento más explícitas?
6. Decisión por actividad: **conservar / adaptar / retirar / pendiente**.
   Registrar texto alternativo, condiciones, motivo y evidencia o criterio
   profesional. Dejar `pendiente` cuando no pueda evaluarse con lo entregado.

## Evidencia que motiva preguntas, no aprobación del catálogo

| Tema | Hallazgo y límite | Pregunta para la revisión |
| --- | --- | --- |
| Perspectivas sobre capacidad | En PEGS, 117 niños de 6 a 9 años con discapacidades, sus padres y docentes aportaron percepciones diferentes sobre actividades cotidianas; el instrumento no valida filtros automáticos de esta app [1]. | ¿Cómo combinar lo que el niño quiere intentar con la información adulta sobre apoyos y condiciones de seguridad, sin excluirlo por diagnóstico? |
| Descanso | Un análisis secundario de un ensayo en 66 niños de 8 a 11 años examinó una intervención conductual con adultos sobre horarios y rutinas [2]. No evaluó dibujos, lectura ni las sugerencias de Moderá. Un experimento de luz nocturna midió melatonina en submuestras pequeñas, no calidad de sueño tras una actividad [3]. | ¿Conviene mantener actividades infantiles durante la transición al descanso? ¿Qué debe decidir la familia sobre horarios, luz y materiales? No convertir las mediciones de melatonina en instrucciones automáticas de iluminación. |
| Lectura | Estudios de entrega de libros y lectura guiada examinaron resultados de alfabetización bajo condiciones distintas a una pausa voluntaria [4, 5]. | ¿Hace falta ofrecer opciones accesibles según lectura, materiales y apoyo disponibles? No atribuir a esta consigna un efecto lector demostrado. |
| Registro de uso | La implementación registra una oferta generada y puede vincular una elección, pero todavía no acredita visualización ni realización. Una selección repetida es una señal provisional de preferencia, no de eficacia. | ¿Qué opciones y posiciones habría que constatar que aparecieron en pantalla para evaluar aceptación sin asumir que las alternativas no elegidas fueron rechazadas? |

Referencias para preparar la entrevista (consultadas el 29 de septiembre de 2026;
las decisiones del catálogo quedan pendientes de dictamen profesional):

1. MISSIUNA, Cheryl, et al. *Examination of the Perceived Efficacy and Goal Setting System (PEGS) with children with disabilities, their parents, and teachers*. 2006. DOI: 10.5014/ajot.60.2.204. Disponible en: https://pubmed.ncbi.nlm.nih.gov/16596924/
2. GEBRE, Azeb, et al. *Child routines moderate a brief behavioral intervention to enhance sleep in school-aged children*. 2024. DOI: 10.1093/jpepsy/jsae015. Disponible en: https://academic.oup.com/jpepsy/article/49/5/365/7637719
3. HIGUCHI, Shigekazu, et al. *Influence of light at night on melatonin suppression in children*. 2014. DOI: 10.1210/jc.2014-1629. Disponible en: https://pubmed.ncbi.nlm.nih.gov/24840814/
4. MOONEY, Jennifer; WINTER, Karen y CONNOLLY, Paul. *Effects of a book gifting programme on literacy outcomes for foster children: A randomised controlled trial evaluation of the Letterbox Club in Northern Ireland*. 2016. DOI: 10.1016/j.childyouth.2016.03.009. Disponible en: https://pure.qub.ac.uk/en/publications/effects-of-a-book-gifting-programme-on-literacy-outcomes-for-fost/
5. KIM, James S. y WHITE, Thomas G. *Scaffolding voluntary summer reading for children in grades 3 to 5: An experimental study*. 2008. DOI: 10.1080/10888430701746849. Disponible en: https://jameskim.scholars.harvard.edu/publications/scaffolding-voluntary-summer-reading-children-grades-3-5-experimental-study

## Catálogo que debe examinarse

La columna de foco plantea preguntas de auditoría del equipo; **no constituye
un dictamen profesional**. Los títulos e identificadores corresponden al código
en `6db2e01`. Las descripciones completas de esa versión aparecen debajo de
la tabla; cualquier cambio posterior requiere actualizar la versión revisada.

| ID | Actividad | Contextos actuales | Nivel | Otra persona | Dispositivo | Foco para la revisión |
| --- | --- | --- | --- | --- | --- | --- |
| `movement_dance_01` | Bailá una canción | Voluntario, general | Activo | No | Posible | Música y variantes de movimiento |
| `movement_sequence_01` | Armá una secuencia de movimientos | Voluntario, general | Activo | No | No | Saltar, girar o agacharse como ejemplos; espacio y alternativas accesibles |
| `movement_ball_01` | Jugá con una pelota | Voluntario, general | Activo | No | No | Disponibilidad de pelota, espacio seguro y adaptación motriz |
| `creative_character_01` | Inventá un personaje | Voluntario, general, descanso | Calmo | No | No | Dibujo, materiales y variantes de expresión |
| `creative_animal_01` | Creá un animal imaginario | Voluntario, general, descanso | Calmo | No | No | Dibujo y materiales; adecuación por edad |
| `creative_favorite_01` | Dibujá algo que te guste | Voluntario, general, descanso | Calmo | No | No | Libertad de elección y alternativas al dibujo |
| `creative_story_01` | Inventá una historia | Voluntario, general, descanso | Calmo | No | No | Escritura/dibujo, comprensión lectora y variantes orales |
| `reading_choose_01` | Elegí algo para leer | Voluntario, general, descanso | Calmo | No | No | Disponibilidad de lectura, nivel lector y variantes accesibles |
| `reading_favorite_01` | Volvé a una historia que te guste | Voluntario, general, descanso | Calmo | No | No | Material conocido, nivel lector y adecuación al descanso |
| `free_play_nearby_01` | Jugá con algo que tengas cerca | Voluntario, general | Moderado | No | No | Materiales disponibles y juego autónomo |
| `free_play_build_01` | Construí algo | Voluntario, general | Moderado | No | No | Piezas disponibles, manipulación y seguridad según edad |
| `free_play_story_01` | Creá una historia con tus juguetes | Voluntario, general | Moderado | No | No | Disponibilidad de juguetes y otras formas de narrar |
| `social_play_01` | Jugá con alguien | Voluntario, general | Moderado | Sí | No | Disponibilidad y voluntad de otra persona de confianza |
| `social_talk_01` | Contá algo de tu día | Voluntario, general, descanso | Calmo | Sí | No | Privacidad, voluntad del niño y persona disponible |
| `social_help_01` | Ayudá con algo | Voluntario, general | Moderado | Sí | No | Riesgo de convertir una pausa voluntaria en obligación doméstica |
| `social_story_01` | Escuchá una historia | Voluntario, general, descanso | Calmo | Sí | No | Persona disponible y variantes sin lectura o pantalla |
| `quiet_prepare_01` | Prepará algo para mañana | General, descanso | Calmo | No | No | Adecuación a la rutina familiar y carga de tarea antes de dormir |
| `quiet_draw_01` | Hacé un dibujo tranquilo | Descanso | Calmo | No | No | Materiales, variantes accesibles y adecuación al descanso |

### Textos actuales que vería el niño

Estos textos son propuestas del equipo y están pendientes de revisión. Las
opciones concretas que se mostrarán también dependen de contexto y filtros.

| ID | Descripción actual |
| --- | --- |
| `movement_dance_01` | Elegí una canción que te guste, dejá el celular y bailá mientras suena. |
| `movement_sequence_01` | Elegí tres movimientos que puedas hacer, como saltar, girar o agacharte, y tratá de repetir la secuencia. |
| `movement_ball_01` | Si tenés una pelota cerca y un lugar seguro, elegí una forma de jugar con ella. |
| `creative_character_01` | Inventá un personaje nuevo y dibujá cómo sería. |
| `creative_animal_01` | Mezclá características de animales que conozcas e inventá uno nuevo para dibujar. |
| `creative_favorite_01` | Elegí un personaje, lugar, objeto o cualquier cosa que tengas ganas de dibujar. |
| `creative_story_01` | Inventá una historia corta. Podés escribirla, dibujarla o hacer las dos cosas. |
| `reading_choose_01` | Buscá un libro, cuento o cómic que tengas ganas de leer. |
| `reading_favorite_01` | Elegí un libro, cuento o cómic que ya conozcas y buscá una parte que quieras volver a leer. |
| `free_play_nearby_01` | Elegí un juguete, cartas, bloques u otra cosa que tengas ganas de usar y empezá a jugar. |
| `free_play_build_01` | Si tenés bloques, piezas u objetos para construir, elegí qué querés crear y empezá. |
| `free_play_story_01` | Elegí algunos juguetes y pensá qué historia podría pasarles. |
| `social_play_01` | Si hay alguien de confianza cerca, preguntale si quiere jugar a algo con vos. |
| `social_talk_01` | Si tenés ganas, contale a alguien de confianza algo divertido o interesante que te haya pasado. |
| `social_help_01` | Si hay alguien cerca, preguntale si necesita ayuda con alguna tarea sencilla. |
| `social_story_01` | Si hay alguien de confianza con quien tengas ganas de hablar, preguntale si quiere contarte una historia o una anécdota. |
| `quiet_prepare_01` | Elegí alguna cosa sencilla que puedas dejar lista para mañana, como tu mochila, ropa o materiales. |
| `quiet_draw_01` | Elegí libremente algo que tengas ganas de dibujar mientras te preparás para terminar el día. |

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

Revisar si la variedad de categorías se traduce en alternativas funcionalmente
distintas: `creative_character_01`, `creative_animal_01`,
`creative_favorite_01`, `creative_story_01` y `quiet_draw_01` pueden requerir
escritura o dibujo aunque pertenezcan a distintas categorías. Comprobar además
si el texto de `social_help_01` preserva el carácter voluntario y la seguridad;
si las opciones de lectura presuponen libros disponibles; y si las actividades
de descanso encajan con la rutina familiar. Son hipótesis de revisión, no
decisiones anticipadas de conservar o retirar actividades.

El profesional puede recomendar otra estructura de catálogo o descartar la
ponderación actual. Tras recibir sus observaciones, registrar una matriz
`versión inicial → observación → decisión → cambio de requisito/catálogo/código`
con responsables y pruebas. Solo entonces actualizar textos y condiciones,
conservar identificadores históricos o versionarlos explícitamente, y preparar
la evidencia para la entrega académica. No atribuir aprobación profesional
antes de completar y conservar esas respuestas.
