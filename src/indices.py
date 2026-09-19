import numpy as np

def calculate_ndbi(swir, nir):
    """
    Normalized Difference Built-up Index (NDBI)
    Hebt versiegelte, bebaute Flächen hervor.
    Sentinel-2: Band 11 (SWIR) und Band 8A (NIR)
    """
    # Verhindert Warnungen bei Division durch Null (NoData-Pixel)
    np.seterr(divide='ignore', invalid='ignore')
    
    ndbi = (swir - nir) / (swir + nir)
    
    # Wo NIR 0 ist (außerhalb des Bildes/Polygons), setzen wir NaN
    ndbi = np.where(nir == 0, np.nan, ndbi)
    
    return ndbi

def calculate_ndvi(nir, red):
    """
    Normalized Difference Vegetation Index (NDVI)
    Hebt vitale Vegetation hervor (kühlende Wirkung).
    Sentinel-2: Band 8 oder 8A (NIR) und Band 4 (Red)
    """
    np.seterr(divide='ignore', invalid='ignore')
    
    ndvi = (nir - red) / (nir + red)
    ndvi = np.where(red == 0, np.nan, ndvi)
    
    return ndvi