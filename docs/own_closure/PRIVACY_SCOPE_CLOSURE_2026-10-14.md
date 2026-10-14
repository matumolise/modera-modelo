# Tarea 4: cierre de privacidad de nuestra parte documental

## Resultado y alcance

**Cerrados inventario, minimización, fronteras de acceso y contrato de conservación/
eliminación de analytics.** No se certifica cumplimiento operativo de la aplicación.
Se conserva la separación acordada: esta entrega documenta nuestro componente;
cuentas, Android, backend, infraestructura y ejercicio real de derechos se integran
después. No se añade una API de supresión sin identidad/autorización del producto.

Base local `edc8641b21d34e67a32ebeda537e8f6d15b40175`, importada por Matías; nueva
rama `privacy-own-scope-closure-candidate`. Sólo documentación/evidencia. No se
cambian modelo, parámetros, catálogo, reglas, stores o ramas anteriores; no se
publica, despliega, contacta terceros ni empieza la redacción de tesis.

El material específico de Juanma sobre la ley no se recuperó como documento
identificable en la búsqueda. Dos documentos de decisiones del modelo de agosto
fueron examinados parcialmente y buscados por términos pertinentes; no se les
atribuye autoría de Juanma ni lectura completa. No se afirma que su material no
exista. Su cotejo posterior no bloquea este contrato técnico.

## Fundamento normativo contrastado, no certificación

La Ley 25.326 contempla datos de personas determinables; pertinencia/finalidad,
información y consentimiento con excepciones, protección de información sensible,
seguridad/confidencialidad, acceso y rectificación/supresión. Exige destruir datos
que ya no sean necesarios; prevé excepciones de conservación. Acceso: diez días
corridos; rectificación/supresión/actualización: cinco hábiles. Sus artículos12,
21 y25 también requieren revisar transferencias, registro y tratamiento por terceros.
La excepción del art25 de hasta dos años no es una retención universal automática.
[Texto actualizado oficial, arts2,4–10,12,14–16,21,25](https://www.argentina.gob.ar/normativa/nacional/64790/actualizacion).

El Decreto1558/2001 reglamenta ese marco y exige contrato/instrucciones y seguridad
en el tratamiento por encargo; no basta denominar un servidor «interno».
[Texto oficial, art25](https://www.argentina.gob.ar/normativa/nacional/70368/actualizacion).

La Resolución AAIP47/2018 aprueba medidas **recomendadas** sobre acceso, cambios,
respaldo, incidentes y destrucción, apoyando la obligación de seguridad sin volver
cada recomendación un mandato literal independiente.
[Texto y secciones del anexo I](https://www.argentina.gob.ar/normativa/nacional/resoluci%C3%B3n-47-2018-312662/texto).

Se recuperó ahora el anexo de AAIP4/2019, que antes no estaba disponible. Su
criterio5 considera autonomía progresiva; si el menor no puede consentir de modo
informado, requiere consentimiento de quien ejerce responsabilidad parental/tutela
y esfuerzos razonables para verificarlo. El criterio de la resolución es obligatorio
para sujetos alcanzados. No fija aquí una edad universal13/16; no se usa una
propuesta de reforma como ley vigente.
[Resolución](https://www.argentina.gob.ar/normativa/nacional/resoluci%C3%B3n-4-2019-318874/texto),
[anexo, criterio5](https://www.argentina.gob.ar/normativa/318874_res4AAIP_pdf/archivo).

Consulta de estas fuentes: 14/10/2026. Para uso real, responsable del producto y
revisión competente deben resolver categoría/finalidad/base aplicables, incluyendo
datos que puedan revelar salud. Una etiqueta funcional o score estimado no elimina
ese análisis. No se presume que una casilla parental autorice cualquier tratamiento.

## Inventario actual, propósito y minimización

| Clase | Necesidad de analytics | Persistencia / decisión |
|---|---|---|
| PMUM HU | Edad6–12, código de sexo, dos categorías parentales, informante/período | Inferencia en memoria; no store de solicitudes PMUM propio. No requiere nombre, DNI, dirección ni nacimiento exacto |
| Exports F12 | Eventos/consulta necesarios para reconstruir duración y explicar procedencia | El CLI conserva originales completos, incluidos campos de aplicación si existen. No afirmar que el crudo completo está minimizado |
| Binding/asignación | Perfil/serie/dispositivo/asignación opacos, zona, día y versión | Asociación civil queda en backend autorizado; hashes/IDs no acreditan anonimato |
| C1 | Duración diaria, intervalo/status/cobertura/flags/procedencia, referencia, estado y recibos | JSON mantiene representaciones/historia/streams/recibos. No solicita diagnósticos ni respuestas PMUM |
| Tarjetas adultas | Días/revisiones/contexto, episodios, versiones y recibos | SQLite conserva payloads originales y resultados; ventanas14/28/56 no son retención |
| Coordinador infantil nuevo | Identidad global, intervalo/tiempos, condiciones operativas, filtros/intereses y ofertas/respuestas | SQLite guarda evidencia de apertura, estado, eventos y recibos. El TTL10min cierra oportunidad/respuesta; **no borra datos** |
| Historial infantil legado | child_id, oferta, actividades, selección/rechazo/postergación/ignorado y timestamps | JSONL; entero legado necesita namespace/aislamiento definido por integración |
| Elegibilidad/condiciones | Filtros funcionales explícitos, no inferencias clínicas | No crear texto libre de diagnósticos ni nuevos mapeos antes de revisión del catálogo. Filtros pueden revelar información sensible según contexto |
| Logs/temporales/backups | Mínimo diagnóstico operativo y recuperación autorizada | No guardar por defecto tokens/cuerpos reales; access logs pueden contener IDs en URL. No se auditó configuración de logging del despliegue |

**Contrato de minimización propio:** no agregar identidad civil o diagnósticos a
estos payloads; mantener respuestas omitidas como desconocidas; no reemplazar
declaraciones por inferencias Android; usar IDs opacos sin nombres/DNI embebidos.
El validador de IDs sólo comprueba formato, no opacidad o titularidad.

Para futuros exports de duración, el collector puede tener un contrato minimizado
antes de fijar sus originales. El preparador no debe quitar campos de un original
congelado manteniendo el mismo hash. Si se reduce crudo, versionar medición/
procedencia, verificar equivalencia y registrar la disponibilidad real de originales.
No se edita el collector ni el preparador en esta entrega.

HU/fuentes de investigación y autorización para familias argentinas son ámbitos
distintos. No se redistribuyen microdatos o joblib en este cierre. El modelo HU
estático no aprende de los niños de la app; borrar una cuenta no requiere modificar
ese binario por los datos de esa cuenta. No se certifica por ello anonimato de la
fuente de entrenamiento ni se reemplaza su gobernanza/licencia.

## Controles existentes y frontera de responsabilidades

| Control | Comprobado/implementado | Responsable de integración / aceptación |
|---|---|---|
| Autenticación de servicio | Bearer antes de leer/parsear cuerpo, comparación segura, errores genéricos, límites/timeouts | Juanma: secreto aleatorio por entorno, rotación, red privada; no distribuir a Android |
| Acceso por perfil | Filtro por profile_id en historial adulto; separación de estados por ID infantil | Backend verifica cuenta/representación autorizada en **cada** operación. Conocer ID o token común no da autorización familiar |
| Respuestas/health | Cache-Control:no-store; salud no expone token, rutas o sujetos en los casos revisados | Infra: cachés/proxies/logging; no atribuir privacidad integral al header |
| Integridad/replay | Recepción original, hashes, conflictos, atomicidad y recuperación de stores | Equipo/infra: backup/restauración consistentes y permisos reales. Hash no equivale a autenticación ni cifrado |
| Transporte/disco | HTTP interno, JSON/SQLite/JSONL legibles, sin cifrado/ACL desplegados acreditados | Infra: enlaces protegidos según topología, permisos efectivos, claves/cifrado y volúmenes; no exponer puerto/token al público |
| Identidad infantil | Nuevo coordinador exige profile_id; legado usa entero | Backend: namespace global y asignaciones verificadas; no compartir «niño1» entre cuentas |
| Consentimiento/información | No se implementa el flujo de cuentas/representación en analytics | Responsable de producto: aviso comprensible, finalidades, prueba de identidad/representación y registro; consideración de autonomía progresiva |
| Derechos/conservación | Ubicación de clases y dependencias identificadas, rectificación versionada adulta | Producto/backend/infra: ejercicio integral, calendario, bloqueo/purga y antiresurrección probados |

El rol jurídico de responsable/encargado del sistema se debe designar; no se
deduce del nombre de un desarrollador. Juanma queda como implementador del
backend, no como responsable legal único por esta tabla. Si se utiliza un
proveedor/región exterior, revisar el tratamiento y transferencias antes de
datos personales reales; no se selecciona ahora proveedor o región.

## Conservación: decisiones por finalidad y evento

No se inventa un plazo30/90días ni se conserva todo para siempre. La política
se define por clase y fin; **antes de datos reales**, responsable del sistema debe
asignar el plazo máximo/revisión y el calendario de backup correspondiente.
El documento cierra este requisito, no simula un temporizador implementado.

| Clase | Condición de conservación propuesta para integración | Cese y dependencia |
|---|---|---|
| Solicitud PMUM | Procesamiento transitorio; persistencia adicional del backend sólo con finalidad declarada | No es necesario guardar todas las estimaciones para que funcione analytics |
| Crudo F12/binding/cola | Reconciliación, reproducción o incidente delimitados y con máximo fijado | Al cesar propósito, purgar copias/cola; no afirmar que un hash sin originales permite reproducirlos |
| Serie C1 | Historia requerida mientras la serie y finalidad estén activas | No truncar all-prior en secreto; cierre/supresión comprende dependencias del estado y recibos |
| Tarjetas/revisiones/recibos | Comunicación vigente, corrección y replay/auditoría con necesidad justificada | Versionar no autoriza archivo perpetuo. Versiones retiradas no se muestran como afirmaciones vigentes |
| Ofertas/respuestas | Coordinación, preferencias observables y diagnóstico operativo limitado | Expiración o rechazo no son supresión. Al cesar propósito, eliminar evidencia/estado/recibos asociados |
| Backups/logs/temporales | Recuperación/operación acotadas y protegidas | Plazo y proceso explícitos; reconciliar exclusiones antes de restaurar servicio |
| Evidencia académica ficticia | Conservación de versiones de ensayo para reproducir metodología | No incorporar familias reales a pruebas, Git, bundles o chats por defecto |

## Unidad de eliminación y procedimiento futuro concreto

**Unidad lógica: perfil dentro de su cuenta autorizada y todos sus datos derivados.**
Una fecha, fila o tarjeta aislada no cubre ese alcance. La unidad física depende
de la partición real: no borrar un store compartido para suprimir sólo una familia.
No hay hoy función integral de purge ni prueba de borrado seguro del producto.

Hallazgo nuevo del coordinador: `receipts` guarda id/fingerprint/body, sin columna
profile_id. Una respuesta de supresión operativa («automatic_disabled») no incluye
perfil en el body. Eliminar sólo `state.profiles[perfil]` deja esos recibos sin
localización completa y contradice además receipt_count si se retiran filas sin
actualizar estado. **No es suficiente borrar el estado visible.**

El contrato para integración exige índice autoritativo de propiedad de peticiones,
incluidas suprimidas/fallidas, y vinculación de todos los IDs/series/artefactos.
Debe existir antes de operar con datos reales: en el backend como índice durable,
o mediante migración explícita de store con cobertura verificable. No se atribuye
su implementación actual ni se inventa una migración que pueda deducir perfiles
de hashes irreversibles. Un store aislado permite borrar su unidad completa,
pero no se afirma que el servicio actual esté particionado por cuenta.

Procedimiento de aceptación futura, coordinado por backend/infra:

1. Autenticar solicitante y legitimación; determinar perfil/cuenta/series y alcance,
   decisión aplicable, plazos y cualquier conservación excepcional justificada.
2. Bloquear nuevas capturas/envíos/ofertas para el alcance, aislar trabajos en curso
   y conservar exclusión mínima protegida mientras haya posibilidad de restauración.
3. Inventariar originales, bindings, cola, índices, C1, tarjetas, coordinador,
   JSONL, snapshots, temporales, logs y backups; comprobar propiedad sin tocar terceros.
4. Ejecutar una operación coordinada y recuperable con escritores detenidos o
   controlados. Mantener invariantes y resolver fallos; no anunciar supresión completa
   cuando sólo una de las bases respondió. No quitar locks/marcas para forzar readiness.
5. Verificar ausencia/inaccesibilidad según el tratamiento autorizado. DELETE o
   unlink no prueban borrado seguro de páginas SQLite, snapshots, journals o disco.
   Infra debe justificar método efectivo sobre los soportes/claves correspondientes.
6. Aplicar el criterio a copias/backups y consumidores; restauración y retry viejos
   deben respetar exclusión antes de reactivar datos. No recrear perfiles retirados
   con los mismos trabajos antiguos o IDs reutilizados.
7. Registrar constancia mínima de operación/alcance/resultados, sin copiar otra vez
   cuerpos, diagnósticos o el historial que se quiso eliminar. Comunicar estado real.

Si la solicitud es rectificación, la última versión vigente debe distinguirse de
evidencia retirada. El historial adulto ya conserva versiones, pero no reemplaza
la decisión de conservar información anterior. C1 rechaza conflicto de un registro
original: no existe API de revisión retrospectiva integral. Su tratamiento requiere
procedimiento versionado/invalidación de dependencias y evidencia autorizada al
integrarse; no reescribir un recibo o fabricar otra serie para ocultar una corrección.

La inmutabilidad sólo describe el comportamiento técnico **durante una conservación
autorizada**. No impide atender derechos ni obliga a mantener identificadores/cuerpos
perpetuamente. No se ejecutaron operaciones destructivas sobre evidencia del usuario.

## Verificación de este bloque y conclusión

- Seis pruebas focalizadas: **6 aprobadas, 2 subtests, 132 deseleccionadas**, una
  advertencia heredada, 1,15s. Autenticación antes del cuerpo, límites, health,
  historial adulto e identidad/filtrado del coordinador. No es otra suite global.
- Comprobación ficticia adicional: PASS de 401 antes de parsear, no-store, ausencia
  del token en health, separación por perfil adulto y límite de propiedad de recibos
  suprimidos. `COMPONENT_PRIVACY_CHECK.json` conserva alcance y resultados.
- No se demostró un bypass nuevo de los controles implementados que requiera parche.
  Los faltantes de autorización familiar, purga/índice completo y medidas de entorno
  quedan **requisitos operativos pendientes**, no funciones declaradas implementadas.
  Resolverlos ahora ampliaría el bloque a la integración diferida por Matías.

**Tarea4 cerrada como diseño/auditoría documental de nuestro componente.** Se puede
afirmar que el diseño identifica datos, controles y ciclo de vida, con fundamento
normativo contrastado. No se puede afirmar «la app cumple la ley», «los datos están
anonimizados/cifrados» o «la supresión real funciona» por estos tests. Los criterios
concretos anteriores quedan a cargo del sistema integrado para la etapa posterior.
