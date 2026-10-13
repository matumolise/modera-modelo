# Ejemplos ficticios de contrato

Todos los ejemplos se copiaron de las trazas del ensayo integrado de `1fd977c`,
sin regenerar tarjetas, números o IDs. `metadata.json` registra su procedencia
y hashes de JSON canónico e identidades de blob Git. Los hashes canónicos no
dependen de la conversión LF/CRLF de Windows. No es parte del cuerpo HTTP.

| Archivo | Uso |
|---|---|
| opening_request.fictitious.json | Entrada de 28 días para apertura de aumento |
| opening_response.fictitious.json | Recibo original de apertura; card_version=1 |
| return_response.fictitious.json | Recibo original de retorno; misma tarjeta, versión 3 |
| history.fictitious.json | Historial completo de tres versiones, incluida la actualización inconclusa |
| insufficient_request.fictitious.json | Entrada con un día MISSING, minutes=null y calidad no verificada |
| insufficient_response.fictitious.json | Evaluación insuficiente sin tarjeta |

Asignación y calidad verdaderas en el ejemplo de apertura pertenecen únicamente
al oráculo del fixture. La cobertura de las representaciones originales permanece
desconocida. Los IDs C1 remiten a ese almacén ficticio, no a un backend real.
Para la demo, mantener un entorno de ensayo y perfiles ficticios; no copiar esas
banderas ni los IDs a una familia. No se acredita lectura/push o eficacia.

Los parsers publicados aceptaron ambas entradas y los cuerpos caben en 16384
bytes. Se cotejaron vínculos C1/serie y tarjetas con sus versiones del historial.
No se volvió a ejecutar un benchmark ni se modificó ningún servicio.
