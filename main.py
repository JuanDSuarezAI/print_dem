import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, LinearSegmentedColormap
import os

def visualizar_dem_limpio(ruta_archivo, factor_escala_max=2000):
    
    if not os.path.exists(ruta_archivo):
        print(f"Error: El archivo {ruta_archivo} no existe.")
        return

    try:
        with rasterio.open(ruta_archivo) as src:
            # --- MANEJO DE MEMORIA ---
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
    # Filtro opcional para ruido extremo negativo si es necesario
    # elevacion_masked = np.ma.masked_less(elevacion_masked, -50) 

    # --- COLORES ---
    colors = [
        (0.0, "#1f0c48"),  # Profundidad/Negativo
        (0.2, "#1fa4b6"),  # Agua panda
        (0.4, "#e5ff00"),  # Zonas bajas
        (0.6, "#f4e6c7"),  # Tierra
        (0.8, "#8c6d31"),  # Montaña
        (1.0, "#ffffff")   # Picos
    ]
    cmap_custom = LinearSegmentedColormap.from_list("custom_terrain", colors)

    # --- HILLSHADE ---
    ls = LightSource(azdeg=315, altdeg=45)
    # vert_exag=10 ayuda a que se note la textura en zonas planas
    rgb = ls.shade(elevacion_masked, cmap=cmap_custom, blend_mode='overlay', vert_exag=10, dx=scale, dy=scale)

    # --- GRAFICACIÓN LIMPIA ---
    fig, ax = plt.subplots(figsize=(12, 12)) # Tamaño cuadrado grande
    
    ax.imshow(rgb, extent=extent, origin='upper')
    
    # ESTO ELIMINA LOS EJES Y EL RECUADRO
    ax.set_axis_off() 
    
    # --- BARRA DE COLOR ---
    min_elev = np.nanmin(elevacion_masked)
    max_elev = np.nanmax(elevacion_masked)
    
    sm = plt.cm.ScalarMappable(cmap=cmap_custom, norm=plt.Normalize(vmin=min_elev, vmax=max_elev))
    sm.set_array([])
    
    # Barra más estética
    cbar = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.02, shrink=0.7)
    cbar.set_label('Elevación (m)', fontsize=10)
    cbar.ax.tick_params(labelsize=9)
    # Hacemos el borde de la barra invisible si quieres un look más moderno
    cbar.outline.set_visible(False) 

    # Guardar imagen automáticamente recortando espacios en blanco
    nombre_salida = "mapa_elevacion_final.png"
    plt.savefig(nombre_salida, dpi=300, bbox_inches='tight', pad_inches=0)
    print(f"Imagen guardada como: {nombre_salida}")
    
    plt.show()

if __name__ == "__main__":
    ruta = input("Ingresa la ruta del archivo .tif: ").strip().replace('"', '').replace("'", "")
    visualizar_dem_limpio(ruta)
