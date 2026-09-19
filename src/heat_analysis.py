import zipfile
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Lokale Module importieren
from config_parser import load_config
from indices import calculate_ndbi, calculate_ndvi

def find_band_in_zip(zip_path, band_suffix):
    """Sucht die richtige .jp2 Datei im ZIP-Archiv."""
    with zipfile.ZipFile(zip_path, 'r') as z:
        for file_info in z.namelist():
            if file_info.endswith(band_suffix):
                return file_info
    raise FileNotFoundError(f"Band mit Suffix {band_suffix} nicht gefunden.")

def load_and_mask_band(zip_path, band_suffix, geometries):
    """Findet ein Band, schneidet es zu und gibt Array sowie Metadaten (Profile) zurück."""
    internal_path = find_band_in_zip(zip_path, band_suffix)
    uri = f"zip+file://{zip_path}!/{internal_path}"
    
    with rasterio.open(uri) as src:
        out_image, out_transform = mask(src, geometries, crop=True)
        
        # Metadaten (Profile) für den GeoTIFF-Export anpassen
        profile = src.profile
        profile.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "dtype": 'float32',
            "nodata": np.nan
        })
        
        return out_image[0].astype('float32'), profile

def save_geotiff(output_path, array_2d, profile):
    """Speichert ein 2D-NumPy-Array als georeferenzierte GeoTIFF-Datei."""
    array_3d = np.expand_dims(array_2d, axis=0) # Rasterio braucht 3 Dimensionen
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(array_3d)
    print(f"Gespeichert: {output_path}")

def process_urban_heat():
    # 1. Pfade und Setup
    config = load_config()
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / config['paths']['data_dir']
    
    # Output-Ordner dynamisch erstellen, falls nicht vorhanden
    output_dir = base_dir / config['paths']['output_dir']
    output_dir.mkdir(parents=True, exist_ok=True)
    
    zip_path = data_dir / config['paths']['sentinel_file']
    geojson_path = data_dir / config['paths']['aoi_file']
    
    th_ndbi = config['thresholds']['ndbi_heat_min']
    th_ndvi = config['thresholds']['ndvi_heat_max']

    # 2. GeoJSON laden und an S2-Koordinatensystem anpassen
    print("Lade Vektordaten...")
    aoi_gdf = gpd.read_file(geojson_path)
    
    temp_path = find_band_in_zip(zip_path, 'B04_10m.jp2')
    with rasterio.open(f"zip+file://{zip_path}!/{temp_path}") as src:
        aoi_gdf = aoi_gdf.to_crs(src.crs)
        geometries = [geom for geom in aoi_gdf.geometry]

    # 3. Satelliten-Bänder laden und zuschneiden
    print("Lade und schneide 10m Bänder (NDVI)...")
    red_10m, profile_10m = load_and_mask_band(zip_path, 'B04_10m.jp2', geometries)
    nir_10m, _ = load_and_mask_band(zip_path, 'B08_10m.jp2', geometries)
    
    print("Lade und schneide 20m Bänder (NDBI)...")
    nir_20m, profile_20m = load_and_mask_band(zip_path, 'B8A_20m.jp2', geometries)
    swir_20m, _ = load_and_mask_band(zip_path, 'B11_20m.jp2', geometries)

    # 4. Indizes berechnen
    print("Berechne Indizes...")
    ndvi = calculate_ndvi(nir_10m, red_10m)
    ndbi = calculate_ndbi(swir_20m, nir_20m)

    # 5. GeoTIFFs exportieren
    print("Speichere GeoTIFFs...")
    save_geotiff(output_dir / "ndvi_result.tif", ndvi, profile_10m)
    save_geotiff(output_dir / "ndbi_result.tif", ndbi, profile_20m)

    # 6. Visualisierung (Karten & Histogramme)
    print("Erstelle Visualisierungen...")
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # --- Reihe 1: NDBI (Versiegelung) ---
    ax_ndbi_map, ax_ndbi_hist = axes[0]
    
    cmap_ndbi = plt.get_cmap('coolwarm').copy()
    cmap_ndbi.set_bad('white', 1.)
    im_ndbi = ax_ndbi_map.imshow(ndbi, cmap=cmap_ndbi, vmin=-0.5, vmax=0.5)
    ax_ndbi_map.contour(ndbi, levels=[th_ndbi], colors='yellow', linewidths=1.5)
    ax_ndbi_map.set_title(f"NDBI (20m) - Versiegelung > {th_ndbi}")
    ax_ndbi_map.axis('off')
    fig.colorbar(im_ndbi, ax=ax_ndbi_map, fraction=0.046, pad=0.04)

    valid_ndbi = ndbi[~np.isnan(ndbi)]
    n, bins, patches = ax_ndbi_hist.hist(valid_ndbi, bins=50, color='gray', edgecolor='black')
    ax_ndbi_hist.axvline(th_ndbi, color='red', linestyle='dashed', linewidth=2)
    for i in range(len(patches)):
        if bins[i] >= th_ndbi: patches[i].set_facecolor('red')
    ax_ndbi_hist.set_title("NDBI Verteilung (Hitze-Cluster rot)")

    # --- Reihe 2: NDVI (Vegetation) ---
    ax_ndvi_map, ax_ndvi_hist = axes[1]
    
    cmap_ndvi = plt.get_cmap('RdYlGn').copy()
    cmap_ndvi.set_bad('white', 1.)
    im_ndvi = ax_ndvi_map.imshow(ndvi, cmap=cmap_ndvi, vmin=-0.2, vmax=0.8)
    ax_ndvi_map.contour(ndvi, levels=[th_ndvi], colors='blue', linewidths=1.5)
    ax_ndvi_map.set_title(f"NDVI (10m) - Fehlende Veg. < {th_ndvi}")
    ax_ndvi_map.axis('off')
    fig.colorbar(im_ndvi, ax=ax_ndvi_map, fraction=0.046, pad=0.04)

    valid_ndvi = ndvi[~np.isnan(ndvi)]
    n, bins, patches = ax_ndvi_hist.hist(valid_ndvi, bins=50, color='gray', edgecolor='black')
    ax_ndvi_hist.axvline(th_ndvi, color='blue', linestyle='dashed', linewidth=2)
    for i in range(len(patches)):
        if bins[i] <= th_ndvi: patches[i].set_facecolor('red')
    ax_ndvi_hist.set_title("NDVI Verteilung (Hitze-Cluster rot)")

    plt.tight_layout()
    
    # Plot als Bild speichern (muss VOR plt.show() passieren!)
    plot_path = output_dir / "heat_analysis_dashboard.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Gespeichert: {plot_path}")
    
   # plt.show()

if __name__ == "__main__":
    process_urban_heat()