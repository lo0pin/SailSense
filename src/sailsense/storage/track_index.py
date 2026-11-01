import csv
from pathlib import Path
from datetime import datetime


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _short_time(timestamp_utc: str) -> str:
    """
    Aus 2026-06-26T14:17:20Z wird 26.06 14:17
    """
    value = _clean(timestamp_utc)

    if not value:
        return "--.-- --:--"

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d.%m %H:%M")
    except ValueError:
        return value[:11]


def load_tracks_index(index_file: str | Path, limit: int = 20) -> list[dict]:
    index_file = Path(index_file)

    if not index_file.exists():
        return []

    rows = []

    try:
        with index_file.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                if _clean(row.get("track_id")):
                    rows.append(row)

    except Exception:
        return []

    rows.sort(key=lambda row: _clean(row.get("start_time_utc")))

    # Neueste zuerst
    rows = list(reversed(rows))

    return rows[:limit]


def format_track_summary(row: dict, selected: bool = False) -> str:
    cursor = ">" if selected else " "
    start = _short_time(row.get("start_time_utc"))
    distance_nm = _safe_float(row.get("distance_nm"))

    # Möglichst kurz für 128x64
    return f"{cursor}{start} {distance_nm:.2f}nm"


def format_track_detail_lines(row: dict, index: int, total: int) -> list[str]:
    start = _short_time(row.get("start_time_utc"))
    duration = _clean(row.get("duration_text")) or "--"
    distance_nm = _safe_float(row.get("distance_nm"))
    distance_km = _safe_float(row.get("distance_km"))
    points = _clean(row.get("point_count")) or "0"
    mode = _clean(row.get("mode")) or "--"

    return [
        f"{index + 1}/{total} {start}",
        f"Mode: {mode}",
        f"Dauer: {duration}",
        f"Dist: {distance_nm:.3f}nm",
        f"{distance_km:.3f}km {points}pts",
        "BACK: zurueck",
    ]
