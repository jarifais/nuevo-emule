# NUEVO EMULE — Hoja de ruta de 30 subetapas

**Aprobada para seguimiento:** 7 de noviembre de 2026. **Rama de trabajo:** `fix/partfile-safety-2026-11-04`. **PR de desarrollo:** [#1](https://github.com/jarifais/nuevo-emule/pull/1).

**Objetivo:** eMule más rápido, eficiente, robusto y seguro con más de 10.000 descargas, SSD USB y rutas de descarga configurables; sin romper compatibilidad eD2k/Kad ni formatos existentes.

**Estados:** ✅ implementada en código (NO significa validada en el equipo); ◐ parcial; ☐ pendiente. La aceptación de cada capa requiere CI de Windows x64, pruebas funcionales, medidas antes/después y ausencia de pérdida/corrupción de `.part`/`.part.met`. No se prometen mejoras porcentuales no medidas.

## Capa 1 — Interfaz y colas masivas

- [x] **1.1 Repintados innecesarios:** optimizar eventos de selección, actualización de filas visibles y recursos GDI. **Implementada; validar en Windows**.
- [x] **1.2 Categorías y búsquedas de filas:** evitar búsquedas repetitivas y conservar recuentos de filas. **Implementada; validar en Windows**.
- [x] **1.3 Inserción/eliminación de fuentes A4AF:** barrido seguro sin filas huérfanas ni punteros liberados prematuramente. **Implementada; validar en Windows**.
- [ ] **1.4 Selección masiva y navegación:** completar manejo de Mayús+flecha, Ctrl+clic, enfoque, teclado y desplazamiento; diagnosticar trabajo O(N) redundante. **Parcial**.
- [ ] **1.5 Diagnóstico y regresión con 10.000+:** medir bloqueos, excepciones, latencias, RAM, CPU, recuentos, fuentes expandidas, pestañas, reanudación y cierre. **Pendiente de ejecución real**.

## Capa 2 — Motor de descargas y CPU

- [x] **2.1 Planificador y solicitudes de fuentes:** reducir recorridos de peticiones, mantener límite TCP, orden y ciclo de transferencias de 100 ms. **Implementada; medir**.
- [ ] **2.2 Estadísticas globales:** reducir cálculos si las mediciones muestran un cuello de botella.
- [ ] **2.3 Recorridos de listas de fuentes:** eliminar scans redundantes sin alterar decisiones de selección.
- [ ] **2.4 Mantenimiento de descargas inactivas:** optimizaciones parciales del temporizador y reloj; verificar transición de estados y purgas.
- [ ] **2.5 Medición de CPU y latencia:** comparar perfil original, versión anterior y versión nueva bajo cargas equivalentes.

## Capa 3 — Disco y archivos temporales

- [x] **3.1 Consultas de espacio libre:** una consulta por carpeta `Temp` y pasada, sin caché entre pasadas. **Implementada; medir**.
- [ ] **3.2 Lecturas/escrituras de `.part`:** instrumentar accesos y latencias antes de cambiar.
- [ ] **3.3 Buffers y vaciados seguros:** preservar persistencia y recuperación; no demorar sin pruebas.
- [ ] **3.4 Movimiento y finalización:** rutas personalizadas, fallos, atomicidad y dispositivos desconectados.
- [ ] **3.5 Perfil de SSD USB:** medir I/O y latencias con 1, 1.000 y >10.000 descargas.

## Capa 4 — Integridad y recuperación

- [ ] **4.1 Guardado seguro de `.part.met`**.
- [ ] **4.2 Copias de seguridad y recuperación de `.bak`**.
- [ ] **4.3 Reinicio tras cierre inesperado**.
- [ ] **4.4 Desconexiones de unidades, rutas perdidas y acceso denegado**.
- [ ] **4.5 Verificación de integridad durante recuperación**.

## Capa 5 — Memoria y estructuras internas

- [ ] **5.1 Índices para búsquedas masivas**.
- [ ] **5.2 Asignaciones/copias innecesarias**.
- [ ] **5.3 Propiedad de objetos y ciclo de vida de punteros**.
- [ ] **5.4 Cachés con invalidación segura**.
- [ ] **5.5 Fugas, fragmentación y RAM con colas masivas**.

## Capa 6 — Conectividad eD2k/Kad

- [ ] **6.1 Descubrimiento y deduplicación de fuentes**.
- [ ] **6.2 Conexiones simultáneas y límites**.
- [ ] **6.3 Reintentos, tiempos de espera y congestión**.
- [ ] **6.4 Búsquedas Kad/servidores, carga de red**.
- [ ] **6.5 Validación de mensajes, límites y entradas malformadas**.

## Reglas de ejecución

1. **Una intervención verificable por vez**, con pruebas que protejan invariantes y documentación del cambio. Se pueden agrupar correcciones estrechamente relacionadas si su impacto está delimitado.
2. **CI de Release x64 obligatorio** en el commit que se distribuya. El ZIP experimental no equivale a una prueba con usuarios.
3. **Aislar cambios en PR borrador**, no fusionar a `main` antes de cumplir los criterios de aceptación.
4. **No ejecutar dos variantes sobre el mismo `Temp`**; preservar rutas `Temp`, `Incoming`, `Category.ini`, `preferences.ini` y ficheros `.part.met`.
5. **Mediciones reproducibles:** versión, tamaño de cola, categorías, red, fuentes, CPU, RAM, SSD/USB, latencia de selección/categoría y registros de fallos; distinguir optimizaciones algorítmicas de ganancias medidas.
6. **La subetapa 1.5 no puede cerrarse desde CI**: exige ejecución en Windows con cola masiva y evidencia de que el bloqueo original no se reproduce.

## Referencias

- [Detalle original y aceptación de la capa 1](PLAN_MEJORAS_POR_CAPAS_2026-11-06.md).
- [Capa 2.1 — planificador](CAPA2_PLANIFICADOR_2026-11-07.md).
- [Capa 3.1 — disco](CAPA3_DISCO_2026-11-07.md).
- [Portable con carpetas compartidas](PORTABLE_INDEPENDIENTE_2026-11-06.md).

**Nota de mantenimiento:** las casillas `[x]` indican implementación, **no validación funcional**. Actualizar esta hoja al incorporar cambios o registrar una prueba reproducible.
