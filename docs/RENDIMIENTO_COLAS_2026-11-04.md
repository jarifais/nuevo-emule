# Auditoría de rendimiento y robustez — 4 de noviembre de 2026

Estado: cambios implementados en rama de pruebas. **Sin validación funcional en un PC Windows ni resultados de rendimiento medidos**. No fusionar a `main` hasta verificar compilación y regresiones.

## Cambios implementados

1. **Contador de archivos visibles** — `srchybrid/DownloadListCtrl.cpp/.h`.
   - `AddFile` actualiza el contador de la pestaña visible en lugar de ejecutar `GetFilesCountInCurCat` y recorrer todas las descargas al añadir cada una.
   - `ShowFile` y `HideFile` mantienen el contador cuando cambia la visibilidad de un archivo.
   - `ShowFilesCount` conserva un recuento completo para sincronización al cambiar de categoría.
   - Comprobar especialmente categorías filtradas, cambios de estado, arranque con miles de archivos y eliminación masiva.

2. **Ordenación por prioridad** — `srchybrid/DownloadQueue.cpp/.h`.
   - Sustituye `HeapSort`, que utilizaba `FindIndex` repetidamente sobre una lista enlazada, por una copia de punteros a `std::vector`, `std::stable_sort` y escritura sobre las mismas posiciones de la lista.
   - Conserva la precedencia de prioridad de categoría y prioridad del archivo. A igual prioridad entre categorías distintas, introduce un criterio de desempate determinista por índice de categoría para satisfacer el contrato de orden estricto del algoritmo de biblioteca. Los nombres vacíos también se ordenan consistentemente en categorías alfabéticas.
   - Verificar manualmente la precedencia con archivos de distintas categorías, prioridades y nombres; este desempate puede modificar la disposición anterior de archivos empatados entre categorías.

3. **Mantenimiento de archivos inactivos** — `srchybrid/DownloadQueue.cpp`.
   - Se mantiene la llamada a `CPartFile::Process` en el ciclo original de 100 ms para archivos activos (sin reducir la cadencia de control de transferencias).
   - Se limita `StopPausedFile` a aproximadamente una ejecución por segundo para cada archivo no activo: su trabajo habitual es la purga de fuentes tras una hora o la eliminación diferida.
   - Se calcula `GetStatus` una vez por elemento y ciclo, en lugar de repetirlo.
   - **Limitación:** la cola completa **todavía se recorre cada 100 ms** para mantener las estadísticas globales; esta mejora reduce el trabajo pesado de los inactivos, pero no elimina ese recorrido. No intentar reescribir el planificador sin una prueba de equivalencia y mediciones.

## Regresiones obligatorias

- Arranque con 0, 1, 1.000, 10.000 y más descargas: comprobar cifra de archivos, pestañas y filtros.
- Añadir, ocultar, cambiar categoría y eliminar archivos: el contador debe coincidir siempre con el recuento real en cada categoría.
- Seleccionar un bloque de miles de descargas con Mayús y flecha: no debe bloquearse el diálogo ni perderse la selección.
- Varias categorías y prioridades, incluida la ordenación alfabética y nombres iguales/vacíos.
- Descargas activas: comparar periodicidad de progreso, velocidad, fuentes, límites y activación con el original.
- Archivos pausados o con error: purga de fuentes tras una hora y eliminación diferida correcta.
- Comprobar `.part` y `.part.met` tras cierres normales, fallos simulados y recuperación.
- Verificar Release x64 en GitHub Actions y ejecutar una prueba de rendimiento real antes de afirmar mejora de velocidad o memoria.

## Próximas investigaciones (no implementadas aquí)

- Eliminar el barrido completo por ciclo mediante una lista activa mantenida con eventos o invalidación segura y estadísticas incrementales. Riesgo: omitir transiciones a activo o conservar punteros a archivos borrados. Requiere pruebas reproducibles.
- Evitar búsquedas repetidas `FindItem` en la lista visual de descargas y su coste con fuentes expandidas.
- Reducir consultas repetidas de espacio libre si varias descargas comparten la misma unidad; confirmar primero efectos de caché y eventos de disco.
- Instrumentar latencia de GUI, lecturas/escrituras, uso de memoria, cola de I/O y recuperación de `.part.met`.

**No se modifican protocolos eD2k/Kad, límites de red, formato de archivos parciales ni política general de carpetas.**

## Sesión siguiente — jueves 5 de noviembre de 2026

**Instrucción del usuario:** continuar por orden de mayor a menor mejora potencial. Empezar por **prioridad 1: interfaz y selección masiva**. No pasar a otra área sin completar primero la revisión de esa prioridad. No depender de un PC local disponible para avanzar; no hacer seguimiento de GitHub Actions por iniciativa propia.

Orden de trabajo acordado (impacto estimado, todavía no medido):
1. **Interfaz y selección masiva:** inspeccionar `CDownloadListCtrl` y otras vistas; eliminar `FindItem` repetidos, redibujados innecesarios y operaciones que escalen mal con más de 10.000 descargas y fuentes expandidas. La primera mitigación de `OnListModified` ya está en esta rama; no repetirla. Proteger selección, foco y ordenación. **Primera tarea de mañana.**
2. **CPU y planificador:** investigar el barrido de todas las descargas cada 100 ms, sin cambiar el procesamiento de descargas activas ni saltar eventos. Ya se redujo a 1 Hz el mantenimiento de archivos inactivos; queda pendiente el barrido de estadísticas.
3. **Acceso a disco y archivos temporales:** analizar operaciones y consultas redundantes, sin alterar integridad ni durabilidad.
4. **Robustez y recuperación:** mejorar gestión de fallos y seguridad de `.part` y `.part.met`.
5. **Memoria:** revisar asignaciones y estructuras de archivos y fuentes a gran escala.
6. **Búsqueda interna por identificador:** evaluar índices para evitar búsquedas lineales repetidas.

Requisitos de trabajo: cambios acotados en la rama `fix/partfile-safety-2026-11-04`, mantener `main` intacta; no romper funciones que ya trabajan correctamente; diferenciar hallazgos confirmados por lectura de código de mejoras que requieren benchmark; conservar descargas y formatos `.part/.part.met`. El usuario ha indicado dejar esta sesión cerrada y **reanudar mañana**, sin trabajo adicional ni promesas de trabajo asíncrono.

