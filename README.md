# print_dem

Script para generar hillshade de un DEM (GeoTIFF), combinándolo con imagen satelital de Esri World Imagery. Optimiza memoria reduciendo resolución cuando el raster es muy grande, respeta valores nodata y permite definir el nombre de salida del PNG.

## Requisitos
- Python 3.9+
- Librerías: `rasterio`, `numpy`, `matplotlib`, `contextily`, `pyproj`
- Acceso a internet para descargar el basemap satelital (si no hay conexión, el script sigue y solo pinta el hillshade).

## Uso rápido
1) Activa el entorno virtual (si aplica) y ejecuta:
```bash
python main.py
```
2) Cuando se solicite:
   - Arrastra o escribe la ruta del archivo `.tif`.
   - Ingresa el nombre de salida (sin extensión). El script agrega `.png` automáticamente. Si lo dejas en blanco, genera `mapa_suave_<nombre_del_tif>.png`.

## Notas
- El script intenta ubicar automáticamente la base de datos de `proj` (configura `PROJ_LIB`). Si hay problemas de datum, reinstala `pyproj`.
- Usa blend `soft`, exageración vertical moderada y percentiles para mejorar el contraste.
- La barra de color muestra el rango real mínimo/máximo redondeado a 0.1.
- Se recomienda trabajar en EPSG:9377 (CTM12), pero el script no bloquea otras proyecciones.
