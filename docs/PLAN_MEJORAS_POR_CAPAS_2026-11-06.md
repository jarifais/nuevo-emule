# Plan de modernización por capas — 6/11/2026

**Objetivo:** mejorar rendimiento, eficiencia, robustez y seguridad de nuevo-emule, manteniendo compatibilidad eD2k/Kad y evitando regresiones. La versión portable ya permite probarla aislada del eMule instalado.

**Caso real de referencia:** más de 10.000 descargas, selección prolongada con Mayús+flecha, SSD conectado por USB; hubo un bloqueo/crash no reproducido ni diagnosticado definitivamente. Las mejoras estimadas todavía no equivalen a benchmarks.

## Capas por prioridad (estimación, no medición)

1. **Interfaz, selección y representación de colas masivas:** optimizar eventos de selección, repintados, cambio de pestañas, expansión/contracción de fuentes y búsquedas de filas. Verificar foco, selección, ordenación, categorías y cierres de ventana.
2. **Planificador y CPU:** investigar barrido de descargas cada 100 ms, temporizadores y estadísticas; mantener los ciclos de transferencias activas y no saltar cambios de estado.
3. **E/S de disco y archivos temporales:** reducir comprobaciones de espacio y operaciones repetidas; medir latencia y cola de I/O antes de modificar durabilidad o buffers.
4. **Integridad y recuperación:** proteger .part y .part.met, estados de finalización, fallos de disco/rutas ausentes y reinicio tras interrupciones.
5. **Memoria, índices y estructuras:** evaluar cachés de filas, índices por hash y vida útil segura de fuentes y descargas, evitando índices obsoletos o uso tras liberar.
6. **Conectividad eD2k/Kad:** revisar fuentes, intercambios, reintentos y compatibilidad, conservando protocolos y comportamiento de red.

**Seguridad transversal:** sin reutilizar datos del eMule instalado; validar rutas y entradas remotas; no habilitar conexiones inseguras ni introducir cambios incompatibles; conservar licencias y crédito de terceros; aislar cambios en rama de pruebas.

## Capa 1: avances implementados

- **Cambio de categoría — commit 758a04c:** sustituye un bucle que realizaba `FindItem` en `ShowFile`/`HideFile` por cada descarga por un barrido de filas visibles, una colección temporal de filas conservadas y reinserción exclusiva de archivos nuevos. Reduce complejidad teórica de aproximada O(N·V) a O(N+V), con N archivos y V filas visibles. No se ha medido tiempo de respuesta real.
- **Contracción de fuentes — commit 08788b8:** localiza una vez el archivo propietario y elimina sus fuentes contiguas, sin examinar todas las filas de la cola. Conserva la exploración completa como respaldo cuando no aparece la fila propietaria.
- Se mantienen las correcciones previas del redibujado de selección y del contador visible; no duplicarlas.

## Criterios obligatorios de aceptación de la capa 1

- Compilar Release Windows x64 para el **último** commit, no uno anterior.
- Ejecutar una prueba en el cliente portable independiente, sin tocar colas reales ni archivos `.part` de la instalación original.
- Probar cambio entre todas las pestañas de categoría con **0, 1, 1.000 y más de 10.000** descargas; los archivos visibles y recuentos deben coincidir, sin duplicados.
- Probar selección Mayús+flecha sostenida, Ctrl+clic, selección múltiple, ordenación, ocultación y expansión de fuentes; no perder foco ni cerrar el proceso.
- Probar renombrar, detener, pausar, reanudar, eliminar y finalizar descargas mientras hay fuentes expandidas.
- Comprobar que `Descargar en...` mantiene sus carpetas de finalización y la descarga sigue en la carpeta Temp de la versión portable.
- Medir latencia de cambio de pestaña, CPU, memoria y cantidad de filas, comparar versión original y optimizada con las mismas condiciones.
- Reabrir la versión portable y confirmar persistencia de descargas de prueba y categorías.
- Revisar registros de fallos; **sin mensaje de excepción reproducido no puede darse por diagnosticado el bloqueo original**.

## Restricciones

- No fusionar a `main` sin validación.
- No proclamar aceleraciones cuantificadas sin benchmark ni afirmar seguridad total por ausencia de errores de compilación.
- Cambios pequeños y reversibles; no modificar protocolos ni formatos persistentes en la capa 1.
- La capa 1 continúa abierta: quedan por revisar las búsquedas `FindItem` en `UpdateItem`, `RemoveFile` y `ShowFile/HideFile`, la respuesta a selección masiva y los repintados de los controles.
