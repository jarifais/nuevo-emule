# nuevo-emule

Versión personalizada de eMule Community para Windows, basada en la publicación **0.72a** de [irwir/eMule](https://github.com/irwir/eMule/releases/tag/eMule_v0.72a-community).

## Primera mejora: «Descargar en...»

Desde los resultados de búsqueda, seleccionar uno o varios archivos y elegir directamente una carpeta de destino mediante el menú contextual. Los archivos temporales siguen gestionándose normalmente y, al completarse las descargas, se guardan en la carpeta elegida.

La integración conserva el formato de categorías y los metadatos de eMule: crea o reutiliza automáticamente una categoría vinculada a esa carpeta para que el destino sobreviva a reinicios, sin obligar a crearla manualmente.

## Procedencia y licencia

Código original: eMule Community, publicación `eMule_v0.72a-community` (commit `ac3d52eafd88e9f6d9e0c2204c6dbead18db750b`). eMule se distribuye bajo GNU GPL v2; se conservan los avisos de autoría del código original. La privacidad de este repositorio no sustituye las obligaciones de la GPL cuando se distribuyan ejecutables.

## Estado

El repositorio se inicializa mediante GitHub Actions a partir de la publicación indicada. **La compilación y prueba funcional en Windows deben verificarse antes de considerar el programa listo para uso.**
