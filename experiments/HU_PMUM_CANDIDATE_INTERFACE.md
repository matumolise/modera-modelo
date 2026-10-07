# Interfaz de prueba del candidato PMUM-SF

Estado: **experimental e interno**. No reemplaza `inference.py`, no decide
riesgos ni recomienda actividades. `hu_pmum_parent_adapter_v2.py` expone
una función local `estimate(model_path, request)`.

Para ensayar la integración HTTP existe `hu_pmum_local_api_v1.py`. Se inicia
con `python experiments/hu_pmum_local_api_v1.py --model RUTA_AL_JOBLIB` y
escucha solo en `127.0.0.1:8765`, con `GET /health` y
`POST /experimental/pmum-estimate` (`Content-Type: application/json`). No
tiene autenticación ni persistencia; **no debe exponerse en red**. El backend
de Juanma será dueño de identidad, autorización y persistencia.

Ejemplo de solicitud, con respuestas ficticias del adulto:

```json
{
  "age": 9,
  "sex_code": 1,
  "weekday_category": 2,
  "weekend_category": 3,
  "respondent": "parent_or_caregiver",
  "reference_days": 30
}
```

Ejemplo de respuesta interna:

```json
{
  "status": "estimated",
  "estimated_pmum_sf_mean": 2.6959,
  "model_version": "hu_pmum_sf_experimental_v1",
  "experimental": true,
  "use": "internal_research_only"
}
```

Si falta una de las dos respuestas del adulto, devuelve
`{"status":"unavailable","reason":"missing_parent_answer"}`. Esto representa
un formulario omitido, **no** una sexta categoría de entrenamiento. Si la
respondió otra fuente (por ejemplo Android), la ventana no es de 30 días o
un código queda fuera de rango, devuelve
`{"status":"unavailable","reason":"..."}`. Un artefacto ausente o dañado
es un error técnico para la capa que lo invoca: no inventar un puntaje.
La función no recibe identificadores del niño ni persiste información. La URL
de prueba es solo local. El backend decidiría la autenticación, persistencia e
identificador del perfil. La salida numérica es una estimación de la media del
PMUM-SF parental (1 a 5), no un diagnóstico ni una categoría clínica.

Para integrar después con el backend, guardar cada respuesta parental como
una revisión con `profile_id`, `answered_at`, versión del formulario, los dos
códigos y período de referencia declarado. Si el adulto cambia un código,
crear una revisión y una nueva estimación con `model_version` y hora; no
recalcular ni reescribir las estimaciones históricas como si el padre hubiera
respondido eso anteriormente. El backend gestiona consentimiento, perfil y
persistencia. Los datos Android conservan su historial separado y continúan
disponibles aunque este modelo se abstenga.

La pregunta se refiere a un promedio de los últimos 30 días. Repetirla cada
semana produciría ventanas superpuestas y puede cargar innecesariamente al
adulto; la frecuencia de solicitud se definirá con producto y profesor. Una
respuesta antigua no debería mantenerse indefinidamente como si describiera
el estado actual del niño.

Entradas válidas: `age` numérica entre 6 y 12, `sex_code` 1 o 2,
`weekday_category` y `weekend_category` enteras de 1 a 5. Los códigos de sexo
siguen el archivo fuente; cualquier otra respuesta requiere evaluar un camino
alternativo, sin asignar el código 4 a una respuesta nueva. Las categorías de
tiempo y la pregunta de día hábil tienen las limitaciones documentadas en
`HU_PMUM_MEASUREMENT_CONTRACT.md`. **No pedir todavía este contrato al adulto**
sin resolver el formulario, ni presentar cuatro decimales en la UI.
