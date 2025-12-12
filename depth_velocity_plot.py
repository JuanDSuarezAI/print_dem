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

# --- CONFIGURACIÓN PROJ (Corrección para Windows/Entornos Virtuales) ---
try:
    os.environ["PROJ_LIB"] = pyproj.datadir.get_data_dir()
except Exception:
    pass

warnings.filterwarnings("ignore")

def obtener_configuracion_continua(tipo_mapa, data_max):
    """
    Define una paleta continua pero con lógica de seguridad.
    Si el raster tiene valores bajos, forzamos que el 'Rojo' no aparezca.
    Si tiene valores extremos, la escala se adapta.
    """
    
    if tipo_mapa == 'v': # VELOCIDAD
        # Referencia: A partir de 2.0 m/s es daño estructural (ROJO)
        # Definimos un gradiente: Transparente -> Cian -> Verde -> Amarillo -> Rojo -> Violeta
        colors = ["#e1f5fe", "#00e5ff", "#00c853", "#ffd600", "#d50000", "#4a148c"]
        # Posiciones relativas del gradiente (0.0 a 1.0) para distribuir los colores
        # Esto ayuda a que el amarillo/rojo resalten más
        nodes = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        
        label_bar = "Velocidad de Flujo (m/s)"
        title = "Mapa de Velocidad (Continuo)"
        
        # Lógica de seguridad:
        # Si el raster tiene max=0.5 (muy lento), NO queremos que se vea rojo.
        # Forzamos que la escala visual llegue al menos a 2.0 para mantener consistencia.
        # Si el raster tiene max=6.0 (rápido), la escala llega a 6.0.
        vmax_viz = max(data_max, 2.5) 

    else: # PROFUNDIDAD
        # Referencia: A partir de 1.5 m es riesgo alto de ahogamiento (ROJO)
        # Gradiente: Azul Claro -> Azul Medio -> Amarillo -> Naranja -> Rojo
        colors = ["#e0f7fa", "#29b6f6", "#fff176", "#ff9800", "#b71c1c"]
        nodes = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        label_bar = "Profundidad de Inundación (m)"
        title = "Mapa de Profundidad (Continuo)"
        
        # Si la inundación es bajita (0.3m), se verá azul. 
        # Si supera 1.5m, empezará a verse roja.
        vmax_viz = max(data_max, 2.0)

    # Creamos el mapa de colores continuo (LinearSegmented)
    cmap_name = "AmenazaCustom"
    cmap = mcolors.LinearSegmentedColormap.from_list(cmap_name, list(zip(nodes, colors)))
    
    return cmap, vmax_viz, label_bar, title

def visualizar_amenaza_continua(ruta_raster, ruta_shapefile, tipo_mapa, nombre_personalizado=None):
    
    # 1. LEER RASTER
    if not os.path.exists(ruta_raster):
        print("Error: No se encuentra el archivo raster.")
        return

    try:
        with rasterio.open(ruta_raster) as src:
            print(f"Procesando: {src.name}")
            
            # Downsampling inteligente para evitar colapsos de memoria
            factor_escala_max = 2000
            scale = 1
            if src.width > factor_escala_max or src.height > factor_escala_max:
                scale = max(src.width, src.height) // factor_escala_max
            
            new_h, new_w = src.height // scale, src.width // scale
            data = src.read(1, out_shape=(new_h, new_w), resampling=rasterio.enums.Resampling.bilinear)
            
            bounds = src.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
            crs_raster = src.crs
            nodata = src.nodata if src.nodata is not None else -9999.0
            
    except Exception as e:
        print(f"Error abriendo raster: {e}")
        return

    # Limpieza de datos (Mascara para NoData y valores <= 0)
    data_masked = np.ma.masked_less_equal(data, 0.001) # Filtramos 0 estricto
    data_masked = np.ma.masked_equal(data_masked, nodata)
    
    if data_masked.mask.all():
        print("El raster no tiene datos válidos en el área.")
        return

    max_val_real = np.nanmax(data_masked)
    min_val_real = np.nanmin(data_masked)
    
    # 2. CONFIGURAR COLORES (Escala Continua Inteligente)
    cmap, vmax_uso, label_text, titulo_mapa = obtener_configuracion_continua(tipo_mapa, max_val_real)

    # 3. LEER SHAPEFILE (Perímetro Urbano)
    gdf = None
    if ruta_shapefile and os.path.exists(ruta_shapefile):
        try:
            gdf = gpd.read_file(ruta_shapefile)
            if gdf.crs != crs_raster:
                gdf = gdf.to_crs(crs_raster)
        except Exception as e:
            print(f"Advertencia: No se pudo cargar el Shapefile. {e}")

    # 4. GRAFICAR
    print("Generando imagen...")
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # A. Raster de Inundación
    # Usamos vmin=0 y vmax=vmax_uso para anclar la escala de seguridad
    im = ax.imshow(data_masked, cmap=cmap, vmin=0, vmax=vmax_uso, 
                   extent=extent, origin='upper', zorder=5, alpha=0.9)
    
    # B. Perímetro Urbano
    if gdf is not None:
        gdf.boundary.plot(ax=ax, color='black', linewidth=1.2, zorder=15, linestyle='--')

    # C. Mapa Base
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_axis_off()
    
    try:
        cx.add_basemap(ax, crs="EPSG:9377", source=cx.providers.Esri.WorldImagery, attribution=False, zoom='auto', zorder=1)
    except: pass

    # 5. BARRA DE COLOR CONTINUA
    # Mostramos una barra continua, no por bloques
    cbar = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02, shrink=0.6)
    cbar.set_label(label_text, fontsize=10, weight='bold')
    cbar.outline.set_visible(False)
    # Etiqueta explícita del máximo en la parte superior
    cbar.ax.text(0.5, 1.02, f"Max: {max_val_real:.2f}", transform=cbar.ax.transAxes, ha='center', va='bottom', fontsize=9, weight='bold')
    
    # Añadir linea indicadora del máximo real si es menor que el tope de la escala
    if max_val_real < vmax_uso:
        cbar.ax.plot([0, 1], [max_val_real/vmax_uso, max_val_real/vmax_uso], 'w-', linewidth=2)
        cbar.ax.text(1.1, max_val_real/vmax_uso, f'Max: {max_val_real:.2f}', 
                     transform=cbar.ax.transAxes, color='black', fontsize=8, va='center')

    # 6. GUARDAR
    if nombre_personalizado:
        # Limpieza básica del nombre ingresado
        nombre_clean = nombre_personalizado.strip().replace('.png', '')
        nombre_salida = f"{nombre_clean}.png"
    else:
        # Nombre automático si no se define uno
        sufijo = "velocidad" if tipo_mapa == 'v' else "profundidad"
        nombre_salida = f"mapa_{sufijo}_{Path(ruta_raster).stem}.png"
    
    try:
        plt.savefig(nombre_salida, dpi=300, bbox_inches='tight', pad_inches=0.1)
        print(f"¡Éxito! Guardado como: {nombre_salida}")
    except Exception as e:
        print(f"Error al guardar: {e}")
        
    plt.close(fig)

if __name__ == "__main__":
    print("--- GENERADOR DE MAPAS CONTINUOS (Velocidad/Profundidad) ---")
    
    r_raster = input("Ruta del raster (.tif): ").strip().strip('"').strip("'")
    
    tipo = input("Tipo de mapa ('v' = Velocidad, 'p' = Profundidad): ").lower().strip()
    while tipo not in ['v', 'p']:
        tipo = input("Por favor ingresa 'v' o 'p': ").lower().strip()
        
    r_shp = input("Ruta Shapefile Urbano (Opcional, enter para saltar): ").strip().strip('"').strip("'")
    
    # NUEVO: Input para el nombre
    nom_salida = input("Nombre para guardar la imagen (Ej: escenario_tr100): ").strip()
    
    visualizar_amenaza_continua(r_raster, r_shp, tipo, nom_salida)
