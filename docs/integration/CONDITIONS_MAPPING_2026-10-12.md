# Condiciones del formulario y catálogo: matriz de revisión

Base: `26654b6`. Se auditan las 18 consignas actuales; no se modifica el catálogo ni se acredita seguridad clínica.
Catálogo: `provisional-sha256:e7a897d256c33c0e6e43ab2f5649750512f4c9c55b1c2d38f1392a616f78fb3b`. Matriz JSON: `CATALOG_CONDITIONS_AUDIT_V1.json`.

## Resolución implementada

`POST /v1/activities/eligibility` acepta una declaración explícita de consideraciones. Es una ampliación candidata; no selecciona actividades, no almacena condiciones y no sustituye revisión funcional.

| Opción | Código | Qué queda por conocer | Resultado actual |
|---|---|---|---|
| Ninguna | `none` | Declaración expresa del adulto, no omisión | `known`, `eligibility: {}`; selección aún provisional |
| Movilidad: brazos/manos | `mobility_arms_hands` | ¿Qué tareas de dibujo o manipulación conviene evitar o adaptar? | `unknown`, `functional_mapping_required` |
| Movilidad: piernas | `mobility_legs` | ¿Qué movimientos o desplazamientos conviene evitar o adaptar? | `unknown`, `functional_mapping_required` |
| Movilidad: ambas | `mobility_both` | ¿Qué tareas de dibujo o manipulación conviene evitar o adaptar?; ¿Qué movimientos o desplazamientos conviene evitar o adaptar? | `unknown`, `functional_mapping_required` |
| Visual | `visual` | ¿Qué apoyo hace falta para libros, dibujos u objetos visuales?; ¿Cómo debe presentarse la consigna para que sea accesible? | `unknown`, `functional_mapping_required` |
| Auditiva | `auditory` | ¿Hay que evitar o adaptar música e historias escuchadas?; ¿Qué forma de comunicación resulta accesible? | `unknown`, `functional_mapping_required` |
| Sensibilidad sensorial | `sensory` | ¿Qué estímulos concretos se deben evitar y en qué contexto? | `unknown`, `functional_mapping_required` |
| No conocido/no respondido | Estado `unknown`, sin `conditions` | Falta información | `unknown`, `considerations_unknown` |

“Ninguna” es exclusiva; conocida con lista vacía es inválida. Se admite una sola alternativa de movilidad y se pueden combinar visual, auditiva y sensorial. Duplicados o códigos nuevos se rechazan. Cada dimensión se conserva; los intereses no anulan restricciones.

Los seguimientos son temas para cerrar el mapeo, no un formulario profesional ya aprobado ni una solicitud de historia clínica. El código no acepta respuestas a esos seguimientos ni las transforma en permisos: ese contrato requiere revisar variantes reales y actualizar/versionar la matriz.

## Auditoría de las 18 actividades

La columna de demandas describe la consigna, no la capacidad de una persona. “Posible” o “no especificada” impide inferir compatibilidad. La sensibilidad sensorial depende del estímulo concreto, su intensidad y el contexto; no se deduce de `activity_level`.

| ID | Evidencia textual | Demandas a revisar | Información o adaptación pendiente |
|---|---|---|---|
| `movement_dance_01` | Elegir y escuchar música; bailar. | Movimiento según variante; música explícita. | Qué movimientos y estímulos puede admitir; acceso a la consigna y elección de canción. |
| `movement_sequence_01` | Elegir y repetir movimientos; ejemplos de saltar/girar/agacharse. | Demanda de piernas según variante; no equivale a toda actividad movement. | Movimientos concretos y variantes; no deducirlos de brazos/piernas. |
| `movement_ball_01` | Pelota y espacio; forma de juego no especificada. | Manipulación, visión, desplazamiento y estímulos dependen del juego. | Cómo se jugaría y con qué apoyos; no definir compatibilidad por categoría. |
| `creative_character_01` | Dibujar un personaje. | Dibujo/manual; material visual tal como está escrito. | Apoyos o variante accesible; si se evita dibujar, revisar esta consigna. |
| `creative_animal_01` | Inventar y dibujar un animal. | Dibujo/manual; material visual tal como está escrito. | Igual que dibujo; interés por animales no elimina restricciones. |
| `creative_favorite_01` | Dibujar libremente. | Dibujo/manual; material visual tal como está escrito. | Medio y apoyos para dibujar; no convertir calma en accesibilidad. |
| `creative_story_01` | Escribir, dibujar o ambas cosas. | Todas las variantes ofrecidas contienen tarea manual. | Variante sin escritura/dibujo no está en el texto; requiere revisión. |
| `reading_choose_01` | Buscar un libro/cuento/cómic y leer. | Acceso a material escrito; manipulación según soporte/apoyo. | Formato accesible y disponibilidad; no asumir audio o braille ya implementados. |
| `reading_favorite_01` | Buscar y releer una parte conocida. | Material escrito; manipulación según soporte/apoyo. | Igual que lectura; conocimiento de la historia no acredita acceso. |
| `free_play_nearby_01` | Elegir juguete, cartas, bloques u otra cosa. | Juego y materiales no fijados; demanda manual posible. | Actividad concreta, acceso a materiales y estímulos; no clasificar todo juego igual. |
| `free_play_build_01` | Construir con piezas/objetos. | Manipulación explícita; estímulos y material visual según objetos. | Material, apoyos y forma de construir; selección por interés no alcanza. |
| `free_play_story_01` | Elegir juguetes y pensar una historia. | Manipulación/visual posibles; pensar no exige por sí solo manipular. | Distinguir imaginar de mover juguetes; variante no especificada. |
| `social_play_01` | Jugar con una persona de confianza disponible. | Juego no especificado; comunicación, manos, piernas y estímulos variables. | Persona disponible y juego concreto; no declararlo accesible por ser social. |
| `social_talk_01` | Contar algo a alguien de confianza. | Forma de comunicación no especificada. | Modo accesible de comunicación; no inferir capacidad de oír/hablar. |
| `social_help_01` | Ayudar en una tarea sencilla no especificada. | Demandas indeterminadas; sencilla no acredita factibilidad. | Tarea concreta, apoyos y persona disponible; no usar categoría como filtro suficiente. |
| `social_story_01` | Escuchar una historia de otra persona. | Escucha explícita; forma de comunicación y estímulos por revisar. | Apoyo/variante de comunicación y persona disponible; variante visual no implementada. |
| `quiet_prepare_01` | Dejar listos mochila/ropa/materiales. | Organización/manipulación según tarea; desplazamiento posible. | Tarea concreta y apoyos; calm no excluye demanda manual o visual. |
| `quiet_draw_01` | Dibujar antes de terminar el día. | Dibujo/manual; material visual tal como está escrito. | Mismas restricciones que dibujo; etiqueta bedtime también provisional. |

## Propuesta operativa para el MVP

1. Conservar las opciones generales si sirven para iniciar una conversación, pero no prometer que ya filtran automáticamente las actividades.
2. Para filtros ejecutables, acordar preferencias/restricciones funcionales referidas a tareas concretas y versiones de actividades efectivamente revisadas. Por ejemplo, decidir que no se ofrezcan las consignas de dibujo, no inferirlo solo de “movilidad”.
3. Si se confirma una exclusión concreta, el backend puede usar `excluded_activity_ids` del endpoint existente. No convertir una exclusión por IDs en una aprobación de todas las actividades restantes.
4. Mientras no exista mapeo suficiente, enviar `eligibility_state: unknown` sin `eligibility`; el selector se abstiene. La solicitud voluntaria también respeta esa abstención.

La alternativa de filtrar por categorías enteras se desaconseja: lectura puede admitir otros formatos, una actividad social puede exigir una tarea motora y una tranquila puede requerir dibujo. No se han implementado esas adaptaciones ni recibido aprobación profesional.

Fuente interna: `docs/f16/F16_PROFESSIONAL_ACTIVITY_REVIEW.md`, instrumento con respuestas profesionales pendientes. No se presenta como un dictamen recibido.
