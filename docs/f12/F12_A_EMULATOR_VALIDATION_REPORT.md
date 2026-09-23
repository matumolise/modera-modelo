# F12-A — Validación técnica Android en emulador

Estado: evidencia experimental consolidada. Este documento no define todavía las reglas productivas de reconstrucción de comportamiento de Moderá.

## 1. Objetivo

Validar empíricamente qué información entrega UsageStatsManager.queryEvents(...) antes de definir sesiones de dispositivo, aperturas de aplicaciones, cambios de aplicación o métricas históricas.

El instrumento utilizado es diagnóstico. No genera BehavioralObservation, no ejecuta el Historical Analyzer y no produce alertas ni recomendaciones.

## 2. Entorno validado

- Dispositivo: Pixel 8 emulado.
- Android API: 37.
- Manufacturer reportado: Google.
- Model reportado: sdk_gphone16k_x86_64.
- Fuente: UsageStatsManager.queryEvents(...).
- Rama de trabajo: phase12-f12a-android.

Las conclusiones de este documento se limitan a este entorno salvo que se indique explícitamente lo contrario.

## 3. Resultados

### A1 — Pantalla y keyguard

Estado: PASS en emulador/API 37.

Se observaron separadamente SCREEN_INTERACTIVE, SCREEN_NON_INTERACTIVE, KEYGUARD_SHOWN y KEYGUARD_HIDDEN.

La evidencia muestra que el estado interactivo de la pantalla y el estado del keyguard no representan el mismo fenómeno ni necesariamente ocurren simultáneamente.

Conclusión:

SCREEN_INTERACTIVE != UNLOCK

No se define todavía KEYGUARD_HIDDEN como DEVICE_SESSION_START.

### A2 — Activities internas

Estado: PASS en emulador/API 37.

Una única entrada externa a Settings produjo múltiples eventos ACTIVITY_RESUMED debido a navegación entre Activities internas.

Conclusión:

ACTIVITY_RESUMED != APP_OPENING

Por lo tanto, contar directamente eventos ACTIVITY_RESUMED produciría una sobreestimación de aperturas.

### A3 — Cambio entre aplicaciones y retorno

Estado: PASS en la repetición controlada.

La primera ejecución se conserva como evidencia auxiliar. La ejecución canónica utilizó Recents para realizar una transición Settings -> Chrome -> Settings.

Se observó el cambio y posterior retorno entre paquetes. También se observaron eventos del launcher asociados a Recents.

Conclusión:

un cambio de paquete es observable, pero:

PACKAGE_TRANSITION != APP_OPENING

y no se asume todavía que cada transición constituya un foreground episode productivo.

Los eventos del launcher se preservan en la captura cruda.

### A4 — Aplicación en background sin bloqueo

Estado: PASS en emulador/API 37.

Settings pasó a background y el launcher quedó activo mientras la pantalla continuó interactiva. SCREEN_NON_INTERACTIVE y KEYGUARD_SHOWN ocurrieron posteriormente.

Conclusión:

APP_BACKGROUND != SCREEN_OFF != KEYGUARD_SHOWN

Por lo tanto, llevar una aplicación al background no puede utilizarse directamente como final de una sesión de dispositivo.

### A5 — Recuperación retrasada y consultas solapadas

Estado: PASS para el alcance experimental definido.

Se realizaron dos consultas de una hora con ventanas ampliamente solapadas. La segunda captura ocurrió aproximadamente 12 minutos y 20 segundos después de la primera.

Los 219 eventos crudos de la primera captura fueron recuperados nuevamente en la segunda al comparar el contenido observable del evento independientemente de los metadatos propios de cada collector run.

Conclusiones:

- eventos anteriores pueden recuperarse retrospectivamente dentro del intervalo probado;
- consultas solapadas pueden devolver nuevamente eventos ya observados;
- repetición entre consultas no implica que haya ocurrido un evento nuevo;
- el collector productivo necesitará una estrategia idempotente para ventanas solapadas.

Este experimento NO determina el límite máximo de retención de Android y NO valida todavía WorkManager, reinicios ni persistencia productiva.

## 4. Restricción de identidad/deduplicación

UsageEvents.Event no proporciona un identificador único general utilizable por el logger.

Durante la validación se observaron eventos indistinguibles mediante una clave simple formada por:

eventTimeEpochMs + eventTypeCode + packageName + className

Por lo tanto, esa combinación no debe tratarse como identidad única ni utilizarse para deduplicación destructiva.

La captura cruda debe preservar multiplicidad. La estrategia de reconciliación/idempotencia se definirá posteriormente.

## 5. Evidencia no canónica

SMOKE_PRE_FIX fue producido antes de corregir el mapper de nombres de eventos modernos.

Sus códigos crudos pueden conservarse para trazabilidad, pero sus eventTypeName no constituyen evidencia semántica canónica.

SMOKE_POST_FIX se conserva como smoke test posterior a la corrección.

A3_AUXILIARY se conserva como evidencia auxiliar porque la transición ejecutada no correspondió exactamente al protocolo canónico posterior.

## 6. Límites de lo validado

Estos experimentos no validan todavía:

- comportamiento en dispositivo Android físico;
- diferencias entre OEM/API;
- límite máximo de retención de UsageEvents;
- scheduler productivo;
- WorkManager;
- persistencia Room definitiva;
- comportamiento exhaustivo bajo Doze/restricciones OEM;
- restart/shutdown;
- medianoche y cambio de zona horaria;
- revocación/restauración de Usage Access;
- definición final de DEVICE_SESSION;
- definición final de APP_OPENING;
- adapters RawUsageEvent -> BehavioralObservation.

Ninguno de esos puntos debe inferirse como resuelto por A1-A5.

## 7. Restricciones semánticas obtenidas

La evidencia acumulada obliga a preservar las siguientes separaciones:

- SCREEN_INTERACTIVE != UNLOCK
- ACTIVITY_RESUMED != APP_OPENING
- APP_BACKGROUND != SCREEN_OFF
- APP_BACKGROUND != DEVICE_SESSION_END
- PACKAGE_TRANSITION != APP_OPENING
- eventos del launcher/Recents no implican automáticamente uso intencional del launcher;
- un evento repetido en una consulta solapada no implica un evento conductual nuevo.

Estas restricciones deberán respetarse al diseñar posteriormente los adapters y representaciones históricas.

## 8. Inventario reproducible de evidencia

Los exports crudos se mantienen fuera del repositorio público. Los SHA-256 permiten identificar exactamente los archivos utilizados en esta validación.

| Caso | Run ID | Archivo | Bytes | SHA-256 |
|---|---|---|---:|---|
| A3_AUXILIARY | 612f8e7dd6814f4fbc419087e8fa0fc7 | summary_612f8e7dd6814f4fbc419087e8fa0fc7.json | 311 | 8BED8CB54D33EDEA8B9598001EA50803717BD2EA291E84D522C040DB329C717E |
| A3_AUXILIARY | 612f8e7dd6814f4fbc419087e8fa0fc7 | events_612f8e7dd6814f4fbc419087e8fa0fc7.jsonl | 71896 | 20FB8BA98C2F1D87F229DCE6993DF0726C20977EA747EE9779DC68B2BC497009 |
| SMOKE_POST_FIX | e55387063ceb46d3907fa6bb43e6acf0 | summary_e55387063ceb46d3907fa6bb43e6acf0.json | 311 | DCA9CF010C61C0CDEE21693E8B63FBDE425146174CC0B11F01F95CD2D52F7F6F |
| SMOKE_POST_FIX | e55387063ceb46d3907fa6bb43e6acf0 | events_e55387063ceb46d3907fa6bb43e6acf0.jsonl | 99177 | 2D71138EC47F0C418263ECA6232B538375DFAF56908D08EEE97C20215ECF8901 |
| A4 | 2a14a1ee7b2b4fd0bc5ea79434814cdc | summary_2a14a1ee7b2b4fd0bc5ea79434814cdc.json | 311 | B85C52EDE10BB5060938BE87604E3387F2845C4CE2B00B76E831C4C59098931B |
| A4 | 2a14a1ee7b2b4fd0bc5ea79434814cdc | events_2a14a1ee7b2b4fd0bc5ea79434814cdc.jsonl | 94753 | 93FD71ABC0963400361B5AA9D11D9D87A603B178B22372C30FA099619D8485BD |
| A3_CANONICAL | 7324079a4f284ad2a0510241f9a09d24 | summary_7324079a4f284ad2a0510241f9a09d24.json | 311 | 1B6F480A904DD669F77C6DD124595352851926A3F91A95E4E9C2B4EC0CB5B163 |
| A3_CANONICAL | 7324079a4f284ad2a0510241f9a09d24 | events_7324079a4f284ad2a0510241f9a09d24.jsonl | 85620 | B35EBB25AF33A866F9A07AF1A56804F853F1E60A284169C0DBEEFB31FC349961 |
| SMOKE_PRE_FIX | 0d3180c9c16147489c7238678814aeec | summary_0d3180c9c16147489c7238678814aeec.json | 311 | 087A3F0FC46459E29775111A6401E63E10AD149BD0EE5783EF7535D1E34A7D7A |
| SMOKE_PRE_FIX | 0d3180c9c16147489c7238678814aeec | events_0d3180c9c16147489c7238678814aeec.jsonl | 92476 | 06AA18390520BE2BDBBB8D581C113D0856104D1E1CBB95FDDC0146EFE4E1FCE9 |
| A2 | c9bc9eb974534ace84100b06806ef528 | summary_c9bc9eb974534ace84100b06806ef528.json | 311 | 1889F324FF132CABA899F4F7CDFBCAA0DAF14128CFFD9CD434BAD3836DDF052E |
| A2 | c9bc9eb974534ace84100b06806ef528 | events_c9bc9eb974534ace84100b06806ef528.jsonl | 51146 | EACA83CEFBF3401C36110637AA111DBA0F3421F340D54C96E7F28A04281E4FAC |
| A5_RUN2 | 2baa6c6760c140bc9a2ce1083e5161a8 | summary_2baa6c6760c140bc9a2ce1083e5161a8.json | 311 | CA7C90CBDDACAD9C81E84817C8B0E04FF890DAE8B2C584C5FACF0318DAB14432 |
| A5_RUN2 | 2baa6c6760c140bc9a2ce1083e5161a8 | events_2baa6c6760c140bc9a2ce1083e5161a8.jsonl | 105070 | 9F4F3644FF78E98009ADB2FC76612443BC6A8C8A01FAA467F92C78BE195D529D |
| A1 | efac7e132765454c89eb25b2e9e97f9b | summary_efac7e132765454c89eb25b2e9e97f9b.json | 311 | 1B2E76EF04E4FEA0DF18AA196070E0BE291022A38F023A9C0F0F27593FB54DD7 |
| A1 | efac7e132765454c89eb25b2e9e97f9b | events_efac7e132765454c89eb25b2e9e97f9b.jsonl | 66623 | 12FD66C206E9387A9E0565D301652E296A02AE669B19663C56970D046A0B17B3 |
| A5_RUN1 | e6944fc142a0450ea7ab2fb6915cba6a | summary_e6944fc142a0450ea7ab2fb6915cba6a.json | 311 | DC396D8860FC25BEFCCBFE46FD835CE79480BBFB3058A3A6FED0B735C4E3E869 |
| A5_RUN1 | e6944fc142a0450ea7ab2fb6915cba6a | events_e6944fc142a0450ea7ab2fb6915cba6a.jsonl | 105070 | 456EC1C6E4E9A15F6F0B47287879216B98088221CE2DF58B67E523F510A7A7AD |

## 9. Estado

A1-A5 quedan completados para el entorno de emulador/API 37 con las limitaciones documentadas.

Esto NO cierra F12-A completa.

El siguiente bloque es validar las conclusiones críticas en al menos un dispositivo Android físico antes de consolidar el contrato técnico de captura.
