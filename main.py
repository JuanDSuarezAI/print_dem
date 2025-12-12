import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, LinearSegmentedColormap
import os

def visualizar_dem(ruta_archivo, factor_escala_max=2000):
    """
    Visualiza un DEM con efecto hillshade y manejo de nodata.
    
    Args:
        ruta_archivo (str): Ruta al archivo .tif
        factor_escala_max (int): Ancho máximo en píxeles para visualización.
                                 Ayuda a no colapsar la memoria con archivos grandes.
    """
    
    if not os.path.exists(ruta_archivo):
        print(f"Error: El archivo {ruta_archivo} no existe.")
        return

    try:
        with rasterio.open(ruta_archivo) as src:
            print(f"Abriendo: {src.name}")
            print(f"Tamaño original: {src.width} x {src.height}")
            print(f"Sistema de Coordenadas detectado: {src.crs} (Asumido CTM12 por usuario)")

            # --- MANEJO DE MEMORIA ---
            # Si el raster es muy grande, calculamos un factor de reducción
            # para leer solo una vista general (overview) y no explotar la RAM.
            scale = 1
            if src.width > factor_escala_max or src.height > factor_escala_max:
                scale = max(src.width, src.height) // factor_escala_max
                print(f"El archivo es grande. Aplicando reducción de escala: 1/{scale}")

            # Leemos los datos redimensionados
            # out_shape define el nuevo tamaño de la matriz
            new_height = src.height // scale
            new_width = src.width // scale
            
            # Leemos la banda 1
            elevacion = src.read(
                1,
                out_shape=(new_height, new_width),
                resampling=rasterio.enums.Resampling.bilinear
            )
            
            # Leemos los límites (bounds) para pintar los ejes con coordenadas reales (CTM12)
            bounds = src.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]

            # Obtenemos el valor nodata del archivo, si no tiene, usamos -9999 por defecto
            nodata_val = src.nodata if src.nodata is not None else -9999.0

    except Exception as e:
        print(f"Error leyendo el archivo: {e}")
        return

    # --- PROCESAMIENTO DE DATOS ---
    
    # Crear una máscara para los valores NoData (-9999)
    # Usamos np.nan para que matplotlib los ignore o los pinte transparente
    elevacion_masked = np.ma.masked_equal(elevacion, nodata_val)
    
    # Manejo de valores extremos si hay ruido (opcional, limpia la visualización)
    # A veces hay puntos -9999 que no están marcados como nodata
    elevacion_masked = np.ma.masked_less(elevacion_masked, -500) # Asumiendo que no hay nada debajo de -500m en tu zona

    # --- CONFIGURACIÓN DE ESTILO (Colores tipo 'Topobatimétria') ---
    
    # Definimos un colormap personalizado similar al de tus imágenes
    # Secuencia: Azul Oscuro -> Azul Claro -> Verde/Amarillo -> Marrón -> Blanco
    colors = [
        (0.0, "#1f0c48"),  # Fondo profundo (Morado oscuro/Azul)
        (0.2, "#1fa4b6"),  # Agua panda / zonas bajas (Turquesa)
        (0.4, "#e5ff00"),  # Zonas medias bajas (Amarillo)
        (0.6, "#f4e6c7"),  # Tierra (Beige)
        (0.8, "#8c6d31"),  # Montaña (Marrón)
        (1.0, "#ffffff")   # Picos (Blanco)
    ]
    cmap_custom = LinearSegmentedColormap.from_list("custom_terrain", colors)

    # --- CÁLCULO DE HILLSHADE (Efecto de relieve) ---
    print("Calculando Hillshade...")
    ls = LightSource(azdeg=315, altdeg=45) # Luz desde el Noroeste a 45 grados

    # rgb_shaded combina el color (basado en elevación) con la sombra (basado en pendiente)
    # vert_exag: Exageración vertical. Auméntalo (ej. 5 o 10) si el terreno se ve muy plano.
    rgb = ls.shade(elevacion_masked, cmap=cmap_custom, blend_mode='overlay', vert_exag=10, dx=scale, dy=scale)

    # --- GRAFICACIÓN ---
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Mostramos la imagen
    im = ax.imshow(rgb, extent=extent, origin='upper')
    
    # Configuración de ejes (Coordenadas CTM12)
    ax.set_title("Modelo de Elevación Digital (Topobatimetría)", fontsize=15)
    ax.set_xlabel("Este (m) - CTM12")
    ax.set_ylabel("Norte (m) - CTM12")
    ax.grid(True, linestyle='--', alpha=0.3)

    # --- BARRA DE COLOR (LEYENDA) ---
    # Como usamos ls.shade, imshow devuelve una imagen RGB sin datos escalares.
    # Necesitamos crear un "ScalarMappable" falso para pintar la barra de colores correcta.
    min_elev = np.nanmin(elevacion_masked)
    max_elev = np.nanmax(elevacion_masked)
    
    sm = plt.cm.ScalarMappable(cmap=cmap_custom, norm=plt.Normalize(vmin=min_elev, vmax=max_elev))
    sm.set_array([]) # Array vacío ficticio
    
    cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Elevación (m)')

    plt.tight_layout()
    plt.show()

# --- EJECUCIÓN ---
if __name__ == "__main__":
    # Solicitamos la ruta al usuario
    ruta = input("Por favor, ingresa la ruta completa de tu archivo .tif: ").strip()
    
    # Quitamos comillas si el usuario copió la ruta como "ruta"
    ruta = ruta.replace('"', '').replace("'", "")
    
    visualizar_dem(ruta)
