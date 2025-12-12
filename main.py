import os
import sys
import pyproj # Necesario para localizar la base de datos

# --- SOLUCIÓN ROBUSTA PARA PROJ.DB ---
try:
    # Le pedimos a pyproj que nos diga dónde está su carpeta de datos
    ruta_proj = pyproj.datadir.get_data_dir()
    
    # Configuramos la variable de entorno
    os.environ['PROJ_LIB'] = ruta_proj
    
    print(f"--- FIX: PROJ_LIB configurado exitosamente en: {ruta_proj} ---")

except Exception as e:
    print(f"--- Error crítico: No se pudo configurar PROJ_LIB. Detalle: {e} ---")
    print("Intenta reinstalar pyproj: pip install --force-reinstall pyproj")

# -------------------------------------------------------------------

import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
import contextily as cx
import os
import warnings

# Suprimir advertencias de CRS que a veces lanza contextily si no coinciden exacto
warnings.filterwarnings("ignore", category=UserWarning)

def visualizar_dem_con_satelite(ruta_archivo, factor_escala_max=2000):
    
    if not os.path.exists(ruta_archivo):
        print(f"Error: El archivo {ruta_archivo} no existe.")
        return

    try:
        with rasterio.open(ruta_archivo) as src:
            print(f"Abriendo: {src.name}")
            
            # --- MANEJO DE MEMORIA ---
            scale = 1
            # Un pequeño margen de seguridad, si se pasa por poco no reescala
            if src.width > (factor_escala_max * 1.1) or src.height > (factor_escala_max * 1.1):
                scale = max(src.width, src.height) // factor_escala_max
                print(f"Reduciendo escala en factor de: {scale} para visualización.")
            
            new_height = src.height // scale
            new_width = src.width // scale
            
            # Leer datos
            elevacion = src.read(
                1,
                out_shape=(new_height, new_width),
                resampling=rasterio.enums.Resampling.bilinear
            )
            
            # Leer bounds
            bounds = src.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
            # Usar un valor numérico seguro si nodata es None
            nodata_val = src.nodata if src.nodata is not None else -99999.0

    except Exception as e:
        print(f"Error leyendo el archivo TIFF: {e}")
        return

    # --- PROCESAMIENTO ---
    # Enmascarar no-data. Es crucial usar una copia para no alterar datos originales si se reusaran
    elevacion_masked = np.ma.masked_equal(elevacion.copy(), nodata_val)

    # Si todo está enmascarado (ej. archivo vacío), salir
    if elevacion_masked.mask.all():
         print("Error: El archivo parece contener solo valores NoData en el área leída.")
         return
    
    # Mapa de colores 'terrain'
    cmap_terrain = plt.get_cmap('terrain')

    # --- HILLSHADE + TRANSPARENCIA AUTOMÁTICA ---
    print("Generando hillshade...")
    ls = LightSource(azdeg=315, altdeg=45)
    
    # CORRECCIÓN CRÍTICA:
    # ls.shade con masked arrays ya devuelve una imagen RGBA (4 canales)
    # con la transparencia aplicada correctamente en las zonas enmascaradas.
    # No necesitamos crear el canal alfa manualmente.
    img_rgba = ls.shade(elevacion_masked, cmap=cmap_terrain, blend_mode='overlay', vert_exag=10, dx=scale, dy=scale)
    

    # --- GRAFICACIÓN ---
    print("Preparando gráfico...")
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # 1. Pintamos el DEM (img_rgba ya tiene transparencia)
    # Usamos zorder=10 para asegurar que quede ENCIMA del satélite
    ax.imshow(img_rgba, extent=extent, origin='upper', zorder=10)
    
    # Ensure the plot limits match the extent exactly
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_axis_off()

    # --- AGREGAR IMAGEN SATELITAL ---
    print("Descargando mapa base satelital (puede tardar)...")
    try:
        # Se fuerza el CRS CTM12 (EPSG:9377)
        cx.add_basemap(ax, 
                       crs="EPSG:9377", 
                       source=cx.providers.Esri.WorldImagery, 
                       attribution=False,
                       zoom='auto',
                       zorder=1) # Satélite al fondo
    except Exception as e:
        print(f"ADVERTENCIA: No se pudo cargar el mapa base satelital. Revisa tu conexión a internet.\nDetalle error: {e}")

    # --- BARRA DE COLOR ---
    min_elev = np.nanmin(elevacion_masked)
    max_elev = np.nanmax(elevacion_masked)
    
    # Creamos el Mappable solo si hay rango válido de datos
    if not np.isnan(min_elev) and not np.isnan(max_elev):
        min_lbl = round(float(min_elev), 1)
        max_lbl = round(float(max_elev), 1)
        sm = plt.cm.ScalarMappable(cmap=cmap_terrain, norm=plt.Normalize(vmin=min_elev, vmax=max_elev))
        sm.set_array([])
        
        cbar = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.02, shrink=0.7)
        cbar.set_label(f'Elevación (m) [{min_lbl}, {max_lbl}]', fontsize=10)
        cbar.outline.set_visible(False)

    # Guardar
    nombre_salida = f"mapa_elevacion_{os.path.basename(ruta_archivo)[:-4]}.png"
    print(f"Guardando imagen en disco...")
    # Se usa try/except al guardar por si hay problemas de permisos
    try:
        plt.savefig(nombre_salida, dpi=300, bbox_inches='tight', pad_inches=0)
        print(f"¡Éxito! Imagen guardada como: {nombre_salida}")
    except Exception as e:
        print(f"Error al guardar la imagen: {e}")
        
    # plt.show() # Comentado para ejecución más rápida en bucles, descomentar si se desea ver.
    plt.close(fig) # Cierra la figura para liberar memoria

if __name__ == "__main__":
    # Permite arrastrar y soltar el archivo en la consola
    ruta = input("Arrastra y suelta el archivo .tif aquí y presiona Enter: ").strip()
    # Limpieza básica de rutas de Windows que a veces añaden comillas o caracteres raros
    ruta = ruta.strip('"').strip("'").replace("& ", "")
    
    visualizar_dem_con_satelite(ruta)
