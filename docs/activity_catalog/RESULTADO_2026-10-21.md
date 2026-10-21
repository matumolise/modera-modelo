# Resultado de la actualización del catálogo

La revisión se realizó sobre `04f1e3a9076d914bccad49d356184d8b7b45ec13`, en
la rama nueva `activity-catalog-cecilia-review-candidate`. El código comprobado
es `95f92729e11a8c2218c38b4d95cff2e538d4f752`. Los commits posteriores de
esta entrega incorporan documentación y evidencia, sin modificar ese código.

## Resultado comprobado

| Comprobación | Resultado |
| --- | --- |
| Word del 19/10 frente al catálogo | Coinciden los 18 títulos y todas las líneas de materiales y consignas. Se comprobó el SHA-256 del original. |
| Pruebas focalizadas | 128 aprobadas y 45 subtests. |
| Regresión completa | 497 aprobadas y 192 subtests. |
| HTTP nativo | PASS con datos ficticios, reinicio de proceso, recibos originales e historiales sin duplicados. Incluye ofertas infantiles, histórico C1 y mensajes adultos. |
| Actualización desde recibos de `04f1e3a` | Se reconstruyeron almacenes ficticios generados por el código original. Se conservaron respuestas e historial, incluidos textos e IDs retirados. |
| Contrato HTTP y selector | Mismos campos y misma función del selector. Cambia la huella del catálogo y, por diseño existente, puede cambiar la selección de solicitudes nuevas. |
| Archivos de C1, PMUM, mensajes adultos y política del coordinador | Sin cambios respecto de la base. No se modificaron sus parámetros. |

Las pruebas se ejecutaron en Linux con Python 3.12.14, dependencias existentes
y pytest 9.1.1. Persistió una advertencia heredada de TestClient sobre httpx.
Los informes están en `evidence/2026-10-21/`. Son resultados de esta versión,
no una atribución de las comprobaciones previas de Windows o Docker.

## Correcciones necesarias para conservar compatibilidad

Se distinguió el catálogo activo de los IDs históricos admitidos. Esto evita
errores al recibir antecedentes o exclusiones antiguos y permite registrar
respuestas a ofertas previas. Una actividad retirada no vuelve a sugerirse ni
se convierte en su sustituta. Tampoco se transfieren selecciones o preferencias
de una actividad distinta a la nueva.

Se actualizó la matriz funcional con el texto vigente. Conserva el estado
provisional, sin aprobación profesional ni mapeo automático de condiciones.

Dos ensayos heredados suponían que no había actividades voluntarias de la
categoría `quiet`. Se corrigieron sus exclusiones para representar el caso sin
actividades elegibles. Otro ensayo fijaba una huella que incluía el catálogo
antiguo. Ahora comprueba que «ninguna» produce la misma selección que filtros
vacíos y conserva la huella original del selector. No se alteró la lógica para
forzar resultados de esas pruebas.

## Lo que falta comprobar fuera de este entorno

- Ejecutar las comprobaciones de esta versión en Windows y reconstruir Docker.
- En Android, mostrar materiales y consigna completos, permitir releer y
  comprobar el recorrido con backend. No se modificó la interfaz de Juanma.
- Recibir la segunda devolución de Cecilia. La primera devolución motivó las
  correcciones, pero no acredita aprobación del catálogo revisado.
- Resolver el mapeo funcional si se pretende excluir automáticamente a partir
  de las condiciones generales del formulario. El servicio actual se abstiene
  cuando ese mapeo no está resuelto. Este paquete no introduce reglas clínicas.
- Mantener separado el cotejo del export Android y la validación de captura
  real. Este trabajo no cierra esa integración.

No se publicó ni desplegó la actualización. El PDF entregado permanece intacto.
