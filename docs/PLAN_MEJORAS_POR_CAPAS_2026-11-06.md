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

- **Cambio de categoría — commit 758a04c:** sustituye las búsquedas `FindItem` repetidas de `ShowFile`/`HideFile` por un barrido de filas visibles y la reinserción exclusiva de archivos nuevos. Se reduce el número de búsquedas; **no es correcto afirmar complejidad global O(N+V)** porque el control base mantiene índices en una lista enlazada y cada `DeleteItem` puede seguir costando O(V).
- **Contracción de fuentes — commits 08788b8 y 7bc1df5:** la primera optimización asumía fuentes contiguas. Se ha sustituido por un barrido completo y seguro que no deja fuentes huérfanas si el orden cambia; ahora cada lectura de fila usa la consulta directa de Windows.
- **Lectura de filas — commits 03e3941 y 215b9cc:** `CDownloadListCtrl::GetItemData` consulta los datos de fila de Windows directamente, sin `m_Params.FindIndex`. En compilaciones Debug compara el resultado con el comportamiento original mediante `ASSERT`.
- **Actualizaciones ocultas — commit 68e157d:** `UpdateItem` evita búsquedas y repintados de archivos fuera de la categoría y de fuentes contraídas.
- **Eliminación con fuentes — commit 90517d2:** `RemoveFile` retira en dos fases filas y entradas del mapa, evitando búsquedas visuales repetidas y liberando memoria solo después de borrar las filas.
- **Desplazamiento y recursos gráficos — commit fc685dc:** `CMuleListCtrl::OnLvnEndScrollList` ya no deja sin liberar el contexto de dibujo obtenido al llegar al final; utiliza `CClientDC` con liberación automática, comprueba el resultado de `GetItemRect` y evita usar el índice `-1` en listas vacías. Es un defecto confirmado por lectura del código, pero **no se puede asegurar que fuera el origen del bloqueo concreto del usuario**.
- **Contador de inserción — commit 4d4ebb3:** `AddFile` incrementa el número de filas visibles solamente cuando el control Windows acepta la nueva fila. Evita un desajuste si `InsertItem` falla; no cambia la ubicación de las descargas.
- **Eliminación de fuentes — commit 87090bd:** `RemoveSource` desconecta del mapa las entradas del cliente, retira las filas visibles en un barrido inverso y solo entonces libera los objetos. Conserva el filtro por archivo propietario y la eliminación global de fuentes A4AF; reduce búsquedas visuales repetidas.
- **Pruebas estáticas — nueve contratos:** `scripts/test_gui_layer1_contract.py` comprueba las invariantes básicas de las correcciones, incluida la liberación del contexto de dibujo, el recuento ante inserciones fallidas y el orden seguro de eliminación de fuentes. Deben mantenerse complementadas con MSBuild y pruebas de interfaz en Windows.

**Estado de validación:** los cambios están implementados en la rama. La compilación del último commit y las pruebas funcionales con dos instancias, 10.000 descargas y selección prolongada aún deben verificarse. Ninguna mejora porcentual está medida. El origen del bloqueo original todavía no se ha diagnosticado con un registro de excepción.
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

## Pruebas adicionales de regresión para eliminación de fuentes

- Mantener un cliente A4AF compartido en dos descargas expandidas; retirar solo una asociación (`owner != NULL`) y confirmar que la otra persiste.
- Retirar el cliente por completo (`owner == NULL`), con fuentes visibles y contraídas; no deben quedar filas huérfanas ni producirse fallos en el repintado.
- Repetir las operaciones mientras otra descarga permanece activa y después de ordenar/cambiar de categoría, verificando que la transferencia no se interrumpe.
- Medir las retiradas de fuentes con 0, 1, 1.000 y más de 10.000 descargas; la ausencia de `FindItem` repetidos es una mejora de algoritmo, no una cifra de aceleración medida.
- La validación funcional en Windows del último commit sigue siendo obligatoria antes de fusionar a `main`.
