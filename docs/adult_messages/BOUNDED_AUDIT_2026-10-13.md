# Revisión acotada de motor y persistencia

13/10/2026. Base local249168a03a10ccc0108145d313f4b3c389556d39, cuyo padre
es109060e0095e2ffe813c6e82d08ec97daaf6dca4. La referencia remota
adult-messages-v1-candidate fue consultada y conserva109060e. Rama nueva:
adult-messages-bounded-audit-candidate. No se publica, integra ni despliega.

## Defectos reproducidos y corregidos

| Caso | Base anterior | Corrección |
|---|---|---|
| Misma serie con otra zona, sin episodio | Usaba registros persistidos y podía crear una tarjeta mezclando la semántica del día | Conflicto409 antes de escribir; cambio de zona requiere serie nueva |
| Misma serie con otra zona, con episodio | Terminaba el aviso pero permitía reutilizar la identidad | Misma guarda para evaluaciones nuevas; replay original se mantiene |
| Reinicio tras perder tabla cards | La recreaba vacía y declaraba listo el store, aunque quedara estado de episodio | Rechazo de store existente incompleto; no crear ni alterar tablas para ocultar pérdida |
| Archivo existente vacío | Lo inicializaba como si fuera nuevo | Indisponibilidad; sólo se inicializa una ruta inexistente |
| Advertencia por corrección C1 | La fecha global del perfil aparecía en otra serie | Fecha mínima por serie; compatibilidad con estado v1 reconstruida desde correcciones registradas |

No se modifica ningún recibo C1. Se corrige únicamente la atribución de la
advertencia en el motor de comunicación. Si un recibo adulto anterior tenía
una advertencia errónea, su replay sigue siendo original; las nuevas evaluaciones
usan el estado corregido por serie. No se finge una revisión del recibo original.

## Verificación

Se añadieron12 tests de regresión y preservación. Ejecutados contra249168a,
6 fallaron y6 pasaron: los fallos corresponden a los defectos de arriba.
Sobre la corrección pasan todos. La suite completa Linux registra378 aprobados
y190 subtests; no se suman los subtests como pruebas independientes.

Las41 comprobaciones focalizadas (12 nuevas,28 de mensajes y1 de catálogo)
también pasaron con locale C, PYTHONUTF8=0 y -X utf8=0. La demo se ejecutó
en ese entorno y produjo JSON legible como UTF8. Eso prueba las correcciones
de codificación heredadas de249168a sin atribuirles la ejecución Windows anterior.

Se verificó explícitamente:

- Replay tras retiro/corrección, avance posterior y reinicio: mismo resultado
  salvo replayed, sin cambios en las tablas de estado, recibos, revisiones o tarjetas.
- Replay equivalente con otro request_id: sólo agrega su alias; no avanza estado,
  cuota ni versión de tarjeta.
- Fallo SQLite al guardar una tarjeta: rollback de revisiones, estado y recibo;
  al eliminar el fallo, el mismo request crea una sola tarjeta correctamente.
- Referencia congelada por fechas, revisión de apertura, límites compartidos y
  conservación de versiones originales; configuración numérica sin cambios.
- Nueva serie con otra zona: transición válida, sin mezclar la historia anterior.

Advertencia heredada de Starlette/httpx, sin cambio de dependencias.
La conexión SQLite de las pruebas nuevas se cierra explícitamente para permitir
limpieza de archivos en Windows. Los tests de raíz pueden generar datos de ensayo
en el worktree; esos archivos se restauran y no forman parte de la corrección.

## Estado al terminar

Queda cerrado este bloque de revisión del motor y persistencia dentro del alcance
probado. La suite Windows365PASS/1omitido pertenece a109060e en modoUTF8,
no a esta corrección. La nueva revisión necesita su propia comprobación Windows.
No se cambia el perfil, no se ejecuta otro benchmark amplio, no se modifica
PMUM/C1/actividades y no se redacta tesis ni se avanza al siguiente bloque.
