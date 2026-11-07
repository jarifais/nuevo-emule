# nuevo-emule

Versión personalizada de eMule Community para Windows, basada en la publicación **0.72a** de [irwir/eMule](https://github.com/irwir/eMule/releases/tag/eMule_v0.72a-community).

## Primera mejora: «Descargar en...»

Desde los resultados de búsqueda, seleccionar uno o varios archivos y elegir directamente una carpeta de destino mediante el menú contextual. Los archivos temporales siguen gestionándose normalmente y, al completarse las descargas, se guardan en la carpeta elegida.

La integración conserva el formato de categorías y los metadatos de eMule: crea o reutiliza automáticamente una categoría vinculada a esa carpeta para que el destino sobreviva a reinicios, sin obligar a crearla manualmente.

## Hoja de ruta de modernización

Seguimos **6 capas y 30 subetapas**, con estados y criterios de aceptación registrados en la [hoja de ruta](docs/HOJA_DE_RUTA_30_SUBETAPAS.md) y en el [issue de seguimiento #2](https://github.com/jarifais/nuevo-emule/issues/2).

La capa 1 optimiza la interfaz, los repintados, las categorías, la selección masiva y las fuentes A4AF. Los cambios están en el [PR de desarrollo #1](https://github.com/jarifais/nuevo-emule/pull/1). **Una subetapa implementada no se considera validada sin pruebas funcionales en Windows**; el caso de más de 10.000 descargas requiere [esta matriz de pruebas](docs/GUI_CAPA1_PRUEBAS_10000.md).

## Procedencia y licencia

Código original: eMule Community, publicación `eMule_v0.72a-community` (commit `ac3d52eafd88e9f6d9e0c2204c6dbead18db750b`). eMule se distribuye bajo GNU GPL v2; se conservan los avisos de autoría del código original. La privacidad de este repositorio no sustituye las obligaciones de la GPL cuando se distribuyan ejecutables.

## Estado

El repositorio se inicializa mediante GitHub Actions a partir de la publicación indicada. **La compilación y prueba funcional en Windows deben verificarse antes de considerar el programa listo para uso.**
