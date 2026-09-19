import yaml
from pathlib import Path

def load_config(config_path="config/config.yaml"):
    """Lädt die YAML-Konfigurationsdatei."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_file.resolve()}")
        
    with open(config_file, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
        
    return config