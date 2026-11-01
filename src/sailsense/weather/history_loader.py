import csv
from pathlib import Path


def _clean_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_recent_weather_history(log_dir: str | Path, max_points: int = 96) -> list[dict]:
    """
    Lädt die letzten Wetterpunkte aus weather_15min-CSV-Dateien.

    Es werden nur Zeilen mit gültigem pressure_hpa übernommen.
    """
    log_dir = Path(log_dir)

    if not log_dir.exists():
        return []

    rows = []

    for path in sorted(log_dir.glob("*weather_15min.csv")):
        try:
            with path.open("r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row in reader:
                    pressure = _clean_float(row.get("pressure_hpa"))

                    if pressure is None:
                        continue

                    rows.append(row)

        except Exception:
            # Eine beschädigte Datei soll die App nicht töten.
            continue

    rows.sort(key=lambda row: row.get("timestamp_utc", ""))

    return rows[-max_points:]
