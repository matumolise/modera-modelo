# Revisión de corrector y resultados

13/10/2026. El contrato inicial tenía tres decisiones abiertas (C1, volumen,
correcciones) y sólo15 pruebas aritméticas. No era producto integrado. En esta
rama se implementa la capacidad HTTP y la persistencia de tarjetas del candidato.

## Correcciones de esta revisión

- Se fijó un perfil inicial y el rol complementario de C1, sin atribuir a un
  experimento no ejecutado una inferioridad del gate C1. No cambia el detector.
- Tope basado en creación, no entrega/visualización que el backend no acredita.
- Revisión diaria creciente y original conservado; recibos de reintentos no cambian.
- Cierre de disminuciones simétrico y explícito; el contrato previo sólo ilustraba
  principalmente avisos de aumento. Contexto y datos insuficientes no son resolución.
- El conteo de días usa referencia original; la exclusión afecta sólo diferencia.
- Decisiones con Fraction sin redondeo; redondeo sólo en texto.
- Calidad desconocida no se convierte en true; ausencia no se convierte en cero.
- Duración máxima de minutos según el día local real, incluidos cambios DST.
- Capacidad deshabilitada por defecto preserva el /health anterior: una primera
  ejecución detectó la regresión de agregar una cuarta capacidad DISABLED; se corrigió
  la implementación, conservando las pruebas anteriores.
- Revisión de reportes: la evaluación en el límite56 ocurre antes de observar el
  primer dato modificado. Se corrigió el reporte para excluirla de la fase posterior
  y de demoras, y se repitió con idéntico perfil. No se cambiaron umbrales.

## Pruebas

Python3.12.14, dependencias fijadas por requirements-analytics-test.txt, pytest9.1.1.
Suite tests/ y siete módulos de raíz:366 passed,190 subtests passed. Incluye28
tests nuevos de mensajes (sus subtests no se suman como tests independientes).
Advertencia heredada Starlette/httpx, sin cambio de dependencias.

Probados: aperturas en ambas direcciones, patrón semanal/pico, retorno y solapamiento,
faltantes/calidad, referencia0, revisión/conflictos/rollback, original conservado,
corrección de avisos activos y archivados, cambios de serie, vigencia/espera/tope,
reinicio y replay, equivalencia de payload ordenado, cuatro requests concurrentes,
HTTP autenticado, deshabilitación y pérdida de repositorio. Demo también ejecutada.

No se probó Android físico, despliegue Windows/AWS o código de tesis_backend.
Los tests originales no modifican el alcance de esa evidencia anterior.

## Perfil fijo sobre simulaciones dependientes

1000 series ficticias,13000 evaluaciones semanales.600 series reutilizadas del
benchmark C1 más400 derivaciones para bajas/retorno/cero aislado.50 semillas por
celda, mismos ruidos; no son1000 familias independientes ni validación externa.

Fase posterior: evaluaciones del límite56 excluido hasta112 inclusive. Columnas:
series con alguna nueva tarjeta /50 y total de nuevas tarjetas (ambos sentidos).

| Escenario | sigma .15: series / tarjetas | sigma .35: series / tarjetas |
|---|---:|---:|
| S0 nivel plano con ruido |0 /0|13 /16|
| S1 pico de un día |0 /0|16 /17|
| S2a escalón +25% |42 /42|29 /31|
| S2b escalón +50% |49 /49|40 /40|
| S3a patrón semanal x1.5 desde inicio |0 /0|21 /23|
| S3b patrón semanal x2.5 desde inicio |1 /1|24 /26|
| Baja25% |45 /45|32 /32|
| Baja50% |50 /50|36 /36|
| Escalón50% por14 días y retorno |49 /49|46 /51|
| Escalón50% con un cero aislado |49 /49|41 /41|

Estas cifras incluyen ambos sentidos: una tarjeta en S2a no necesariamente es
un aumento. Con sigma .35, S2a tuvo23 aperturas de aumento y8 de disminución;
28/50 trayectorias no abrieron un aumento después del límite56. Para S2b fueron
38 aumentos y2 disminuciones;12/50 sin apertura posterior de aumento. Los episodios,
topes y aperturas previas pueden afectar esas omisiones.

Lectura limitada: con ruido bajo la regla evitó nuevas tarjetas en S0/S1 durante
reporte y respondió a muchos escalones/bajas; con ruido alto generó considerable
carga aun sin cambio del nivel del generador. Puede haber diferencias reales entre
promedios observados sin cambio nominal del generador. No son falsas alarmas clínicas.
El perfil no se presenta como calibrado o apto para familias. El resultado se publica
íntegro; no se ajustan valores hasta obtener una tabla más favorable.

## Cierre real de esta entrega

Motor, valores iniciales, estados, persistencia, contrato HTTP y demo implementados.
La siguiente tarea de Juanma es conectar datos verificados y DTO a la pantalla,
no reinterpretar los informes anteriores. La revisión profesional y evidencia con
familias permanecen como límites externos, sin simular aprobación inexistente.
