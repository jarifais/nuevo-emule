# Nuevo eMule portable independiente — 6 de noviembre de 2026

## Objetivo

En el modo aislado predeterminado, ejecutar **nuevo-emule.exe** junto al eMule instalado sin compartir datos ni reemplazar su ventana. En el modo de rutas compartidas, usar las carpetas existentes **solo después de cerrar el instalado**. Este paquete es una **compilación experimental de Windows x64 Release**, no una versión validada funcionalmente en un PC de usuario.

## Separación implementada en la rama de desarrollo

- `NEW_EMULE_PORTABLE_BUILD` está definido para el proyecto eMule Release x64: la variante portable se decide en compilación, no por argumentos editables del usuario.
- `CemuleApp::ProcessCommandline` usa un mutex propio para la variante portable: impide abrir dos copias de **la misma variante portable** sobre el mismo directorio de datos, pero permite abrir el eMule instalado en paralelo.
- `Emule.cpp` y `EmuleDlg.cpp` registran mensajes de identificación de ventana distintos para cada variante. Así, al comprobar instancias ya abiertas, no se activa por error la ventana del otro programa.
- Título visible: «nuevo-emule PORTABLE» (también cuando se muestran tasas de transferencia).
- `CPreferences::GetDefaultDirectory` no consulta el perfil de eMule instalado, ni su preferencia de directorios en el registro. Usa `data/` dentro de la carpeta descomprimida.
- En modo portable, `data/Temp` y `data/Incoming` son los valores predeterminados, pero **se respetan** `TempDir`, `TempDirs` e `IncomingDir` de `data/config/preferences.ini`. Así se pueden reutilizar carpetas existentes sin duplicar los archivos, de manera explícita. Las preferencias siguen siendo independientes del eMule instalado.
- Se desactiva la toma automática de asociaciones ED2K, el cambio de inicio automático y la alteración automática de reglas del firewall de eMule.
- Se mantienen los puertos de red elegidos mediante las preferencias propias. Si se copia `preferences.ini` del instalado, los puertos también serán los de ese archivo; nunca ejecutar ambos clientes a la vez utilizando las mismas carpetas temporales.
- Si se utilizan carpetas externas, el portable comprueba al arrancar que las rutas configuradas existan y sean directorios; si falta un disco USB, se detiene antes de cargar la cola, evitando sustituir silenciosamente las rutas.
- Si se utilizan carpetas externas, el portable busca la ventana original y reserva el mutex de instancia del eMule instalado para su puerto configurado. Esta protección es preventiva, **no autoriza** a iniciar el original con `-ignoreinstances` ni a utilizar perfiles compartidos en paralelo.

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

## Comprobación manual del modo aislado (sin compartir Temp)

1. Extraer el **ZIP de la compilación que contenga estas correcciones** en una carpeta nueva, distinta de la instalación de eMule, y con permisos de escritura.
2. Abrir el eMule instalado y dejarlo funcionando.
3. Ejecutar `nuevo-emule.exe` (no `emule.exe` de un ZIP antiguo).
4. Confirmar dos procesos distintos en el Administrador de tareas. Verificar que la segunda ventana muestra «nuevo-emule PORTABLE».
5. Comprobar que solo se crean ficheros de configuración y temporales dentro de `data/`, y que `Incoming` y `Temp` del instalado no cambian.
6. Reiniciar solo la variante portable y comprobar que conserva **sus** preferencias y descargas de prueba.
7. Verificar que un segundo inicio de `nuevo-emule.exe` no abre otra instancia que comparta su perfil.
8. Comprobar conectividad si se desean descargas concurrentes; asegurarse de que los puertos TCP/UDP no coinciden.

**Precaución:** la simultaneidad descrita aquí solo corresponde al modo aislado. En el modo compartido está prohibido utilizar simultáneamente los mismos `.part`/`.part.met`. No hay pruebas funcionales realizadas sobre un equipo Windows con eMule instalado de forma simultánea.


## Reutilizar rutas del eMule instalado sin duplicar Temp (modo voluntario)

1. **Cerrar por completo el eMule instalado** y comprobar que no queda su proceso en el Administrador de tareas. No abrir dos programas sobre los mismos `.part`/`.part.met`.
2. Extraer el nuevo ZIP en un directorio distinto y vacío. **No copiar** la carpeta `Temp` ni `Incoming`.
3. Antes del primer inicio del portable, copiar **solo los archivos pequeños** `preferences.ini` y `Category.ini` desde la carpeta `config` original hacia `data/config` del portable, sin borrar los originales. Los directorios guardados en `preferences.ini` deben existir y ser accesibles. `Category.ini` conserva los filtros y categorías (incluidas rutas de finalización); revisar las rutas externas antes de descargar. El directorio `config` original puede estar bajo la instalación, el perfil de usuario o datos públicos, según cómo esté instalado eMule.
4. Iniciar **solo** `nuevo-emule.exe`. En Opciones > Carpetas, comprobar que las rutas `Temp` e `Incoming` corresponden a las del eMule instalado. La cola se carga desde los `.part.met` originales, sin mover/copiar `Temp`.
5. Cerrar normalmente el portable antes de abrir el original. El portable guarda sus preferencias en **su propio** `data/config/preferences.ini` al cerrar; los cambios de progreso de descargas se escriben en los `.part`/`.part.met` **originales**. Al volver a abrir el portable se mantienen las rutas elegidas.
6. Si solo interesa la interfaz con >10.000 descargas, desconectar la red durante la primera prueba; medir selección Mayús+flecha, cambio de categoría y memoria sin efectuar transferencias. Si hace falta probar descargas reales, conviene respaldar antes al menos los ficheros de metadatos `.part.met` y `.part.met.bak`, que normalmente ocupan mucho menos espacio que toda la carpeta `Temp`.

**Limitaciones:** es una compilación experimental. La comprobación de instancias minimiza el riesgo pero no garantiza exclusividad absoluta si se usan parámetros para ignorar instancias, otros clientes, puertos diferentes o sesiones distintas. Nunca ejecutar en paralelo sobre una misma carpeta `Temp`. Si un destino original desaparece o deja de estar disponible, restaurarlo antes del inicio en vez de aceptar una carpeta alternativa.

## Pendiente

- Confirmar el éxito de la última ejecución de compilación y que el release incluya este commit.
- Prueba manual de dos versiones en paralelo **solo con perfiles aislados**; en modo compartido, comprobar que no pueden abrirse a la vez.
- Posteriores benchmarks de selección masiva, CPU, memoria, E/S y recuperación de ficheros.
