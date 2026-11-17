# Optimización de Kad — Fase 1: planificación de búsquedas de fuentes

Base: eMule Community 0.72a (repositorio `jarifais/nuevo-emule`).

## Hallazgos comprobados en el código

- `srchybrid/DownloadQueue.cpp`: `CDownloadQueue::Process()` procesa las descargas por prioridad cada ~100 ms.
- `srchybrid/PartFile.cpp`: cada archivo puede iniciar una búsqueda Kad cuando tiene menos fuentes que su límite UDP, Kad está conectado, el temporizador del archivo lo permite y no supera el límite de búsquedas simultáneas.
- Hay un intervalo compartido entre búsquedas y una espera progresiva por archivo; NO deben eliminarse indiscriminadamente.
- Antes de esta modificación, un archivo con `GetKadFileSearchID() != 0` podía superar los controles globales, consumir el turno de consulta y finalmente no iniciar ninguna búsqueda nueva.
- `srchybrid/DownloadQueue.cpp::KademliaSearchFile()` ya realiza controles de límites de fuentes, IP filtradas, auto-conexiones y tipos de fuente compatibles.
- `srchybrid/kademlia/kademlia/SearchManager.cpp` elimina o detiene búsquedas según sus límites; `Search.cpp` conserva la estrategia de búsqueda por nodos próximos.

## Cambio de Fase 1

En `CPartFile::Process()`, comprobar `!GetKadFileSearchID()` **antes** de consumir el turno global de búsqueda. Elimina un intento inútil cuando ese archivo ya está buscando fuentes y permite que el siguiente archivo elegible aproveche el turno.

Se mantienen sin cambios la cadencia global, el máximo de búsquedas en paralelo, los tiempos de reconsulta, las protecciones de fuentes y la lógica de transferencia. Esta corrección puede mejorar la distribución de búsquedas en colas con múltiples descargas; **no implica una ganancia porcentual de velocidad confirmada**.

## Validación pendiente (Windows)

1. Compilar x64 con el mismo procedimiento que la rama estable. Verificar errores y advertencias nuevos.
2. Con Kad conectado y puertos TCP/UDP correctamente accesibles, añadir varias descargas con pocas fuentes. Confirmar en el registro/ventana de búsquedas que nunca se asigna un nuevo turno a un archivo con búsqueda propia aún activa.
3. Comparar la versión base y esta rama con archivos de igual hash, mismas opciones y condiciones lo más equivalentes posible. Medir tiempo hasta primera fuente útil, fuentes únicas aceptadas por minuto, número de búsquedas iniciadas y velocidad de descarga efectiva.
4. Repetir con 1, 10, 100 y, si los recursos lo permiten, 1000 archivos; incluir archivos con fuentes abundantes, pausados, reiniciados y sin fuentes.
5. Verificar que los límites de consultas simultáneas y su cadencia no cambian; comparar carga de CPU, paquetes UDP y consumo de memoria. Confirmar que no hay cambios en rutas `Temp`, categorías ni ficheros `.part/.met`.
6. Probar Kad con UDP bloqueado/firewalled y con Kad desconectado: el cambio no debe provocar ráfagas de tráfico, cuelgues ni alterar la descarga vía eD2k.
7. Confirmar que no hay regresiones de selección, pausa/reanudación o búsqueda de fuentes tras reiniciar eMule.

## Siguientes fases propuestas

- **Fase 2 — diagnóstico:** añadir contadores de búsquedas Kad (iniciadas/completadas), tiempo hasta primera fuente, fuentes aceptadas/rechazadas, estado de firewall UDP y carga de consultas; instrumentación activable, de coste bajo.
- **Fase 3 — reparto:** evaluar, mediante datos de Fase 2, la equidad entre descargas sin fuentes y con prioridad diferente; evitar el hambre de los archivos situados al final de la cola.
- **Fase 4 — resiliencia:** revisar caducidad de contactos, resultados tardíos, nodos sin respuesta y comportamiento ante NAT o pérdidas UDP, sin romper compatibilidad con Kad.
- **Fase 5 — rendimiento:** ajustar solo parámetros con mejora reproducible y sin elevar la carga de la red pública; comparar velocidad real y cantidad de fuentes útiles, no solo respuestas Kad.

## Criterio de aceptación

No fusionar con `main` ni generar binarios de distribución hasta que haya compilación Windows y pruebas funcionales satisfactorias. Una reducción de turnos desperdiciados es la hipótesis técnica; el efecto sobre velocidad todavía debe medirse.
