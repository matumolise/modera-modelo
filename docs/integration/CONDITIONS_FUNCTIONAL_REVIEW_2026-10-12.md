# Matriz funcional del catálogo — revisión acumulativa

Fuente: las 18 consignas de recommendations.py en 94ff3a8, catálogo provisional. Esta matriz describe tareas/estímulos, no capacidades ni compatibilidad clínica. No cambia el selector ni el catálogo.

E = tarea/estímulo explícito; V = depende de variante/soporte/apoyo; N = no especificado. Ninguna letra significa permitido, prohibido o seguro. Música explícita no equivale a requerir capacidad auditiva. Todas las consignas necesitan revisión del acceso a instrucciones/UI. Leer no fija formato visual; dibujar/escribir/construir no fija miembros o apoyos; los ejemplos de movimientos no son obligatorios. Esos dominios quedan V hasta conocer la modalidad concreta.

| Actividad | Brazos/manos | Piernas | Visual | Auditiva | Sensorial | Información concreta pendiente |
|---|---|---|---|---|---|---|
| `movement_dance_01` | V | V | N | E | E | Qué movimientos y estímulos puede admitir; acceso a la consigna y elección de canción. |
| `movement_sequence_01` | V | V | N | N | V | Elegir los movimientos concretos: saltar/girar/agacharse son ejemplos, no una secuencia obligatoria ni una inferencia de capacidades. |
| `movement_ball_01` | V | V | V | V | V | Cómo se jugaría y con qué apoyos; no definir compatibilidad por categoría. |
| `creative_character_01` | V | N | V | N | V | Apoyos o variante accesible; si se evita dibujar, revisar esta consigna. |
| `creative_animal_01` | V | N | V | N | V | Igual que dibujo; interés por animales no elimina restricciones. |
| `creative_favorite_01` | V | N | V | N | V | Medio y apoyos para dibujar; no convertir calma en accesibilidad. |
| `creative_story_01` | V | N | V | N | V | Variante sin escritura/dibujo no está en el texto; requiere revisión. |
| `reading_choose_01` | V | N | V | N | V | Formato accesible y disponibilidad; no asumir audio o braille ya implementados. |
| `reading_favorite_01` | V | N | V | N | V | Igual que lectura; conocimiento de la historia no acredita acceso. |
| `free_play_nearby_01` | V | V | V | V | V | Actividad concreta, acceso a materiales y estímulos; no clasificar todo juego igual. |
| `free_play_build_01` | V | V | V | N | V | Material, apoyos y forma de construir; selección por interés no alcanza. |
| `free_play_story_01` | V | V | V | N | V | Distinguir imaginar de mover juguetes; variante no especificada. |
| `social_play_01` | V | V | V | V | V | Persona disponible y juego concreto; no declararlo accesible por ser social. |
| `social_talk_01` | N | N | N | V | V | Modo accesible de comunicación; no inferir capacidad de oír/hablar. |
| `social_help_01` | V | V | V | V | V | Tarea concreta, apoyos y persona disponible; no usar categoría como filtro suficiente. |
| `social_story_01` | N | N | N | E | V | El titulo Escucha una historia explicita escucha; confirmar modo accesible, apoyos o variante revisada y persona disponible. La descripcion no fija apoyos. |
| `quiet_prepare_01` | V | V | V | N | V | Tarea concreta y apoyos; calm no excluye demanda manual o visual. |
| `quiet_draw_01` | V | N | V | N | V | Mismas restricciones que dibujo; etiqueta bedtime también provisional. |

## Reevaluación de una corrección inicialmente propuesta

En esta auditoría primero se leyó la descripción de social_story_01 y se propuso retirar la escucha explícita. Al contrastar el título completo —Escuchá una historia— se comprobó que esa corrección no correspondía. Se conserva escucha como tarea explícita y se agregan título y su SHA a la matriz y al test. La modalidad/apoyos concretos no están fijados ni existe una variante adaptada aprobada; no se deduce capacidad auditiva ni exclusión automática de una condición.

## Opciones y combinaciones

- Ninguna es una declaración exclusiva sobre las consideraciones del formulario. No demuestra materiales, otra persona disponible, posibilidad de interactuar con dispositivo ni acceso a UI. El backend debe consolidar esos requisitos antes del selector; copiar `known/{}` del resolver como aprobación global sería una interpretación incorrecta.
- Una sola alternativa de movilidad, combinable con visual/auditiva/sensorial. Ambas reúne los temas de manos y piernas, sin derivar prohibiciones por categoría.
- Las 31 combinaciones no vacías admitidas sin Ninguna mantienen unknown en el resolver actual; se comprobó que el selector se abstiene.
- No respondido, datos contradictorios y seguimientos sin resolver no equivalen a Ninguna. Intereses y nivel calm/moderate/active no reemplazan información funcional.

## Ajuste propuesto para el formulario MVP

Conservar la pregunta general solo si se explica que identifica temas para revisar. Para un efecto ejecutable, acordar respuestas referidas a las tareas existentes: dibujo/escritura/manipulación; movimientos concretos; formato de lectura y consignas; música/estímulos específicos; comunicación; apoyo/persona/materiales disponibles. No pedir diagnóstico o historia clínica para obtener estos datos.

Propuesta de opciones por tarea: sin restricción declarada; evitar; requiere adaptación/apoyo; no conocido. Solo una exclusión concreta y confirmada puede traducirse al filtro `excluded_activity_ids` existente. Una adaptación no se implementa cambiando un permiso: necesita variante de consigna revisada/versionada. Datos desconocidos mantienen abstención. La exclusión de algunas actividades no aprueba automáticamente las restantes.

No se recomienda filtrar por categorías completas: una actividad social puede requerir movimiento, una calm puede exigir dibujo y una lectura puede necesitar otro soporte todavía no implementado. Antes de habilitar mapeo automático: dictamen por actividad/variante, requisitos codificados, tests de combinaciones y versión aprobada. No se cambió el endpoint para fingir esos datos.

## Responsables y aceptación

Equipo + profesional: conservar/adaptar/retirar/pendiente, demandas y apoyos por actividad. Juanma/UX: presentación, omisión explícita, combinaciones y consolidación operativa. Analytics: filtros deterministas y abstención probada. Android: acceso real a consigna y confirmación de entrega. Cierre requiere aprobación trazable de variantes y pruebas con inputs explícitos; esta matriz todavía no cumple ese cierre.
