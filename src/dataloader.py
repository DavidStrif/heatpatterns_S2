import geopandas as gpd
import rasterio
from pathlib import Path
from src.config_parser import load_config

def load_project_data(config_path="config/config.yaml"):
    """
    Lädt die GeoJSON-Datei und das Sentinel-2 Bild basierend auf der Konfiguration.
    """
    config = load_config(config_path)
    
    # Pfade dynamisch zusammenbauen
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / config['paths']['data_dir']
    
    geojson_path = data_dir / config['paths']['aoi_file']
    raster_path = data_dir / config['paths']['sentinel_file']
    
    # Prüfen ob Daten existieren
    if not geojson_path.exists():
        raise FileNotFoundError(f"GeoJSON fehlt: {geojson_path}")
    if not raster_path.exists():
        raise FileNotFoundError(f"Sentinel-Datei fehlt: {raster_path}")
    
    # Daten laden
    aoi_gdf = gpd.read_file(geojson_path)
    s2_raster = rasterio.open(raster_path)
    
    print(f"Erfolgreich geladen:")
    print(f"- AOI: {len(aoi_gdf)} Geometrien, CRS: {aoi_gdf.crs}")
    print(f"- Sentinel-2: {s2_raster.count} Bänder, CRS: {s2_raster.crs}")
    
    return aoi_gdf, s2_raster

if __name__ == "__main__":
    # Testlauf
    aoi, raster = load_project_data()