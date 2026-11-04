# Plan de pruebas: Descargar en...

Versión base: eMule Community 0.72a. Esta lista **no implica pruebas manuales realizadas**; GitHub Actions verifica compilación, no el comportamiento interactivo.

## Preparación

- Windows x64; realizar copia de seguridad de la configuración de eMule y de cualquier descarga en curso.
- Utilizar exclusivamente archivos cuya distribución/descarga esté autorizada.
- Crear dos carpetas de prueba, por ejemplo `D:\Pruebas\DestinoA` y `D:\Pruebas\DestinoB`.
- Mantener una carpeta `Temp` distinta de las carpetas de destino.

## Casos funcionales

| ID | Acción | Resultado esperado |
| --- | --- | --- |
| QA-01 | Buscar y descargar mediante la opción habitual. | Comportamiento original intacto. |
| QA-02 | Seleccionar un resultado, elegir «Descargar en...» y DestinoA. | Archivo completado en DestinoA, no en Incoming. |
| QA-03 | Seleccionar varios resultados y DestinoB. | Todos los nuevos archivos terminan en DestinoB. |
| QA-04 | Abrir «Descargar en...» y cancelar. | No se añaden descargas ni categorías. |
| QA-05 | Repetir DestinoA con otros resultados. | Se reutiliza la categoría de destino existente. |
| QA-06 | Pausar, cerrar e iniciar eMule durante una descarga destinada a DestinoA. | El destino se conserva cuando termina la transferencia. |
| QA-07 | Seleccionar un resultado que ya esté descargándose. | No se crea duplicado ni se cambia su destino. |
| QA-08 | Descargar dos archivos de igual nombre a un mismo destino. | No se sobrescribe silenciosamente ningún archivo existente. |
| QA-09 | Utilizar una carpeta de red accesible (UNC). | La selección y el traslado final funcionan, si la red y permisos lo permiten. |
| QA-10 | Quitar permisos o desconectar el destino durante la descarga. | **Limitación de la base original:** eMule puede redirigir la finalización a Incoming si desaparece el destino. No considerar superado hasta modificar y probar ese comportamiento. |

## Comprobaciones técnicas

1. La opción de contexto solo está habilitada cuando hay resultados descargables seleccionados.
2. La carpeta temporal de los `.part` no se cambia por el nuevo menú.
3. La carpeta asociada queda guardada mediante las categorías ya persistentes en eMule.
4. El archivo compilado se identifica como binario Windows x64 y procede del commit esperado.
5. Probar eD2k y Kad en un entorno autorizado, sin dar por probado el funcionamiento de red por el simple hecho de compilar.

## Criterio de aceptación

Compilación x64 correcta **y** QA-01 a QA-09 comprobados manualmente. QA-10 permanece como limitación expresamente conocida hasta implementarla.
