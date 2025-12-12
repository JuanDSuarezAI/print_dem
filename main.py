import os
from pathlib import Path
import warnings

import contextily as cx
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import rasterio
from matplotlib.colors import LightSource


# Configura PROJ_LIB para evitar errores de datum
try:
    os.environ["PROJ_LIB"] = pyproj.datadir.get_data_dir()
except Exception as exc:
    print(f"Advertencia PROJ_LIB: {exc}")


warnings.filterwarnings("ignore")


def visualizar_dem_con_satelite_suave(ruta_archivo, factor_escala_max=2000, nombre_salida=None):
    if not os.path.exists(ruta_archivo):
        print(f"Error: El archivo {ruta_archivo} no existe.")
        return

    try:
        with rasterio.open(ruta_archivo) as src:
            print(f"Procesando: {src.name}")

            # Reduccion de escala para limitar memoria
            scale = 1
            if src.width > (factor_escala_max * 1.1) or src.height > (factor_escala_max * 1.1):
                scale = max(src.width, src.height) // factor_escala_max
                print(f"Reduciendo escala: factor {scale}")

            new_height = max(1, src.height // scale)
            new_width = max(1, src.width // scale)

            elevacion = src.read(
                1,
                out_shape=(new_height, new_width),
                resampling=rasterio.enums.Resampling.bilinear,
            )
            bounds = src.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
            nodata_val = src.nodata if src.nodata is not None else -99999.0
    except Exception as exc:
        print(f"Error leyendo TIFF: {exc}")
        return

    elevacion_masked = np.ma.masked_equal(elevacion.copy(), nodata_val)
    if elevacion_masked.mask.all():
        print("Error: El archivo contiene solo valores NoData en el area leida.")
        return

    cmap_terrain = plt.get_cmap("terrain")

    print("Generando hillshade suave...")
    ls = LightSource(azdeg=315, altdeg=35)
    img_rgba = ls.shade(
        elevacion_masked,
        cmap=cmap_terrain,
        blend_mode="soft",
        vert_exag=5,
        dx=scale,
        dy=scale,
    )

    fig, ax = plt.subplots(figsize=(12, 12))
    ax.imshow(img_rgba, extent=extent, origin="upper", zorder=10)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_axis_off()

    try:
        cx.add_basemap(
            ax,
            crs="EPSG:9377",
            source=cx.providers.Esri.WorldImagery,
            attribution=False,
            zoom="auto",
            zorder=1,
        )
    except Exception as exc:
        print(f"Advertencia al cargar basemap: {exc}")

    # Barra de color con min/max reales
    min_real = float(np.nanmin(elevacion_masked))
    max_real = float(np.nanmax(elevacion_masked))
    vmin_uso = min_real if min_real > 0 else 0.0
    vmax_uso = max_real

    norm = plt.Normalize(vmin=vmin_uso, vmax=vmax_uso)
    sm = plt.cm.ScalarMappable(cmap=cmap_terrain, norm=norm)
    sm.set_array([])

    niveles = np.linspace(vmin_uso, vmax_uso, 5)
    cbar = plt.colorbar(sm, ax=ax, fraction=0.030, pad=0.02, shrink=0.6, ticks=niveles)
    cbar.ax.set_yticklabels([f"{x:.1f}" for x in niveles])
    cbar.set_label(f"Elevacion (m) [{min_real:.1f}, {max_real:.1f}]", fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    cbar.outline.set_visible(False)

    # Guardar con nombre proporcionado por el usuario
    base_predeterminado = f"mapa_suave_{Path(ruta_archivo).stem}"
    base_nombre = nombre_salida.strip().strip('"').strip("'") if nombre_salida else base_predeterminado
    if not base_nombre.lower().endswith(".png"):
        base_nombre = f"{base_nombre}.png"
    nombre_salida_final = base_nombre

    print("Guardando imagen...")
    plt.savefig(nombre_salida_final, dpi=300, bbox_inches="tight", pad_inches=0)
    print(f"Listo: {nombre_salida_final}")
    plt.close(fig)


if __name__ == "__main__":
    ruta = input("Arrastra el archivo .tif: ").strip().strip('"').strip("'")
    salida = input("Nombre del archivo de salida (sin extension, opcional): ").strip()
    salida = salida if salida else None
    visualizar_dem_con_satelite_suave(ruta, nombre_salida=salida)
