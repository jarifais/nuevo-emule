# Laboratorio A/B automático — eMule Community 0.72a

**Estado (26-11-2026):** planificador y analizador de telemetría JSONL desarrollados y probados con datos sintéticos. Aún no conectados al ejecutable de eMule. Diseño detallado y tareas en [issue #6](https://github.com/jarifais/nuevo-emule/issues/6).

## Propósito

Construir un único eMule portable de laboratorio con la búsqueda mejorada de descargas (PR #4), telemetría idéntica en todos los perfiles, y mejoras de red independientes con interruptores internos. El ordenador alternará las configuraciones según un calendario y registrará resultados automáticamente. **Ningún algoritmo aprobará o descartará cambios por sí solo**: la decisión técnica se hará tras revisar el informe.

Proteger las rutas reales Temp, Incoming, archivos .part y .part.met. Reutilizar las carpetas actuales sin duplicar descargas grandes; nunca ejecutar simultáneamente la versión instalada y la portable sobre el mismo estado. Preparar una copia pequeña de seguridad de configuración y metadatos críticos antes de utilizar el cliente experimental.

## Cuatro mejoras candidatas — hipótesis, no resultados probados

| ID | Área | Qué queremos optimizar | Estado |
|---|---|---|---|
| kad_01 | Kad | No consumir un turno de búsqueda si el archivo ya tiene una búsqueda activa | Código en PR #5, sin interruptor ni validación |
| ed2k_01 | Servidores eD2k | Evitar peticiones redundantes de fuentes sin aumentar carga sobre servidores | Por auditar y programar |
| udp_01 | UDP | Evitar reintentos/consultas innecesarios respetando el protocolo | Por auditar y programar |
| tcp_01 | TCP / clientes P2P | Evitar conexiones/reintentos que no aporten fuentes útiles | Por auditar y programar |

No aumentar indiscriminadamente conexiones ni frecuencias de consulta. Se auditarán dependencias entre módulos y posibles efectos negativos. Los cambios de interfaz y gestión de descargas que ya existían estarán presentes en **todos** los modos; no se mezclarán con experimentos de red.

## Diseño inicial: una campaña de seis días

El planificador crea **24 bloques de seis horas**. Se reservan **12 bloques para el funcionamiento original**, tres para cada una de las cuatro mejoras por separado. Se asignan tres bloques baseline a cada franja de seis horas del día; las mejoras se distribuyen con una semilla reproducible. Se excluyen inicialmente los primeros treinta minutos de cada bloque como estabilización.

Solo se activa una mejora por bloque, o ninguna en el caso de referencia. Esto evita atribuir falsamente a una mejora los efectos de otra. Las combinaciones de mejoras se analizarán en otra fase si hay resultados positivos individuales.

Conexiones persistentes, búsquedas ya iniciadas y colas heredadas pueden contaminar bloques posteriores. El controlador Windows deberá cambiar flags solo en puntos seguros, recibir **acuse del propio eMule** de que el perfil se ha aplicado, registrar incidencias y prolongar la estabilización o invalidar el bloque cuando sea necesario. Un cambio de fichero sin confirmación del cliente no cuenta.

**Seis días son una prueba inicial, no una duración estadística garantizada.** Las descargas y los peers cambian, y tres bloques por mejora proporcionan, en el mejor caso, evidencia preliminar. Si el número de fuentes o las medidas son insuficientes, la conclusión será inconcluyente y se recomendará ampliar pruebas.

## Métricas

Las mediciones por minuto propuestas son:

- Búsquedas Kad iniciadas efectivamente y turnos desperdiciados por búsquedas ya activas.
- Fuentes útiles Kad nuevas **validadas y aceptadas**, distinguidas de duplicados y de fuentes procedentes de eD2k.
- Tráfico real de descarga de piezas, separado de sobrecarga de Kad/UDP y peticiones de servidores.
- Reintentos UDP, intentos TCP, conexiones establecidas y fallidas.
- Fase siguiente obligatoria: tiempo monotónico hasta primera fuente útil incluyendo búsquedas sin resultados, CPU, memoria, estado de red Kad/eD2k, pérdida de conectividad, reinicios, errores y costes de instrumentación.

La telemetría no debe añadir escritura bloqueante al procesamiento de paquetes. Guardar datos por lotes, separados de Temp, con rotación y límites. No registrar direcciones IP, rutas, nombres de archivos ni identidades de terceros en claro.

## Herramientas implementadas de análisis local

El repositorio contiene scripts/lab_experiment.py con dos subcomandos:

1. plan: produce calendario determinista con inicio ISO-8601, offsets horarios y máscara de mejoras para cada bloque.
2. report: analiza **únicamente** muestras JSONL existentes y devuelve informe JSON por mejora. No abre eMule ni activa opciones.

Ejemplo de uso:

    python scripts/lab_experiment.py plan --start "2026-12-01T00:00:00+01:00" --seed 20261126 --out lab-plan.json
    python scripts/lab_experiment.py report --plan lab-plan.json --samples lab-samples.jsonl --out lab-report.json
    python -m unittest discover -s tests -v

Cada muestra exige ID de experimento, mismo ID de compilación, ID de bloque, UTC de comienzo del minuto, máscara realmente aplicada y confirmada por eMule, bandera de telemetría sana y nueve contadores iniciales definidos en el código. Se rechazan mediciones con flags discrepantes, ausencia de acuse, duplicados, intervalos equivocados o contadores inválidos. Para declarar un bloque completo hacen falta al menos **264 de sus 330 minutos** observables. Sin datos suficientes el informe es inconcluyente. La herramienta **no acepta automáticamente** mejoras.

## Integración y validación pendientes

1. Reconciliar PR #4 y PR #5 preservando las codificaciones de los archivos C++ heredados; mantener main protegido.
2. Instrumentar código C++ con contadores auditados, almacenamiento local de bajo coste y un modo de comparación A/A. Comprobar que los flags desactivados reproducen la conducta original.
3. Implementar flags independientes por módulo, acuse de su aplicación y transiciones seguras.
4. Añadir controlador automático del calendario, supervisión de errores y vuelta segura a referencia ante problemas.
5. Compilar Windows x64 y probar conectividad normal/filtrada, pocas/muchas descargas, fuentes escasas, reanudación y protección de archivos temporales.
6. Crear informe reproducible con anomalías, ventanas válidas, mediciones por capa y efectos/variabilidad. Revisión humana posterior para **mantener, descartar o declarar inconcluyente** cada mejora.

**Límite actual:** la prueba real todavía no puede iniciarse. Solo están creados el planificador, el analizador offline, la especificación y los tests con muestras artificiales. El cliente no dispone aún de telemetría A/B ni de cambios automáticos activables.
