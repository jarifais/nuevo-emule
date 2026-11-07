# Capa 1 — validación GUI reproducible con más de 10.000 descargas

**Estado:** procedimiento listo; **sin resultado funcional todavía**. Las pruebas estáticas de CI y la compilación Windows no demuestran la ausencia de bloqueos ni la aceleración de la interfaz.

## Requisitos y seguridad

- Windows x64; anotar versión de eMule original, commit del portable y modelo/puerto del SSD USB.
- Cola real de referencia (>10.000 archivos), número de categorías, filas visibles, fuentes expandidas y rutas `Temp`/`Incoming`.
- **No abrir dos clientes contra la misma cola**. Cerrar el instalado antes de abrir el portable y viceversa. La versión nueva puede escribir `.part`/`.part.met` originales.
- Si hay espacio para ello, conservar por separado copia de los **metadatos** `.part.met` y `.part.met.bak`, no es necesario duplicar los `.part` gigantes. No desconectar un SSD mientras una aplicación escribe.
- Primera ronda desconectado de Internet para aislar la interfaz del tráfico de red y del proceso de descargas.

## Escenarios mínimos (original → portable)

| Escenario | Procedimiento | Evidencia |
|---|---|---|
| 0 / 1 / 1.000 / 10.000+ descargas | Al iniciar, contar filas y categorías; medir tiempo hasta que la lista queda utilizable | Tiempo de carga, RAM, CPU, recuentos |
| Mayús + flecha | Seleccionar bloques crecientes y mantener la combinación 30–60 s | Si la selección responde, retrasos, bloqueos |
| Ctrl + A, Ctrl + clic | Selección completa, cambio de foco, deselección | Correcto estado de selección y foco |
| Categorías | Cambiar entre todas las pestañas, incluidas vacías; repetir 20 veces | Recuentos, latencia, elementos sin duplicar |
| Fuentes | Expandir, contraer y ordenar diferentes descargas, con fuentes A4AF compartidas | No aparecen filas huérfanas ni crash |
| Borrado visual | Ocultar archivos completados; realizar la prueba sobre archivos completados de prueba (no activos) | Recuento correcto, sin punteros colgantes |
| Renombrar, pausar, reanudar | En descargas de prueba, modificar estados con fuentes expandidas | Estado coherente después de cerrar/abrir |
| Destinos personalizados | Confirmar rutas `Descargar en...`, `Temp` e `Incoming` antes y después de reiniciar | Rutas persistentes, sin redirigir a otras carpetas |
| Cierre / reapertura | Cerrar normalmente, abrir de nuevo la misma variante | Cola, categorías y rutas intactas |
| Red activa | Conectar y descargar brevemente solo después de las anteriores | Sin regresiones de fuentes ni transferencia |

No declarar la subetapa 1.5 terminada hasta que se hayan superado esos escenarios con el usuario y se conserven resultados comparables.

## Muestreo sin instalar programas

Usar `scripts/measure_gui_layer1.ps1` con **PowerShell de Windows**. Ejemplos desde la raíz del repositorio:

```powershell
# Versión original, solo ella abierta; CPU/RAM durante inactividad.
.\scripts\measure_gui_layer1.ps1 -ProcessName emule -Variant original -Scenario idle -Seconds 60 -OutputPath .\results\original-idle.csv

# Portable, con la misma cola y el original cerrado.
.\scripts\measure_gui_layer1.ps1 -ProcessName nuevo-emule -Variant portable -Scenario idle -Seconds 60 -OutputPath .\results\portable-idle.csv

# Mientras se recogen muestras, mantener Mayús+flecha sobre la lista.
.\scripts\measure_gui_layer1.ps1 -ProcessName nuevo-emule -Variant portable -Scenario shift-arrow -Seconds 60 -OutputPath .\results\portable-selection.csv

# Repetir también con -Scenario categories y -Scenario sources, así como
# con la versión original en ejecuciones separadas.
```

El CSV almacena CPU normalizada por núcleos, memoria privada, working set, hilos, handles y estado básico de respuesta de la ventana. La métrica `GuiResponding` no sustituye a un informe de cuelgue ni identifica por sí misma el origen del bloqueo.

**Latencia de interfaz:** anotar manualmente el intervalo desde pulsar la tecla/cambiar categoría hasta que finaliza el repintado. Para tiempos exactos sería necesaria instrumentación específica o una herramienta externa de medición. No inferir latencia de las muestras de CPU.

## Si ocurre un fallo

1. No abrir la segunda versión mientras la primera siga ejecutándose.
2. Guardar los CSV y la hora exacta; copiar los eventos asociados al ejecutable en **Visor de eventos → Registros de Windows → Aplicación**, especialmente errores de aplicación y bloqueos de ventana.
3. Anotar categoría, cantidad de seleccionados, fuentes expandidas, número de filas, estado de la conexión y pasos precisos para reproducir.
4. Si la aplicación no responde, consultar primero el consumo de RAM, CPU y disco. Evitar finalizar la tarea mientras se estén guardando metadatos, salvo que esté irremediablemente bloqueada.
5. No afirmar que el problema está resuelto sin al menos una ejecución exitosa de los escenarios con 10.000+ descargas.

## Criterio de aceptación de 1.5

- Sin fallos o bloqueos de ventana durante la sesión de pruebas descrita.
- Recuentos, selecciones, foco, categorías y fuentes A4AF coherentes.
- Persistencia de `preferences.ini`, `Category.ini`, `.part` y `.part.met` verificada tras cierre y reapertura.
- CSV original y portable con configuración comparable; registrar si la ganancia es estadísticamente observable o no.
- Un caso reproducible/registro si se detecta de nuevo el bloqueo; analizar la causa antes de marcar resuelto.

**Faltante externo:** la ejecución en un equipo Windows con la cola masiva y el SSD USB reales; no puede simularse ni certificarse mediante los contratos de CI.
