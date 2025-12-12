import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
import os

def visualizar_dem_terrain(ruta_archivo, factor_escala_max=2000):
    
    if not os.path.exists(ruta_archivo):
        print(f"Error: El archivo {ruta_archivo} no existe.")
        return

    try:
        with rasterio.open(ruta_archivo) as src:
            # --- MANEJO DE MEMORIA (Downsampling) ---
            scale = 1
            if src.width > factor_escala_max or src.height > factor_escala_max:
                scale = max(src.width, src.height) // factor_escala_max
            
            new_height = src.height // scale
            new_width = src.width // scale
            
            elevacion = src.read(
                1,
                out_shape=(new_height, new_width),
                resampling=rasterio.enums.Resampling.bilinear
            )
            
            bounds = src.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
            nodata_val = src.nodata if src.nodata is not None else -9999.0

    except Exception as e:
        print(f"Error leyendo el archivo: {e}")
        return

    # --- PROCESAMIENTO ---
    elevacion_masked = np.ma.masked_equal(elevacion, nodata_val)
    
    # --- COLORES (USANDO 'terrain') ---
    # Obtenemos el mapa de colores nativo de matplotlib
    # Esto reemplaza toda la lista manual de colores que teníamos antes.
    cmap_terrain = plt.get_cmap('terrain')

    # --- HILLSHADE ---
    ls = LightSource(azdeg=315, altdeg=45)
    
    # Aplicamos el sombreado usando el cmap 'terrain'
    rgb = ls.shade(elevacion_masked, cmap=cmap_terrain, blend_mode='overlay', vert_exag=10, dx=scale, dy=scale)

    # --- GRAFICACIÓN ---
    fig, ax = plt.subplots(figsize=(12, 12))
    
    ax.imshow(rgb, extent=extent, origin='upper')
    ax.set_axis_off() # Sin ejes ni bordes
    
    # --- BARRA DE COLOR ---
    min_elev = np.nanmin(elevacion_masked)
    max_elev = np.nanmax(elevacion_masked)
    
    sm = plt.cm.ScalarMappable(cmap=cmap_terrain, norm=plt.Normalize(vmin=min_elev, vmax=max_elev))
    sm.set_array([])
    
    # Barra de color limpia
    cbar = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.02, shrink=0.7)
    cbar.set_label('Elevación (m)', fontsize=10)
    cbar.ax.tick_params(labelsize=9)
    cbar.outline.set_visible(False)

    # Guardar
    nombre_salida = "mapa_elevacion_terrain.png"
    plt.savefig(nombre_salida, dpi=300, bbox_inches='tight', pad_inches=0)
    print(f"Imagen guardada con paleta 'terrain' como: {nombre_salida}")
    
    plt.show()

if __name__ == "__main__":
    ruta = input("Ingresa la ruta del archivo .tif: ").strip().replace('"', '').replace("'", "")
    visualizar_dem_terrain(ruta)
