# Telemetria de laboratorio, fase 1 (solo referencia)

Esta rama incorpora una **sonda real en** `CDownloadQueue::Process()` de eMule Community 0.72a. Es una etapa de instrumentacion; no hay todavia un ensayo A/B valido ni mejoras de Kad activadas.

## Funcionamiento
- Una muestra cada 60 segundos en el hilo habitual de la cola de descargas.
- Lee contadores de la cola y `CStatistics`, sin cambiar las peticiones a Kad, servidores o peers.
- Registra hora UTC, sesion, reloj monotono de 32 bits, velocidad estimada B/s, archivos en cola/activos/descargando, fuentes enumeradas (sumadas por archivo), clientes transfiriendo y contadores **acumulativos** de bytes recibidos y sobrecarga de Kad/servidor.
- Guarda JSONL en el directorio de logs configurado por eMule: `lab-telemetry-v1.jsonl`; al alcanzar 8 MiB rota a `lab-telemetry-v1.previous.jsonl`. Maximo nominal: 16 MiB. Nunca guarda nombres, hashes, IP, puertos ni rutas de descargas.
- Si el directorio no es escribible, no detiene la descarga; solo emite aviso en OutputDebugString. La telemetria puede tener lagunas: **no** se marca como sana sin verificar su salida.
- El volcado sincronico una vez por minuto es pequeno, pero aun debe evaluarse su coste y sustituirse por un escritor asincrono acotado antes de experimentar a escala.

## Validar los registros
```shell
python scripts/lab_telemetry_report.py <ruta-logs>/lab-telemetry-v1.previous.jsonl <ruta-logs>/lab-telemetry-v1.jsonl --out informe-fase1.json
```
Si solo existe el fichero actual, se pasa solo ese fichero. El informe cuenta registros corruptos, gaps y diferencias de contadores acumulativos dentro de cada sesion. No decide mejoras.

## Limitaciones explicitas
1. Esta version **no mide** latencia de busqueda Kad, tasa de fuentes Kad validas, turnos perdidos, reintentos por transporte, conexiones TCP ni CPU/memoria.
2. No existen aun interruptores ni reconocimientos de perfil aplicado, por tanto este JSONL no satisface el contrato de `scripts/lab_experiment.py`.
3. No ha sido compilada ni ejecutada en Windows: falta comprobar MFC/Win32, rutas de logs, rotacion, integridad y rendimiento.
4. No usar dos clientes a la vez sobre los mismos archivos `Temp/.part`. No toca esas rutas.

## Siguiente paso tecnico
Agregar eventos Kad y eD2k/TCP/UDP, memoria/CPU, estado de conexion y autentico perfil experimental; verificar con pruebas A/A y sobrecarga de la sonda antes de iniciar el calendario de seis dias.
