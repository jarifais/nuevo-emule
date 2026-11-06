# Nuevo eMule portable independiente — 6 de noviembre de 2026

## Objetivo

Poder ejecutar **nuevo-emule.exe** simultáneamente con el eMule instalado, sin usar sus datos ni reemplazar o activar su ventana. Este paquete es una **compilación experimental de Windows x64 Release**, no una versión validada funcionalmente en un PC de usuario.

## Separación implementada en la rama de desarrollo

- `NEW_EMULE_PORTABLE_BUILD` está definido para el proyecto eMule Release x64: la variante portable se decide en compilación, no por argumentos editables del usuario.
- `CemuleApp::ProcessCommandline` usa un mutex propio para la variante portable: impide abrir dos copias de **la misma variante portable** sobre el mismo directorio de datos, pero permite abrir el eMule instalado en paralelo.
- `Emule.cpp` y `EmuleDlg.cpp` registran mensajes de identificación de ventana distintos para cada variante. Así, al comprobar instancias ya abiertas, no se activa por error la ventana del otro programa.
- Título visible: «nuevo-emule PORTABLE» (también cuando se muestran tasas de transferencia).
- `CPreferences::GetDefaultDirectory` no consulta el perfil de eMule instalado, ni su preferencia de directorios en el registro. Usa `data/` dentro de la carpeta descomprimida.
- En modo portable se fuerzan `data/Temp` y `data/Incoming` al cargar las preferencias, sin reutilizar rutas escritas en un archivo INI.
- Se desactiva la toma automática de asociaciones ED2K, el cambio de inicio automático y la alteración automática de reglas del firewall de eMule.
- Se mantienen los puertos de red elegidos de forma independiente mediante las preferencias propias (la asignación inicial suele ser aleatoria); en caso de conflicto es necesario cambiarlos.

## Estructura del ZIP

```text
nuevo-emule.exe
LEEME.txt
data/
  LEEME-DATOS.txt
  config/      <- preferencias.ini y demás configuración que genere la aplicación
  Temp/        <- ficheros temporales solo de la prueba
  Incoming/    <- descargas finalizadas solo de la prueba
```

El ZIP se publica como prerelease de GitHub, **únicamente cuando su workflow Windows x64 termine correctamente**. Un release antiguo no demuestra que estas correcciones estén incluidas.

## Comprobación manual obligatoria

1. Extraer el **ZIP de la compilación que contenga estas correcciones** en una carpeta nueva, distinta de la instalación de eMule, y con permisos de escritura.
2. Abrir el eMule instalado y dejarlo funcionando.
3. Ejecutar `nuevo-emule.exe` (no `emule.exe` de un ZIP antiguo).
4. Confirmar dos procesos distintos en el Administrador de tareas. Verificar que la segunda ventana muestra «nuevo-emule PORTABLE».
5. Comprobar que solo se crean ficheros de configuración y temporales dentro de `data/`, y que `Incoming` y `Temp` del instalado no cambian.
6. Reiniciar solo la variante portable y comprobar que conserva **sus** preferencias y descargas de prueba.
7. Verificar que un segundo inicio de `nuevo-emule.exe` no abre otra instancia que comparta su perfil.
8. Comprobar conectividad si se desean descargas concurrentes; asegurarse de que los puertos TCP/UDP no coinciden.

**Precaución:** no apuntar las dos instancias a los mismos `.part`/`.part.met` ni copiar a la variante experimental la cola en producción de más de 10.000 descargas. Hacer pruebas primero con archivos de prueba. No hay pruebas funcionales realizadas sobre un equipo Windows con eMule instalado de forma simultánea.

## Pendiente

- Confirmar el éxito de la última ejecución de compilación y que el release incluya este commit.
- Prueba manual con las dos versiones a la vez.
- Posteriores benchmarks de selección masiva, CPU, memoria, E/S y recuperación de ficheros.
