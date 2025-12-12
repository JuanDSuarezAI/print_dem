import os
import sys
import warnings
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pyproj
import rasterio

# --- CONFIGURACIÓN PROJ ---
try:
    os.environ["PROJ_LIB"] = pyproj.datadir.get_data_dir()
except Exception:
    pass

warnings.filterwarnings("ignore")

def obtener_configuracion_peligro(tipo_mapa, data_max):
    """
    Define los colores y los intervalos (bins) fijos para peligrosidad.
    Esto asegura que 1.5 m/s siempre se vea peligroso, sin importar el máximo del raster.
    """
    if tipo_mapa == 'v': # VELOCIDAD
        # Rangos basados en estabilidad de vehículos y personas
        # 0-0.5 (Bajo), 0.5-1.0 (Medio), 1.0-2.0 (Alto), >2.0 (Extremo)
        bounds = [0, 0.5, 1.0, 2.0, max(5.0, data_max + 1)] 
        
        # Colores Hex: Verde suave, Amarillo, Naranja, Rojo Intenso
        colors = ["#4cedb2", "#ffee00", "#ff9900", "#cc0000"]
        label_bar = "Velocidad (m/s)"
        title = "Mapa de Velocidad de Flujo"
        
    else: # PROFUNDIDAD
        # Rangos: 0-0.3 (Tobillos), 0.3-0.8 (Rodilla/Cintura), 0.8-1.5 (Pecho), >1.5 (Te tapa)
        bounds = [0, 0.3, 0.8, 1.5, max(5.0, data_max + 1)]
        
        # Colores: Celeste agua, Azul agua, Naranja alerta, Rojo peligro
        colors = ["#a6cee3", "#1f78b4", "#fdbf6f", "#e31a1c"]
        label_bar = "Profundidad (m)"
        title = "Mapa de Profundidad de Inundación"

    # Creamos el mapa de colores discreto (traffic light style)
    cmap = mcolors.ListedColormap(colors)
    # BoundaryNorm fuerza a que los colores cambien EXACTAMENTE en los bounds
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    
    return cmap, norm, bounds, label_bar, title

def visualizar_amenaza(ruta_raster, ruta_shapefile, tipo_mapa, nombre_salida=None):
    
    # 1. LEER RASTER
    if not os.path.exists(ruta_raster):
        print("Error: No se encuentra el archivo raster.")
        return

    try:
        with rasterio.open(ruta_raster) as src:
            print(f"Leyendo raster: {src.name}")
            
            # Downsampling para memoria (opcional, ajusta 2000 según necesites)
            factor_escala_max = 2000
            scale = 1
            if src.width > factor_escala_max or src.height > factor_escala_max:
                scale = max(src.width, src.height) // factor_escala_max
            
            new_h, new_w = src.height // scale, src.width // scale
            data = src.read(1, out_shape=(new_h, new_w), resampling=rasterio.enums.Resampling.bilinear)
            
            # Coordenadas
            bounds = src.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
            crs_raster = src.crs
            nodata = src.nodata if src.nodata is not None else -9999.0
            
    except Exception as e:
        print(f"Error abriendo raster: {e}")
        return

    # Enmascarar NoData y valores <= 0 (asumimos que 0 no es inundación para visualizar)
    data_masked = np.ma.masked_less_equal(data, 0)
    data_masked = np.ma.masked_equal(data_masked, nodata)
    
    if data_masked.mask.all():
        print("El raster no tiene datos válidos (todo es <= 0 o nodata).")
        return

    max_val_real = np.nanmax(data_masked)
    
    # 2. CONFIGURAR COLORES (Lógica de peligrosidad)
    cmap, norm, boundaries, label_text, titulo = obtener_configuracion_peligro(tipo_mapa, max_val_real)

    # 3. LEER Y PROCESAR SHAPEFILE (Perímetro Urbano)
    gdf = None
    if ruta_shapefile and os.path.exists(ruta_shapefile):
        try:
            print("Cargando perímetro urbano...")
            gdf = gpd.read_file(ruta_shapefile)
            
            # CRÍTICO: El shapefile debe tener el mismo sistema de coordenadas que el raster
            if gdf.crs != crs_raster:
                print(f"Reproyectando shapefile de {gdf.crs} a {crs_raster}...")
                gdf = gdf.to_crs(crs_raster)
        except Exception as e:
            print(f"Advertencia: No se pudo cargar el Shapefile. {e}")

    # 4. GRAFICAR
    print("Generando mapa...")
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # A. Datos de inundación (Sin Hillshade, plano, colores categóricos)
    im = ax.imshow(data_masked, cmap=cmap, norm=norm, extent=extent, origin='upper', zorder=5, alpha=0.9)
    
    # B. Perímetro Urbano (Solo borde)
    if gdf is not None:
        # Plot del borde en negro o gris oscuro
        gdf.boundary.plot(ax=ax, color='black', linewidth=1.5, zorder=15, linestyle='--')

    # C. Mapa Base Satelital
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_axis_off()
    
    try:
        # EPSG:9377 para CTM12 Colombia
        cx.add_basemap(ax, crs="EPSG:9377", source=cx.providers.Esri.WorldImagery, attribution=False, zoom='auto', zorder=1)
    except:
        print("No se pudo descargar el mapa base.")

    # 5. LEYENDA (Customizada para mostrar rangos)
    # Truco: Usamos los boundaries para pintar la barra
    cbar = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02, shrink=0.6, ticks=boundaries[:-1] + [max_val_real])
    
    # Ajustamos etiquetas para que el ultimo valor muestre el máximo real
    labels_cbar = [str(b) for b in boundaries[:-1]]
    labels_cbar.append(f">{boundaries[-2]} (Max: {max_val_real:.2f})")
    
    # Limpiamos las etiquetas intermedias si son muchas, pero aquí son pocas (4 o 5)
    cbar.ax.set_yticklabels(labels_cbar) 
    cbar.set_label(label_text, fontsize=10, weight='bold')
    cbar.outline.set_visible(False)
    
    # Título
    plt.title(f"{titulo}\n(Máximo registrado: {max_val_real:.2f})", fontsize=12)

    # 6. GUARDAR
    sufijo = "velocidad" if tipo_mapa == 'v' else "profundidad"
    base_predeterminado = f"mapa_amenaza_{sufijo}_{Path(ruta_raster).stem}"
    base_nombre = nombre_salida.strip().strip('"').strip("'") if nombre_salida else base_predeterminado
    if not base_nombre.lower().endswith(".png"):
        base_nombre = f"{base_nombre}.png"
    nombre_salida_final = base_nombre
    
    plt.savefig(nombre_salida_final, dpi=300, bbox_inches='tight', pad_inches=0.1)
    print(f"¡Mapa guardado!: {nombre_salida_final}")
    plt.close(fig)

if __name__ == "__main__":
    print("--- GENERADOR DE MAPAS DE AMENAZA (Profundidad/Velocidad) ---")
    
    r_raster = input("Ruta del archivo .tif: ").strip().strip('"').strip("'")
    
    tipo = input("¿Qué variable es? (Escribe 'v' para Velocidad, 'p' para Profundidad): ").lower().strip()
    while tipo not in ['v', 'p']:
        tipo = input("Opción no válida. Escribe 'v' o 'p': ").lower().strip()
        
    r_shp = input("Ruta del Shapefile de perímetro urbano (.shp): ").strip().strip('"').strip("'")
    
    nombre_out = input("Nombre del archivo de salida (sin extensión, opcional): ").strip()
    nombre_out = nombre_out if nombre_out else None
    
    visualizar_amenaza(r_raster, r_shp, tipo, nombre_salida=nombre_out)
