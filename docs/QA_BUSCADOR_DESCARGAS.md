# QA: buscador interno de descargas

Base: eMule Community 0.72a personalizada. El filtro opera sobre las filas de la categoría visible; no altera las conexiones, la cola de transferencia ni las carpetas Temp. «Todas» muestra el conjunto permitido por el filtro de categoría original.

## Funcionalidad

- Barra permanente en la vista de descargas y en la vista dividida.
- Búsqueda por nombre, sin distinguir mayúsculas, con todas las palabras introducidas (AND); modo de fragmento o palabra completa. Puntos, guiones, espacios y guiones bajos delimitan palabras.
- Contador de archivos visibles / total de archivos de la categoría, sin contar fuentes; limpiar con botón o Escape desde el campo.
- Seleccionar todo marca únicamente filas de archivo visibles. Ctrl+A en la lista filtrada hace lo mismo; Ctrl+F enfoca el campo. La ventana de búsqueda avanzada original sigue accesible desde el menú contextual.
- Las operaciones por selección usan los comandos originales. «Cambiar destino...» utiliza las categorías persistentes y está limitado a descargas incompletas que no están completándose. No mueve archivos ya completados ni temporales.
- El menú de la pestaña de categoría sigue actuando sobre la categoría completa; no es un menú de selección.

## Pruebas de aceptación pendientes en Windows

| ID | Caso | Resultado esperado |
|---|---|---|
| FIL-01 | Buscar `test` entre Test.iso, test2.iso y sample.iso. | 2/3, sin distinción de mayúsculas. |
| FIL-02 | Activar palabra completa. | Solo Test.iso. |
| FIL-03 | Buscar `test iso` y luego `iso test`. | Mismas coincidencias (AND). |
| FIL-04 | Buscar texto inexistente; pulsar Limpiar. | 0 resultados, selección deshabilitada; lista restaurada. |
| FIL-05 | Expandir fuentes y seleccionar todas las coincidencias. | Solo archivos, nunca fuentes. |
| FIL-06 | Seleccionar coincidencias y cambiar el texto; Ctrl+A. | Ningún archivo oculto queda seleccionado; solo los resultados nuevos se seleccionan. |
| FIL-07 | Pausar, reanudar y cambiar prioridades de resultados. | Solo los seleccionados cambian. |
| FIL-08 | Cambiar de categoría, mover archivos o cambiar el estado de una descarga durante la búsqueda. | El filtro se mantiene y el contador refleja la categoría. |
| FIL-09 | Añadir, renombrar, completar o retirar descargas mientras el filtro está activo. | Las filas y el contador se actualizan; no hay fuentes huérfanas. |
| FIL-10 | Cambiar destino de varias descargas a una carpeta válida y reiniciar. | Se reutiliza/crea la categoría; la carpeta persiste y Temp no cambia. |
| FIL-11 | Cancelar el selector, elegir carpeta inválida o completar una descarga durante el selector. | No se modifica el destino de descargas excluidas o que ya no existen. |
| FIL-12 | Cancelar archivos seleccionados o limpiar completados con filtro. | Solo coincidencias seleccionadas (cancelar), o completados visibles (limpiar); se conserva la confirmación original de cancelación. |
| FIL-13 | Alternar vista dividida, descarga completa, subidas y redimensionar. | La barra no tapa la lista ni aparece en subidas. |
| FIL-14 | Probar nombres Unicode, espacios, guiones, puntos y caracteres no latinos. | Coincidencia coherente con las reglas de Windows; sin excepciones. |
| FIL-15 | Probar 1.000, 5.000 y 10.000 filas, con fuentes expandidas y transferencias autorizadas en curso. | Medir latencia por tecla y consumo de CPU; comprobar que no hay bloqueos ni regresiones de transferencia. |
| FIL-16 | Probar Windows con distintos escalados y tema claro/oscuro. | Controles legibles y accesibles. |

Compilar x64 con MSBuild, probar en un perfil aislado sin usar la cola de producción y registrar resultados antes de publicar. La creación de este plan no constituye ejecución de las pruebas. Se conserva la limitación previa de la versión base sobre el destino desaparecido durante la finalización.

## Criterio de aceptación

Compilación correcta, comprobación de todos los casos funcionales y mediciones comparativas frente a main. No publicar un ejecutable de producción basándose únicamente en una revisión de código.
