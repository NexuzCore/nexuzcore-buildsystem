import json

from pathlib import Path

from core.logger import success, info, warning, error


def load_config(config_file: str | Path) -> dict:
    """_summary_

    Args:
        config_file (str | Path): _description_

    Raises:
        FileNotFoundError: _description_

    Returns:
        dict: _description_
    """
    
    
    config_file = Path(config_file)
    if not config_file.exists():
        raise FileNotFoundError(f"Config-Datei nicht gefunden: {config_file}")
    with open(config_file, "r") as f:
        return json.load(f)
