# Telemetria Kad - fase 2 (instrumentacion, NO experimento A/B)

## Alcance implementado

Rama derivada de `feature/lab-telemetry-stage1` de eMule Community 0.72a.
Solo instrumenta eventos ya existentes. No cambia cadencias, limites ni algoritmos de Kad, eD2k, TCP o UDP.

Las muestras siguen registrandose aproximadamente cada 60 segundos en `lab-telemetry-v1.jsonl` (con rotacion). **El nombre del fichero no indica el formato**: los nuevos registros son `schema_version: 2`; el analizador admite registros antiguos de formato 1 y los separa por version y sesion.

## Diccionario de los seis nuevos contadores acumulativos

| Campo JSON | Momento exacto de incremento |
|---|---|
| `kad_slots_consumed_cumulative` | Despues de ejecutar `SetLastKademliaFileRequest()` en `CPartFile::Process()`: se consumio un turno global de busqueda. |
| `kad_slots_wasted_active_search_cumulative` | Se consumio ese turno, pero el archivo ya tenia un `GetKadFileSearchID()` activo; no se lanzo nueva busqueda. |
| `kad_lookups_started_cumulative` | `PrepareLookup()` devolvio un objeto de busqueda. **No prueba que haya respuestas ni fuentes.** |
| `kad_lookups_prepare_failed_cumulative` | `PrepareLookup()` devolvio null tras consumir el turno. |
| `kad_source_candidates_cumulative` | `KademliaSearchFile()` preparo un candidato de origen Kad antes de intentar incorporarlo. |
| `kad_new_sources_accepted_cumulative` | `CheckAndAddSource()` devolvio true para un candidato de Kad, que se incorporo a la lista de fuentes del archivo. **No prueba conectividad ni bytes descargados.** |

Regla de contabilidad ideal, considerando incrementos atomicos que pueden observarse en instantes ligeramente distintos:
`turnos_consumidos = turnos_desperdiciados + busquedas_iniciadas + fallos_preparacion`.
Una discrepancia en los registros es una advertencia de integridad, **no evidencia de aceleracion**.

Los incrementos usan primitivas `Interlocked` y las muestras leen los acumulados sin reiniciarlos. Asi, un fallo de escritura no borra los conteos. El limite del contador es de 32 bits por proceso: cualquier retroceso se rechaza para el intervalo, y un posible desbordamiento se trata conservadoramente como no valido. Los campos no incluyen IP, hashes, nombres de descargas, rutas ni IDs de pares.

## Validacion y analisis

- Los intervalos con contadores decrecientes, marcas de tiempo no crecientes o separacion superior a tres minutos se excluyen; los huecos nunca se rellenan inventando eventos.
- Versiones 1 y 2 de un mismo `session_id` se procesan como sesiones distintas.
- El informe ofrece tasa de fuentes aceptadas por minuto y fraccion de turnos perdidos; ambas **son diagnosticos descriptivos**, no una estimacion causal de la mejora Kad.
- La informacion sobre fuentes aceptadas no equivale a fuentes conectables, fuentes que enviaron datos o tiempo hasta la primera fuente util.
- Las validaciones unitarias de Python y los controles estaticos del codigo C++ **no sustituyen** compilar ni ejecutar eMule en Windows.

Para generar el informe:

```shell
python scripts/lab_telemetry_report.py <ruta-logs>/lab-telemetry-v1.previous.jsonl <ruta-logs>/lab-telemetry-v1.jsonl --out informe-kad-fase2.json
```

## Criterios pendientes para un laboratorio fiable

1. Compilar Windows x64, revisar warning/errores y verificar el JSON real, escrituras, rotacion y cierre. Probar contadores con descargas sin fuentes y multiples descargas.
2. Medir impacto sobre CPU, E/S, latencia del hilo de la cola, estabilidad de Kad y tamanos de registros. Migrar el escritor sincrono a cola acotada no bloqueante si afecta la aplicacion.
3. Incorporar bandera reversible `KAD-01` y confirmacion del estado realmente aplicado; la rama actual registra solo el **algoritmo original**.
4. Instrumentar inicio/fin de cada busqueda y aceptacion/conexion/transferencia de fuentes para poder evaluar latencia real hasta fuente util.
5. Ensayar A/A (mismo comportamiento en ambos bloques) y despues A/B alternado con periodos de estabilizacion, controles de firewall y estados eD2k/Kad, y tamaño de muestra suficiente.
6. Preservar las rutas existentes de `Temp/.part`, sin duplicarlas ni ejecutar dos instancias a la vez. No fusionar en main ni distribuir binarios sin QA.

**Decision final:** conservar, descartar o inconcluso despues de un informe reproducible y revision humana. No aprobar mejoras por umbrales automaticos no validados.
