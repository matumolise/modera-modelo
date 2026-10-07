# Entrega técnica a Juanma — modelo PMUM-SF experimental

**Borrador para revisar antes de enviarlo.** Rama:
`hu-pmum-real-data-candidate` en `matumolise/modera-modelo`. El modelo
entrenado (`hu_pmum_sf_experimental_v1.joblib`) se encuentra en la computadora
de Matías, fuera de Git. SHA-256 de ese archivo:
`56c991f40e56d2241196dc6f9efc1c9027c079e98a1b67549f48b10292e371e0`.
Se entrenó en Windows 10.0.26200, Python 3.10.0, NumPy 2.2.6, SciPy 1.15.3,
scikit-learn 1.7.2 y joblib 1.5.3. Las cuatro dependencias directas se
registran en `experiments/requirements-hu-model.txt`. SHA-256 del ZIP fuente:
`f16adde7e9fae278de2fa5d25412533b98db91306b31e2ba637f09c05347e8f5`.
El artefacto entrenado en otros sistemas o versiones puede tener un hash
diferente aunque pase la misma predicción de referencia; no confundir sus
hashes ni cargar archivos serializados de un origen no confiable.

## Qué hace hoy

El modelo entrenado con 803 niños de la base real PHI-CSU predice la **media
del PMUM-SF parental (1–5)** a partir de edad, código de sexo y dos categorías
de tiempo total de pantalla declaradas por el adulto. La evaluación cruzada
exploratoria dio MAE 0,6427 frente a 0,7430 de predecir la media. Este dato
no demuestra funcionamiento con niños argentinos. El modelo de once variables
en `inference.py` sigue aparte y se entrenó con datos sintéticos: no hay que
llamarlo como si fuera este modelo.

El Python del modelo corre por separado del backend de Juanma y de la app
Android. **No deben implementarse dos cálculos del PMUM-SF:** el backend
administra respuestas e identidad; el servicio Python calcula el puntaje.
Las once métricas del celular siguen el histórico y los patrones, sin
convertirse en entradas de este modelo.

## Contrato de solicitud (provisional)

El servicio local ofrece `POST /experimental/pmum-estimate` con
`Content-Type: application/json`:

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

`age` debe estar entre 6 y 12. `sex_code` acepta 1 o 2 de la base original;
si falta o tiene otro valor, el candidato se abstiene. Las categorías son
enteros del 1 al 5 y **son respuestas del adulto**, no minutos que Android
transforma. El adulto piensa en tiempo promedio del niño en todas las
pantallas durante los últimos 30 días: menos de 1 h, 1–2, 3–4, 5–6 o 7 h o
más, para día hábil y fin de semana. No sumar el uso Android al total que
estima el adulto. El texto completo del día hábil no pudo recuperarse de la
base y las opciones tienen huecos: documentar la redacción adoptada. La app
puede funcionar sin estas respuestas, pero no mostrar un puntaje del modelo.

Ejemplo de respuesta interna, con datos inventados:

```json
{
  "status": "estimated",
  "estimated_pmum_sf_mean": 2.6959,
  "model_version": "hu_pmum_sf_experimental_v1",
  "experimental": true,
  "use": "internal_research_only"
}
```

Si falta una respuesta: `{"status":"unavailable","reason":"missing_parent_answer"}`
sin campo de puntaje. Otros motivos incluyen `invalid_feature_value`,
`reference_period_mismatch` y `respondent_mismatch`. Un modelo que no carga
produce error del servicio, no un puntaje inventado. No derivar de aquí
etiquetas de riesgo o diagnósticos: no hay umbrales PMUM-SF validados para
este uso ni evaluación local.

En el prototipo HTTP una estimación y una abstención son ambas respuestas
`200` con distinto `status` JSON. JSON inválido o largo inválido devuelve
`400`, tipo de contenido distinto de JSON devuelve `415` y un artefacto que
no se puede cargar devuelve `503`. El backend debe distinguir `unavailable`
de un fallo técnico del servicio.

## Responsabilidades de cada parte

| Parte | Responsabilidad |
| --- | --- |
| Android/padre | Capturar edad y respuestas, permitir omitirlas; mostrar las cinco opciones originales y el período de 30 días. Mantener las once métricas Android en el flujo histórico separado. |
| Backend de Juanma | Autenticar al adulto; asociar respuesta y resultado con `profile_id`; guardar `answered_at`, revisión del formulario, ventana de referencia, las dos categorías, `model_version` y hora del cálculo. Si cambia una respuesta, crear nueva revisión y nueva estimación sin reescribir el histórico. Si hay abstención, dejar el score ausente y permitir el resto de la app. |
| Servicio Python | Validar las entradas, cargar el artefacto confiable y devolver la estimación o abstención. No recibe identificador del niño ni persiste datos en el prototipo. |

## Ejecución local para integración

1. En la máquina que ejecutará el servicio Python, usar Python 3.10 y el
   entorno de `experiments/requirements-hu-model.txt`, o verificar antes la
   compatibilidad de otras versiones. Colocar el `.joblib` de Matías en una
   ubicación local confiable, fuera del repositorio, y comprobar su SHA-256.
   No cargar un `.joblib` recibido de un origen desconocido. Si se reentrena
   desde el ZIP, verificar la fuente, los 803 casos y la prueba de predicción;
   el binario resultante puede tener otro hash.
2. Ejecutar
   `python experiments/hu_pmum_artifact_check_v2.py DIRECTORIO_DEL_MODELO`.
3. Iniciar
   `python experiments/hu_pmum_local_api_v1.py --model RUTA_AL_JOBLIB`.
   Escucha solo en `127.0.0.1:8765`; confirmar `GET /health` y enviar una
   solicitud de ejemplo desde el backend que corre en la **misma máquina**.
   Si el backend corre en otra máquina o en un contenedor, `localhost` no
   alcanza: acordar despliegue interno, autenticación y red antes de conectarlo.

El servidor de ejemplo usa la biblioteca estándar y **no trae autenticación
ni persistencia**. Está limitado a pruebas locales; Android no debe llamarlo
directamente. Todavía hay que acordar con Juanma el stack y despliegue reales
del backend antes de fijar la URL final o abrirlo en una red.

## Criterio de cierre técnico de la integración

- El backend autenticado manda las cuatro entradas y el período correctos.
- Un ejemplo válido devuelve la versión y un puntaje; una respuesta omitida
  no produce puntaje, y la app sigue mostrando el histórico Android.
- La modificación de respuestas crea otra revisión, sin cambiar puntajes
  antiguos; el backend no interpreta un nuevo score como cambio semanal de
  conducta si las ventanas de 30 días se superponen.
- El servicio falla de forma visible si falta/cambia el artefacto.
- Se documenta que el endpoint es experimental y que la validación externa
  y la aprobación de alcance del docente siguen pendientes.

**Preguntas concretas para Juanma antes del despliegue:** ¿en qué stack y
entorno corre su backend (proceso local, contenedor o servidor)? ¿El perfil ya
guarda la edad y el sexo del niño, con una opción para dejar este último sin
respuesta? ¿Ya guarda revisiones de respuestas parentales con fecha y
`profile_id`? Con esas respuestas se acuerda la URL interna, el manejo de
ausencias y el formato definitivo de persistencia.
