# Estado vigente de los cuatro frentes propios

Esta matriz sustituye el uso del informe previo e43695a como lista de pendientes.
Conserva cierres acumulativos y restricciones; no redacta tesis ni aprueba producto.

| Frente propio | Estado para esta entrega documental | Evidencia | Responsable y cierre |
|---|---|---|---|
| 1. Ofertas infantiles | Coordinador implementado y contrato cerrado | Código0d806c2, candidato0d2bdee; Linux451/192subtests; Windows450/uno omitido/192subtests; 46 focales y cinco escenarios ficticios PASS | Matías/componente; importar/validar ya realizado. Entrega visual sigue diferida |
| 2. Trazabilidad PMUM | Cadena recuperable cerrada; fijo/anidado y NoChildren resueltos | e3031a3; fuente/SAV/hash originales, registro del ajuste, manifiesto hash-idéntico, auditoría readonly PASS y originales cotejados en Windows | Matías/componente; no snapshot prefit probado ni weekday literal completo, no reproducción bit a bit/validación externa |
| 3. Configuración C1 | Perfil experimental conservado y afirmaciones cerradas | edc8641; huella confirmada Windows, 14 blobs y seis salidas cotejados; 69 pruebas/42subtests y tres fixtures acotados PASS | Matías/componente; sin convertir SMOKE en calibración de producto |
| 4. Privacidad | Inventario/contrato de minimización, acceso y ciclo de vida cerrados | Informe actual, fuentes oficiales y seis pruebas/dos subtests + comprobación ficticia | Matías/diseño; no certificado de cumplimiento ni purga integral implementada |

Los conteos pertenecen a ejecuciones específicas, no se suman entre bloques.
Tareas2/3/4 no cambian el runtime probado en Windows; no se les atribuye otra
ejecución global. La herramienta offline de tarea2 tiene su propia verificación.

## Decisión sobre redacción

**Los cuatro frentes permiten comenzar la redacción de nuestra parte con el
alcance y evidencias registrados.** No apareció otra tarea técnica propia,
indispensable y acotada para esta entrega documental al contrastar este bloque
con los contratos y cierres. No es garantía de haber recuperado todos los chats
o la última versión de cada documento académico.

Antes/durante la redacción deberá cotejarse la versión vigente de requisitos y
texto académico: entradas parentales de HU frente al antiguo modelo Android,
función de C1 frente a tarjetas, RF-10/CU-04 y separación de resultados reales/
ficticios. Ese trabajo editorial no se declara hecho ni se adelanta aquí.
No se convierte una falta de validación en una métrica inventada o aprobación.

## Diferidos que permanecen registrados

| Frente posterior | Estado y criterio de aceptación | Responsable |
|---|---|---|
| Catálogo/condiciones/adaptaciones | Cecilia dijo que revisaría; aún sin dictamen recibido. Vincular devolución a versión exacta y aplicar observaciones verificables | Cecilia/equipo |
| Integración real | Captura física, identidad/cobertura, backend/Android, acuses/deduplicación visual, operación y despliegue no ejecutados ahora | Juanma/equipo |
| Privacidad operativa | Identidad/representación, aviso/base, propiedad de solicitudes, medidas del entorno, calendario de retención, supresión y restauración sin resurrección | Responsable del producto por designar; backend/infra |
| Uso real/calibración y adaptación de instrumentos | No acreditados por fixtures; C1 sin perfil calibrado y PMUM sin validación externa, weekday adaptado declarado | Equipo/revisión correspondiente |

El material de privacidad de Juanma se cotejará cuando esté disponible; no se
afirma haberlo leído. La revisión profesional del catálogo no acredita privacidad,
calibración C1 o precisión PMUM. Estos puntos futuros no se ejecutan automáticamente
ni se presentan como realizados para llamar al producto completo.
