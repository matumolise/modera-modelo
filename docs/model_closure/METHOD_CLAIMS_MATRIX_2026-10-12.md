# Matriz de afirmaciones y respaldo

La tabla separa el hecho comprobado de lo que no puede concluirse. “Probada” siempre se refiere al alcance explícito. El artefacto y los documentos originales se conservan.

Es una matriz revisada: los bloques 1/2A/2B permanecen como antecedentes; la reauditoría final confirmó conteos mediante SAV y reprodujo nuevamente OOF PMUM y C2 con resultados idénticos. Se leyeron las fuentes primarias específicamente utilizadas, sin afirmar una revisión completa de toda la bibliografía o tesis. Windows/Docker y la carga del binario original tienen PASS según la evidencia aportada por Matías. Las decisiones de producto y validación científica siguen abiertas. Ver [cierre vigente](WINDOWS_DOCKER_CLOSURE_2026-10-12.md) y FINAL_REVIEW_2026-10-12.md.

| Afirmación admisible | Estado / respaldo | No permite afirmar |
|---|---|---|
| Fuente HU identificada por SHA, 806 completos, 803 incluidos por código niño 1/2 | Probada: ZIP, SEM.dat/SEM.inp/SAV y loader; cohort audit | Que 803 sea la selección original completa de los autores (SEM.inp exige además sexo cuidador 1/2; aquí serían 800 completos) |
| Objetivo HU es media de nueve ítems 1–5 | Probada: sumas coinciden en completos, PMUMTotal/9 | Que cuatro entradas equivalgan a administrar PMUM-SF |
| 1=varón; 2=mujer; 4=otra respuesta/no desea responder | Probada: diccionario SAV, 4 marcado faltante de usuario | Inferir sexo desde nombre o imputar faltantes |
| Pregunta weekend parental sobre últimos 30 días y total de dispositivos listados | Probada: etiqueta fuente | Que el texto weekday completo sea idéntico; está truncado |
| Ridge fijo mejora media/mediana dentro de la cohorte en OOF exploratorio | Probada: alpha1 MAE .6427, RMSE .7839, R² .2231; baseline media .7430 y mediana .7455 | Utilidad clínica, validación externa o test independiente no explorado |
| Selección alpha1/10/100 produjo MAE .6427, RMSE .7826, R² .2257 | Probada: cinco pliegues, cuatro internos, elección [1,1,1,10,1] | Que todos los ajustes fueron alpha1 o que esa evaluación corresponde a un único joblib |
| Transformadores se ajustan sólo con train; no se usan ítems objetivo como inputs | Probada: código y separación de índices | Ausencia de todo sesgo/fuga indirecta o validez causal |
| Subgrupo operativo NoChildren=1, n=300: MAE fijo .6676 y R² .1568 reportados | Conteo confirmado en bloque 2A; métricas recuperadas del mismo OOF | Validación independiente o equivalencia exacta con hogares de un hijo sin cotejar la recodificación original; no se reajustó en ese subconjunto |
| HU original pasó el verificador y HTTP Windows/Docker con las guardas actuales | Resumen aportado: original_pmum_artifact_loaded=true; pmum_original_artifact, windows_pmum_c1_http y docker_pmum_c1_http=PASS; el verificador exige la huella registrada y la referencia 2.6959 | Que el original se haya cargado desde Linux, se hayan inspeccionado todos los logs individuales o se haya reproducido el entrenamiento final |
| API conserva abstenciones/experimental y comprueba coherencia técnica | Pruebas estructurales con fixtures y recorrido Windows/Docker con HU original según resumen recibido | Aprobación clínica o protección frente a un manifiesto falsificado íntegramente |
| Validación del instrumento PMUM original respalda el constructo de esa escala | Fuente primaria Domoff et al.; población original 4–11, parental | Validación de HU Ridge 6–12, versión argentina o estimación desde Android |
| Antecedente HU/DE estudió invarianza y reportó problemas para equiparar niveles | Antecedente leído, no nuevo ajuste multigrupo aquí | Aprobación de pooling HU/DE. El candidato permanece sólo HU |
| C1 usa referencia prequential mediana/1.4826MAD y CUSUM bilateral | Probada: núcleo conservado, fixtures y auditoría de snapshot | Normalidad garantizada, magnitud/inicio/duración de episodio o riesgo clínico |
| La API usa all_prior_usable_records_v1 y conserva historia con CHANGE | Implementada/probada, perfil vinculado | Política óptima o avalada para uso real |
| MISSING no avanza CUSUM; cero observado puede formar referencia | Probada: núcleo, pruebas/regresiones y HTTP | Que desconocido sea cero o que consulta vacía tenga cobertura total |
| Replay devuelve IDs/fechas previos y no escribe resultado nuevo | Probada: comparación de recibos y bytes tras kill/restart | Implementación durable de backend de Juanma, no leído |
| Carga rechaza recibo observado/outcome/cruce incongruente | Implementada/probada: contraejemplos base y regresiones | Que readiness reconstruya toda mediana/MAD o autentique el archivo |
| Auditoría offline detecta referencia consistente matemáticamente pero ajena a la historia | Implementada/probada: reconstrucción sin escritura | Que corrija el historial, lo firme o proporcione migración |
| C2 contiene 14.688 escenarios sobre 1.836 ventanas de 75 participantes; la fuente tiene 93 | Bloque 2B: admisión recontada; reauditoría final: experimento completo reproducido, JSON idéntico | 14.688 sujetos independientes, contribución de los 93 a ventanas admisibles, sensibilidad/especificidad/FPR clínicas |
| Perturbación C2 de tres observaciones; 285 ventanas tienen saltos calendario y referencia sólo fondo humano no perturbado | Bloque 2B: runner y admisión recontados, sin imputar gaps | Tres días seguidos, offsets como latencia calendario o validación de referencia adaptativa de la API |
| Cruce experimental C2 y evento emitido C1 son resultados distintos | Reauditoría final: primer dato elegible puede cruzar desde CUSUM cero pero emisor con estadístico anterior None no emite; contraejemplo ficticio | Tasa C2 como tasa de eventos de API; validación del emisor/API por el experimento |
| Smoke técnico con parámetros explícitos | Probada: min_history3 en fixture y trayectoria conocida | Calibración de k/h/madurez o configuración recomendada |
| Núcleo C1, artefacto HU, parámetros científicos, selector, F12 y perfiles conservados; validación de entrada/carga reforzada | Diff/inventarios; el bloque 1 sólo reordena la validación del rango de edad en row_for_model, sin ajustar ni sustituir el modelo | Que todos los componentes externos estén conectados |
| E50 accesible describe once variables y synthetic_pmu_severity | Probada en secciones seleccionadas del PDF antiguo | Que .6743 de ese modelo sea MAE HU; que el último texto para el 15 sea idéntico |
| Cierre del documento final | Propuesta y pendiente de decisión | Aprobación literal de Santiago/Cecilia o cambios ya incorporados al PDF |

La fuente primaria PMUM y NIST se utilizan dentro de su alcance, no como aprobación del producto. Los experimentos recuperados en memoria no crean un modelo de entrega. Los resultados recuperados se incorporaron al paquete revisado y la evidencia Windows recibida se conserva junto con este cierre. La propuesta de tesis permanece revisable; el resumen de etapas no sustituye los logs completos del entorno externo.
