# Texto actualizado del componente analítico de Moderá

Propuesta editorial del13/10/2026 para revisión e integración por el equipo.
Se basa en el código y evidencia disponibles; no afirma haber comparado una
nueva versión completa de la entrega del50%. Las referencias y numeración
deben integrarse a la bibliografía y estructura del documento vigente.

## Arquitectura y alcance

Moderá incorpora un servicio analítico que reúne componentes con funciones
diferentes: una estimación experimental del puntaje PMUM-SF, un analizador
histórico del uso registrado en el dispositivo y un selector de actividades.
A estos componentes se agrega una política de mensajes para el adulto
responsable. La separación permite identificar qué datos utiliza cada uno
y evita interpretar sus resultados como si representaran la misma medida.

El objetivo funcional de los mensajes consiste en acompañar al adulto con una
descripción breve de los cambios observados y una sugerencia práctica. El uso
registrado en un teléfono no representa el uso total de pantallas ni permite,
por sí solo, determinar quién utilizó el dispositivo. Por este motivo, las
tarjetas indican el período, la referencia y el alcance de la medición.

## Estimación experimental de PMUM-SF

El desarrollo inicial utilizó un prototipo con once variables observables y
un objetivo sintético. Ese trabajo se conserva como antecedente de exploración,
separado del candidato posterior basado en respuestas parentales reales.
Sus métricas no se presentan como resultados del modelo actual.

El candidato HU v1 emplea cuatro entradas: edad, código de sexo del niño y
categorías parentales de tiempo de pantalla para días hábiles y fines de semana.
La variable objetivo es la media de los nueve ítems del PMUM-SF, calculada como
PMUMTotal/9, con escala de1 a5. No se utilizan como entradas los ítems del
cuestionario ni las métricas obtenidas automáticamente de Android.

La cohorte operativa comprende803 registros de niños de6 a12 años con los
nueve ítems completos y códigos de sexo1 o2. Se seleccionó a partir del archivo
húngaro SEM.dat cuya procedencia técnica se documentó mediante la huella del
archivo fuente. La selección no equivale exactamente al filtro empleado en
el análisis original de esa fuente y no acredita representatividad argentina.

Se aplicó regresión Ridge con regularización alpha=1. La edad se estandariza
y las variables categóricas se codifican mediante one-hot dentro del proceso
de entrenamiento de cada partición. La evaluación interna de cinco pliegues
obtuvo MAE0,6427, RMSE0,7839 y R²0,2231. Los baselines de media y mediana
obtuvieron MAE0,7430 y0,7455. Una evaluación separada de selección anidada
de alpha obtuvo MAE0,6427, RMSE0,7826 y R²0,2257; esos resultados describen
el procedimiento de selección, no el único artefacto final de alpha fijo.

El diseño y las alternativas se exploraron previamente, por lo que estas
métricas no constituyen un test externo independiente. La evidencia disponible
es transversal: no demuestra que comparar estimaciones de un mismo niño
permita medir un cambio longitudinal de uso problemático. Asimismo, la pregunta
completa de día hábil permanece truncada en los metadatos recuperados.

El servicio conserva el alcance experimental e interno de esta estimación.
Su puntaje no determina la frecuencia de actividades, la apertura de tarjetas
ni el texto de recomendaciones. La validación del instrumento PMUM-SF original
no valida automáticamente esta regresión de cuatro entradas ni habilita
categorías clínicas de riesgo para el producto.

## Analizador histórico

El analizador C1 procesa la duración diaria de pantalla interactiva reconstruida
a partir de registros de Android. Cada observación conserva su intervalo,
estado, procedencia y calidad declarada. Un cero efectivamente observado se
distingue de la falta de datos. La identidad de la serie debe corresponder
a la asignación histórica del dispositivo y a la versión de medición.

Para cada observación admisible se construye una referencia con valores previos
de la misma serie, mediante mediana y escala robusta1,4826×MAD. El adaptador
vigente utiliza toda la historia previa admisible. El detector acumula desvíos
en ambas direcciones mediante CUSUM. Cuando la referencia no puede estimarse
o falta evidencia suficiente, se abstiene; no introduce un valor artificial
para evitar la abstención.

Se distingue el estado técnico CHANGE del evento emitido y del mensaje visible.
La emisión requiere las condiciones del cruce y una evaluación elegible previa;
no demuestra la causa, duración o gravedad de un cambio. Los resultados se
conservan con identificadores estables y los reintentos compatibles recuperan
el recibo original sin avanzar nuevamente el estado.

La evaluación exploratoria adicional empleó600 series ficticias,24 configuraciones
y1.612.800 evaluaciones, con auditoría aritmética independiente. Permitió
comprobar diferencias entre picos, escalones y patrones semanales, así como
persistencia de estados sin nuevas emisiones. No proporciona etiquetas clínicas,
validación con familias ni selección de una configuración de uso real.

## Mensajes al adulto

La política de comunicación compara dos períodos consecutivos de14 días
locales completos mediante una evaluación semanal. El candidato inicial
requiere días observados y verificados de la misma serie. No calcula el
promedio omitiendo datos faltantes ni representa una ausencia como uso cero.

Se consideran aumentos y disminuciones. Para abrir una tarjeta se exige una
diferencia de al menos20 minutos diarios que permanezca al excluir cualquiera
de los días de las dos ventanas y que aparezca en al menos10 de los14 días
recientes respecto de la media del tipo de día en la referencia. Estos valores
son decisiones iniciales de ingeniería, no umbrales de salud o de riesgo.

Cada aviso constituye un episodio con referencia congelada por fechas. Las
evaluaciones posteriores actualizan la misma tarjeta. El retorno utiliza un
margen de5 minutos diarios y una comprobación de sensibilidad a la exclusión
de un día; requiere una ventana reciente que ya no se superponga con la que
abrió el aviso. El seguimiento distingue resolución, resultado inconcluso,
datos insuficientes, cambio de serie, vencimiento y retiro por corrección.

El candidato establece una vigencia máxima de56 días, una espera de14 días
tras la terminación y un tope compartido de una tarjeta nueva por28 días.
Estos controles regulan el volumen y la repetición. Se cuentan tarjetas creadas;
la creación no acredita que el adulto las haya recibido o visualizado.

La tarjeta incluye título, explicación, períodos comparados y un consejo
general de conversación o acuerdos familiares. Una disminución no se presenta
como prueba de bienestar ni como efecto de Moderá. C1 conserva su función
analítica y queda vinculado como evidencia técnica complementaria; no se
modifica su estado para hacerlo coincidir con los períodos de la tarjeta.

La implementación agrega persistencia transaccional de episodios, recibos,
revisiones diarias e historial de versiones. Un reintento idéntico recupera
el resultado original; un contenido incompatible produce conflicto. Las
correcciones de evidencia generan revisiones y pueden retirar un aviso cuya
apertura ya no corresponde, conservando lo que se había registrado.

La evaluación del perfil de comunicación comprendió1.000 series ficticias
dependientes y13.000 decisiones semanales. Con ruido bajo, la fase posterior
no produjo nuevas tarjetas en los escenarios de nivel plano y pico aislado;
con ruido alto se observaron tarjetas aun sin cambio nominal del nivel del
generador. También hubo omisiones y aperturas en dirección distinta del
escalón nominal. Estos resultados limitan la interpretación del perfil y no
se presentan como validación de mensajes con familias.

## Actividades e integración

La selección infantil utiliza preferencias y condiciones de elegibilidad con
un contrato distinto del PMUM y de la comunicación adulta. Una respuesta
omitida se distingue de la declaración explícita de ausencia de consideraciones.
Cuando la información no permite resolver la elegibilidad, se conserva el
estado desconocido. La revisión funcional del mapping y del catálogo debe
registrarse antes de atribuir a sus filtros una aprobación profesional.

El backend informó integración de preferencias, ofertas y selecciones, junto
con persistencia e idempotencia. Ese reporte constituye evidencia del responsable
de la integración, no una auditoría independiente de su implementación en este
bloque. De la misma forma, la asociación de una selección con una oferta no
demuestra por sí sola que la actividad fue renderizada al niño.

La suite del candidato de mensajes registró366 pruebas aprobadas en Linux.
La ejecución compartida de Windows registró365 aprobadas y una omitida,
con190 subtests aprobados, usando Python en modo UTF-8. La demo comprobó
aumento, disminución, reinicio, replay, retorno e historial con datos ficticios.
Estas comprobaciones verifican software y contratos; no prueban eficacia.

Para completar el recorrido de producto deben conectarse el export real de
Android, su recepción durable, la atribución histórica, el cierre diario y
la presentación de tarjetas en la vista del padre. La revisión profesional
de recomendaciones, la comprensión por adultos y la evidencia con familias
se mantienen como límites externos que no pueden sustituirse por pruebas
sintéticas. La entrega académica debe distinguir esos límites del desarrollo
técnico implementado.

## Referencias a integrar

La bibliografía vigente debe conservar las fuentes primarias del instrumento
PMUM-SF (Domoff et al.,2019; DOI10.1037/ppm0000163), los registros originales
de los datasets HU y MEDIATICINO y el respaldo metodológico específico de
CUSUM y Ridge. Completar metadatos del dataset desde sus registros originales;
no deducir autores/licencia del nombre del ZIP. Este texto no realiza una
nueva revisión bibliográfica ni afirma aprobación profesional recibida.
