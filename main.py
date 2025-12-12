import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
import contextily as cx
import os
import sys
import pyproj
import warnings

# --- CONFIGURACIÓN ROBUSTA DE PROJ (Igual que antes) ---
try:
    ruta_proj = pyproj.datadir.get_data_dir()
    os.environ['PROJ_LIB'] = ruta_proj
except Exception as e:
    print(f"--- Advertencia PROJ: {e} ---")
# -------------------------------------------------------

warnings.filterwarnings("ignore")

def visualizar_dem_con_satelite_suave(ruta_archivo, factor_escala_max=2000):
    
    if not os.path.exists(ruta_archivo):
        print(f"Error: El archivo {ruta_archivo} no existe.")
        return

    try:
        with rasterio.open(ruta_archivo) as src:
            print(f"Procesando: {src.name}")
            # Manejo de escala para memoria
            scale = 1
            if src.width > (factor_escala_max * 1.1) or src.height > (factor_escala_max * 1.1):
                scale = max(src.width, src.height) // factor_escala_max
            
            new_height = src.height // scale
            new_width = src.width // scale
            
            elevacion = src.read(1, out_shape=(new_height, new_width), resampling=rasterio.enums.Resampling.bilinear)
            bounds = src.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
            nodata_val = src.nodata if src.nodata is not None else -99999.0

    except Exception as e:
        print(f"Error leyendo TIFF: {e}")
        return

    elevacion_masked = np.ma.masked_equal(elevacion.copy(), nodata_val)
    if elevacion_masked.mask.all(): return
    
    cmap_terrain = plt.get_cmap('terrain')

    # --- AQUÍ ESTÁN LOS CAMBIOS CLAVE PARA REDUCIR BRILLO ---
    print("Generando hillshade suave...")
    
    # CAMBIO 1: Altitud de la luz un poco más baja (opcional, prueba con 35 o 40)
    # Una luz más baja genera sombras más largas y menos brillo cenital directo.
    ls = LightSource(azdeg=315, altdeg=35) 
    
    # CAMBIO 2 y 3 en ls.shade:
    img_rgba = ls.shade(
        elevacion_masked, 
        cmap=cmap_terrain, 
        blend_mode='soft', # <--- CAMBIO CLAVE: Usar 'soft' en vez de 'overlay'
        vert_exag=5,       # <--- CAMBIO CLAVE: Reducir exageración (antes era 10)
        dx=scale, 
        dy=scale
    )
    # ---------------------------------------------------------
    
    # --- GRAFICACIÓN (Resto del código igual) ---
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.imshow(img_rgba, extent=extent, origin='upper', zorder=10)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_axis_off()

    try:
        cx.add_basemap(ax, crs="EPSG:9377", source=cx.providers.Esri.WorldImagery, attribution=False, zoom='auto', zorder=1)
    except: pass

    # --- BARRA DE COLOR (Con tu ajuste de mínimo en 0 y ticks exactos) ---
    min_real = np.nanmin(elevacion_masked)
    max_real = np.nanmax(elevacion_masked)
    vmin_uso = min_real if min_real > 0 else 0 
    vmax_uso = max_real
    
    norm = plt.Normalize(vmin=vmin_uso, vmax=vmax_uso)
    sm = plt.cm.ScalarMappable(cmap=cmap_terrain, norm=norm)
    sm.set_array([])
    
    # Ticks exactos
    niveles = np.linspace(vmin_uso, vmax_uso, 5)
    
    # Barra un poco más pequeña y discreta (shrink=0.6)
    cbar = plt.colorbar(sm, ax=ax, fraction=0.030, pad=0.02, shrink=0.6, ticks=niveles)
    cbar.ax.set_yticklabels([f'{x:.2f}' for x in niveles])
    cbar.set_label('Elevación (m)', fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    cbar.outline.set_visible(False)
    
    # Guardar
    nombre_salida = f"mapa_suave_{os.path.basename(ruta_archivo)[:-4]}.png"
    print(f"Guardando imagen...")
    plt.savefig(nombre_salida, dpi=300, bbox_inches='tight', pad_inches=0)
    print(f"¡Listo!: {nombre_salida}")
    plt.close(fig)

if __name__ == "__main__":
    ruta = input("Arrastra el archivo .tif: ").strip().strip('"').strip("'")
    visualizar_dem_con_satelite_suave(ruta)
