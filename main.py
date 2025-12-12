import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LightSource
from rasterio.enums import Resampling


def visualizar_dem_con_hillshade(ruta_tiff, ruta_salida=None, max_pixels=8_000_000):
    """Genera y guarda un hillshade suavizando memoria en archivos grandes."""
    ruta = Path(ruta_tiff)
    if not ruta.exists():
        print("❌ La ruta especificada no existe.")
        return

    with rasterio.open(ruta) as src:
        epsg = src.crs.to_epsg() if src.crs else None
        if epsg != 9377:
            print("⚠️ El archivo no está en proyección CTM12 (EPSG:9377); se continuará de todos modos.")

        height, width = src.height, src.width
        scale = 1.0
        if height * width > max_pixels:
            scale = (max_pixels / (height * width)) ** 0.5
        out_shape = (max(1, int(height * scale)), max(1, int(width * scale)))

        elevacion = src.read(
            1,
            out_shape=out_shape,
            resampling=Resampling.average,
        ).astype(np.float32)
        elevacion = np.where(elevacion == src.nodata, np.nan, elevacion)

        ls = LightSource(azdeg=315, altdeg=45)
        shaded = ls.shade(elevacion, cmap=plt.cm.terrain, blend_mode="overlay")

        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(
            shaded,
            extent=(src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top),
            origin="upper",
        )
        ax.set_title("Modelo de Elevación con Hillshade", fontsize=14)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

        plt.tight_layout()

        salida = Path(ruta_salida) if ruta_salida else ruta.with_name(f"{ruta.stem}_hillshade.png")
        plt.savefig(salida, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"✅ Imagen guardada en: {salida}")


def _parse_args():
    parser = argparse.ArgumentParser(description="Genera hillshade desde un DEM en formato TIFF.")
    parser.add_argument("ruta", help="Ruta del archivo TIFF")
    parser.add_argument(
        "--salida",
        help="Ruta de salida de la imagen (png). Por defecto crea *_hillshade.png junto al TIFF.",
    )
    parser.add_argument(
        "--max-pixels",
        type=int,
        default=8_000_000,
        help="Número máximo de píxeles para reducir resolución y evitar problemas de memoria.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    visualizar_dem_con_hillshade(args.ruta, args.salida, args.max_pixels)
