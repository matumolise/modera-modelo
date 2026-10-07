# Experimento PMUM-SF con datos reales de Hungría

Ejecutar desde la raíz del repositorio:

```bash
python experiments/hu_pmum_real_data.py '/ruta/21802447.zip'
```

El script lee `SEM.dat` y `SEM.inp` directamente del ZIP PHI-CSU, filtra niños
de 6 a 12 años con los nueve ítems completos y verifica que `PMUMTotal` sea su
suma. Usa edad, código de sexo y categorías ordinales de tiempo de pantalla
en día hábil y fin de semana. Ninguna pregunta PMUM entra como predictor.

Separa 20 % de los niños antes de elegir la regularización mediante cinco
pliegues del conjunto restante. Compara el modelo lineal con la media del
conjunto de entrenamiento y muestra resultados aparte para hogares de un hijo.
Ese primer conjunto apartado **ya fue consultado**. No se debe ajustar el modelo
según sus resultados y seguir llamándolo una evaluación final intacta.
Para revisar estabilidad, el script también usa validación cruzada anidada:
en cada pliegue externo selecciona la regularización solo con datos del pliegue
de entrenamiento y compara edad/sexo, tiempo y las cuatro entradas. Muestra
errores por edad y hogares de un hijo. Esa revisión posterior sigue siendo
exploratoria; no es una prueba con niños argentinos ni una nueva muestra externa.
Las categorías de pantalla no se convierten a minutos. No se guardan filas,
identificadores, predicciones individuales ni un modelo para producción.

Esta evaluación solo usa respuestas parentales húngaras. La muestra seleccionó
al niño que más usaba pantallas en hogares con varios hijos. La pregunta de
día hábil tiene su etiqueta truncada en el archivo: antes de implementarla
en la aplicación hay que verificar su texto y alcance completos. Tampoco
demuestra funcionamiento con niños argentinos ni con mediciones de Android.
Tres niños tienen el código de sexo 4; se preserva como categoría sin asignarle
un significado que no hemos verificado en el codebook. El archivo `SEM.inp`
excluye `CHGender > 2` en sus propios análisis, por lo que el script informa
también una sensibilidad con 803 niños que excluye esos tres casos. Las
comparaciones cruzadas de 806 y 803 usan divisiones distintas, así que solo
sirven para verificar si cambia mucho la conclusión general.

La etiqueta íntegra del día de fin de semana menciona los últimos 30 días,
tiempo total y teléfono, tablet, computadora, consola y televisor. La etiqueta
del día hábil fue truncada por el formato del archivo `.sav`: no se confirma
que enumere todas las mismas pantallas. Por eso hay una comparación diagnóstica
`age_sex_weekend`, que omite la variable de alcance incompleto. Esta opción se
identificó tras mirar los resultados originales, de modo que sus cifras son
exploratorias y no justifican afirmar que supera al modelo de cuatro entradas
en una población nueva.
El experimento no modifica `inference.py` ni el motor actual mientras se
resuelve el alcance con Santiago.

## Modelo candidato (sin conexión a la aplicación)

Después de auditar el experimento, se puede entrenar una copia local del
candidato de cuatro entradas con el ZIP exacto identificado por SHA-256:

```bash
python experiments/hu_pmum_candidate_v1.py train '/ruta/21802447.zip' experiments/output
python experiments/hu_pmum_candidate_v1.py predict experiments/output/hu_pmum_sf_experimental_v1.joblib 9 1 2 3
```

El segundo comando es solo una prueba técnica: 9 años, código de sexo 1,
categoría 2 en día hábil y categoría 3 en fin de semana. No corresponde a un
niño identificado. El artefacto y su manifiesto se guardan en
`experiments/output/`, excluido de Git. Se entrena con 803 niños (`CHGender`
1 o 2); los tres de código 4, no identificado, se excluyen para no inventar
una opción equivalente en la aplicación. Si el padre no puede o no quiere
responder alguna entrada, este candidato no devuelve una estimación: hará
falta acordar una alternativa con evaluación propia.

La cifra de evaluación cruzada proviene del análisis exploratorio; entrenar
después con los 803 niños completos produce un artefacto técnico, no una
validación adicional ni autorización para usarlo con familias argentinas.

Comprobación técnica del candidato: manteniendo edad y código de sexo, sus
predicciones aumentan al subir cada categoría de tiempo. Sin embargo, con
edad 9, día hábil categoría 2 y fin de semana categoría 3, el puntaje estimado
es 2,6959 para `sex_code=1` y 2,3180 para `sex_code=2`. En validación cruzada
anidada exploratoria con 803 niños, quitar sexo aumenta el MAE aproximado de
0,6427 a 0,6627. Este contraste observado en la muestra no establece que
usar sexo sea adecuado para niños argentinos; requiere decisión explícita
antes de integrar el candidato. El puntaje sin redondear tampoco es una
categoría de riesgo clínica para presentar a familias.

Para verificar una copia del modelo y del manifiesto en otro equipo, copiar
`hu_pmum_artifact_check_v2.py` y ejecutar:

```bash
python experiments/hu_pmum_artifact_check_v2.py '/ruta/directorio_del_modelo'
```

El resultado `PASS` confirma procedencia, versión, número de niños,
preprocesamiento, ejemplo de inferencia, rechazo de entradas inválidas y
una comprobación de monotonía en categorías. El comportamiento del adaptador
de servicio se verifica por separado, al integrar el backend. **No** demuestra validez externa,
precisión clínica ni preparación para publicar el modelo.

Para preparar un traslado del artefacto entrenado en Windows, ejecutar
`hu_pmum_environment_report_v1.py DIRECTORIO_DEL_MODELO` y contrastar el
SHA-256 con el del documento `JUANMA_INTEGRATION_HANDOFF_DRAFT.md`. El archivo
`requirements-hu-model.txt` fija las dependencias directas de ese entorno.

El script `hu_pmum_sex_audit_v1.py` hace la comparación agregada y
reproducible por código de sexo y por cantidad de hijos, seleccionando alpha
por validación cruzada dentro de cada pliegue. Con cuatro entradas, el error
medio firmado en los grupos de códigos 1 y 2 queda cerca de cero. Sin sexo,
subestima en promedio 0,1404 el código 1 y sobrestima 0,2332 el código 2
en esta muestra. No prueba que uno de los enfoques sea más justo en Argentina:
las diferencias pueden reflejar selección de hogares, respuestas parentales
o composición de grupos. Mantener sexo en el candidato húngaro es coherente
con esta evaluación interna; su uso efectivo en la app queda condicionado a
la definición del alcance y a explicitar esa limitación.
