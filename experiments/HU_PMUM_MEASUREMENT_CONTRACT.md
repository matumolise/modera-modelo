# Contrato provisional del experimento PHI-CSU → Moderá

Estado: experimento con datos reales, sin aprobación docente ni conexión a la app.
Fuente: ZIP Zenodo 21802447; SHA-256
`f16adde7e9fae278de2fa5d25412533b98db91306b31e2ba637f09c05347e8f5`.
Archivos consultados: `SEM.dat`, `SEM.inp` y etiquetas de `SEM.sav`.

| Campo del modelo | Origen | Contrato de entrada propuesto | Límite |
| --- | --- | --- | --- |
| `age` | `CHAge` | Edad del niño en años al responder | Dos de los 806 valores son fraccionarios (6,5 y 8,5); confirmar cómo calcula edad la app. |
| `sex` | `CHGender` | Código de respuesta equiparable al cuestionario | Tres casos con código 4 sin significado confirmado; análisis de sensibilidad excluyéndolos. No inferir sexo desde Android. |
| `weekday_category` | `STIWeekday` | Elección del adulto de 1 a 5 sobre día hábil promedio | La etiqueta fue cortada antes de la pregunta: alcance completo de pantallas no comprobado. |
| `weekend_category` | `STIWeekend` | Elección del adulto de 1 a 5 sobre día de fin de semana promedio de los últimos 30 días, contando teléfono, tablet, computadora, consola y TV | Autorreporte de todas las pantallas; no equivale a minutos registrados por Android. |
| Resultado de entrenamiento | `PMUMTotal` y `PMUM1`–`PMUM9` | Media de los nueve ítems (escala 1–5); solo disponible al entrenar/evaluar | Prohibido usar los ítems o el total como entradas. La app estima el puntaje; no diagnostica. |

Las etiquetas de **ambas** variables de tiempo tienen cinco respuestas:
`1 = menos de 1 hora`, `2 = 1–2 horas`, `3 = 3–4 horas`,
`4 = 5–6 horas`, `5 = 7 horas o más`. Hay huecos de redacción
entre 2–3, 4–5 y 6–7 horas. El dataset no registra minutos precisos ni
explica cómo resolvieron los padres esas fronteras. El experimento conserva
los códigos ordinales originales. No asignar puntos medios ni mapear
automáticamente minutos de Android a estos códigos sin definir y justificar
una regla nueva y evaluar el cambio de medición.

## Pregunta candidata para la app (aún no aprobada)

> Pensando en los últimos 30 días, ¿cuánto tiempo total pasó el niño frente a
> pantallas en un día hábil promedio? Considerá teléfono, tablet, computadora,
> consola y televisión.

> Pensando en los últimos 30 días, ¿cuánto tiempo total pasó el niño frente a
> pantallas en un día de fin de semana promedio? Considerá teléfono, tablet,
> computadora, consola y televisión.

**Decisión provisional de interfaz:** mostrar las cinco opciones originales
en ese mismo orden y guardar el código elegido por el adulto, sin pedir
minutos ni sumar registros de Android. Si su estimación cae entre dos opciones
(por ejemplo 2,5 horas), ofrecer la indicación «elegí la opción que mejor
represente el tiempo habitual». Esa indicación no está verificada como parte
del cuestionario original y debe documentarse como diferencia del formulario.
No se agrega una sexta categoría al modelo. El adulto puede dejar sin responder
la pregunta: la app continúa funcionando, pero no calcula el PMUM-SF hasta
contar con ambas respuestas. No afirmar equivalencia perfecta de instrumentos
por conservar los mismos códigos.
La pregunta de fin de semana conserva el alcance explícito documentado; la
de día hábil es una reconstrucción razonable, **no** una transcripción
verificada. Si no se resuelve, comparar como análisis de sensibilidad un
modelo de edad, sexo y fin de semana; se exploró tras ver el desempeño del
modelo de cuatro variables y por eso no es confirmación independiente.

No sumar datos de Android a las respuestas parentales: el teléfono ya está
incluido y las mediciones no tienen el mismo método ni período. La ventana de
30 días hace que una respuesta diaria o semanal sea una medición distinta;
el rediseño de frecuencia de actualización queda pendiente.
