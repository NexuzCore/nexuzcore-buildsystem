import json
from pathlib import Path

def load_config(config_file: str | Path) -> dict:
    config_file = Path(config_file)
    if not config_file.exists():
        raise FileNotFoundError(f"Config-Datei nicht gefunden: {config_file}")
    with open(config_file, "r") as f:
        return json.load(f)
