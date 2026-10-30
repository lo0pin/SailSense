from pathlib import Path
import yaml


PROJECT_ROOT = Path.home() / "sailsense"
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)
