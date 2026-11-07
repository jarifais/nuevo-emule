# Capa 2.1 — planificador y CPU (7 de noviembre de 2026)

## Alcance de este cambio

**Objetivo:** reducir CPU y recorridos repetidos sobre listas grandes sin alterar el protocolo eD2k/Kad, el límite de 15 solicitudes por paquete TCP, el tiempo de proceso de las descargas activas o los formatos persistidos.

1. **Mantenimiento inactivo:** `CDownloadQueue::Process()` conserva el ciclo activo de **100 ms**; las descargas pausadas, con error o completadas siguen revisándose aproximadamente cada segundo, como en la versión previa. En ese barrido, `time(NULL)` se consulta **una sola vez**, y la marca temporal se pasa a `CPartFile::StopPausedFile(time_t)`. Las llamadas externas a `StopPausedFile()` conservan la consulta propia del reloj mediante el parámetro opcional. La purga de fuentes cada hora y `m_bDelayDelete` siguen presentes.

2. **Solicitudes al servidor:** `CDownloadQueue::ProcessLocalRequests()` antes hacía una búsqueda completa para encontrar cada una de hasta 15 solicitudes. Ahora lee la cola una vez, descarta las solicitudes de archivos inactivos, calcula la misma puntuación `m_LastSearchTime + prioridad`, ordena establemente las posiciones y prepara los paquetes en orden. Recomprueba el estado antes de incluir cada elemento; los archivos grandes no admitidos por el servidor siguen descartándose sin consumir uno de los 15 huecos. Se mantiene la exclusión del valor centinela `_UI32_MAX`, que no resultaba seleccionable en el código anterior. Si todos los candidatos tienen ese valor, la versión nueva termina la selección en vez de quedarse en un bucle sin progreso.

3. **Pruebas y compilación:** `scripts/test_scheduler_layer2_contract.py` comprueba contratos del código y compara la selección de un modelo del planificador previo con el modelo nuevo para tamaños de 0 a 10.000 entradas, prioridades, empates, archivos descartados y solicitudes inválidas. La compilación MSBuild Release x64 y las comprobaciones de CI son obligatorias.

## Complejidad, sin cifras inventadas

- **Antes:** hasta **15 barridos completos** sobre la lista de peticiones en una emisión, aparte de las solicitudes descartadas.
- **Después:** **un barrido para examinar estados** y una ordenación estable `O(Q log Q)` para escoger el mismo orden. El beneficio principal consiste en reducir las repetidas consultas de estado y recorridos sobre los nodos de una lista enlazada; no se presupone una aceleración neta universal porque ordenar y reservar memoria también tienen coste.
- **Mantenimiento de inactivos:** consulta del reloj por lote en lugar de por archivo.
- **Sin modificar:** la agregación global de estadísticas y el procesamiento de archivos activos cada 100 ms. Requerirán instrumentación real antes de cambiar su frecuencia, para evitar regresiones de interfaz o transferencias.

## Pruebas funcionales obligatorias en Windows

1. **Sin conexión:** comparar CPU, RAM y fluidez del original y la nueva versión con 0, 1, 1.000 y >10.000 descargas. Mantener constantes cola, categorías, estado de red y número de fuentes.
2. **En conexión eD2k:** confirmar el orden de prioridad de solicitudes de fuentes, máximo 15 por trama y separación temporal entre tramas; incluir varios archivos con igual prioridad, pausados y archivos >4 GiB con un servidor sin soporte de archivos grandes.
3. **Transferencia activa:** confirmar que la velocidad, las limitaciones de descarga y los cambios de estado no presentan regresiones.
4. **Mantenimiento:** pausar/reanudar y producir estados de error; comprobar purga de fuentes pasadas 1 hora y borrado aplazado, también al recuperar una unidad USB desconectada.
5. **Regresión:** persistencia de `.part`/`.part.met`, categorías, rutas compartidas del portable y exclusión de instancias. Nunca usar simultáneamente ambos procesos sobre el mismo `Temp`.

## Estado

Cambio aislado en la rama `fix/partfile-safety-2026-11-04`. **No fusionar a `main`** sin resultados de compilación y pruebas funcionales. La ejecución automática de pruebas de contrato no demuestra ganancias de rendimiento ni elimina la necesidad de medir en el equipo real.
