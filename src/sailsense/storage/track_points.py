import csv
import math
from pathlib import Path


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_track_points(track_file: str | Path, max_points: int = 800) -> list[dict]:
    """
    Lädt GPS-Punkte aus einer SailSense-Track-CSV.

    Gibt eine Liste zurück:
      [{"lat": ..., "lon": ...}, ...]

    Bei sehr langen Tracks wird ausgedünnt, damit das OLED nicht unnötig
    tausende Punkte zeichnen muss.
    """
    track_file = Path(track_file)

    if not track_file.exists():
        return []

    points = []

    with track_file.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            lat = _safe_float(row.get("lat"))
            lon = _safe_float(row.get("lon"))

            if lat is None or lon is None:
                continue

            points.append(
                {
                    "lat": lat,
                    "lon": lon,
                }
            )

    if max_points and len(points) > max_points:
        step = max(1, math.ceil(len(points) / max_points))
        reduced = points[::step]

        if reduced[-1] != points[-1]:
            reduced.append(points[-1])

        points = reduced

    return points
