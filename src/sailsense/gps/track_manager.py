import csv
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sailsense.gps.distance import haversine_m, meters_to_km, meters_to_nm


TRACK_FIELDNAMES = [
    "track_id",
    "timestamp_utc",
    "lat",
    "lon",
    "speed_kn",
    "speed_kmh",
    "course_deg",
    "alt_m",
    "sats",
    "fix_quality",
    "hdop",
    "distance_from_previous_m",
    "distance_total_m",
    "distance_total_nm",
    "marker",
]

TRACK_INDEX_FIELDNAMES = [
    "track_id",
    "mode",
    "start_time_utc",
    "end_time_utc",
    "duration_seconds",
    "duration_text",
    "distance_m",
    "distance_nm",
    "distance_km",
    "point_count",
    "start_lat",
    "start_lon",
    "end_lat",
    "end_lon",
    "track_file",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def make_track_id() -> str:
    return utc_now().strftime("track_%Y%m%d_%H%M%S")


def duration_text(seconds: float) -> str:
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


@dataclass
class TrackStats:
    track_id: str
    mode: str = "manual"
    start_time_utc: str = field(default_factory=utc_now_iso)
    end_time_utc: Optional[str] = None
    start_monotonic: float = field(default_factory=time.monotonic)
    end_monotonic: Optional[float] = None
    distance_m: float = 0.0
    point_count: int = 0
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None

    @property
    def duration_seconds(self) -> float:
        end = self.end_monotonic if self.end_monotonic is not None else time.monotonic()
        return max(0.0, end - self.start_monotonic)

    @property
    def distance_nm(self) -> float:
        return meters_to_nm(self.distance_m)

    @property
    def distance_km(self) -> float:
        return meters_to_km(self.distance_m)


class TrackManager:
    """
    Manuelle GPS-Track-Session.

    start():
        neuer Track mit eigener CSV-Datei

    add_point(point):
        speichert höchstens alle point_interval_seconds einen GPS-Punkt

    stop():
        beendet Track und schreibt tracks_index.csv
    """

    def __init__(
        self,
        log_dir: str | Path,
        index_file: str | Path,
        point_interval_seconds: float = 5,
        min_sats: int = 5,
        max_hdop: float = 5.0,
    ):
        self.log_dir = Path(log_dir)
        self.index_file = Path(index_file)
        self.point_interval_seconds = float(point_interval_seconds)
        self.min_sats = int(min_sats)
        self.max_hdop = float(max_hdop)

        self.active = False
        self.stats: Optional[TrackStats] = None
        self.track_file: Optional[Path] = None
        self.file_handle = None
        self.writer = None

        self.last_point = None
        self.last_write_monotonic = 0.0
        self.pending_marker = None

        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.index_file.parent.mkdir(parents=True, exist_ok=True)

    def start(self, mode: str = "manual") -> TrackStats:
        if self.active:
            raise RuntimeError("Track läuft bereits.")

        track_id = make_track_id()
        self.track_file = self.log_dir / f"{track_id}.csv"

        self.file_handle = self.track_file.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file_handle, fieldnames=TRACK_FIELDNAMES)
        self.writer.writeheader()
        self.file_handle.flush()

        self.stats = TrackStats(track_id=track_id, mode=mode)
        self.active = True
        self.last_point = None
        self.last_write_monotonic = 0.0
        self.pending_marker = None

        return self.stats

    def stop(self) -> Optional[TrackStats]:
        if not self.active or self.stats is None:
            return None

        self.stats.end_time_utc = utc_now_iso()
        self.stats.end_monotonic = time.monotonic()

        if self.file_handle:
            self.file_handle.flush()
            self.file_handle.close()

        self._write_index_row()

        finished = self.stats

        self.active = False
        self.stats = None
        self.track_file = None
        self.file_handle = None
        self.writer = None
        self.last_point = None
        self.last_write_monotonic = 0.0
        self.pending_marker = None

        return finished

    def set_marker(self, marker: str):
        self.pending_marker = marker

    def add_point(self, point: dict, force: bool = False) -> bool:
        if not self.active or self.stats is None or self.writer is None:
            return False

        if not self._point_quality_ok(point):
            return False

        now = time.monotonic()

        if (
            not force
            and self.last_write_monotonic
            and now - self.last_write_monotonic < self.point_interval_seconds
        ):
            return False

        lat = point.get("lat")
        lon = point.get("lon")

        if lat is None or lon is None:
            return False

        distance_from_previous = 0.0

        if self.last_point is not None:
            distance_from_previous = haversine_m(
                self.last_point.get("lat"),
                self.last_point.get("lon"),
                lat,
                lon,
            )

            # Grobe Filterung gegen GPS-Ausreißer:
            # Einzelne Sprünge über 500 m werden ignoriert.
            if distance_from_previous > 500:
                return False

            self.stats.distance_m += distance_from_previous
        else:
            self.stats.start_lat = lat
            self.stats.start_lon = lon

        self.stats.end_lat = lat
        self.stats.end_lon = lon
        self.stats.point_count += 1

        row = {
            "track_id": self.stats.track_id,
            "timestamp_utc": point.get("timestamp_utc"),
            "lat": lat,
            "lon": lon,
            "speed_kn": point.get("speed_kn"),
            "speed_kmh": point.get("speed_kmh"),
            "course_deg": point.get("course_deg"),
            "alt_m": point.get("alt_m"),
            "sats": point.get("sats"),
            "fix_quality": point.get("fix_quality"),
            "hdop": point.get("hdop"),
            "distance_from_previous_m": round(distance_from_previous, 2),
            "distance_total_m": round(self.stats.distance_m, 2),
            "distance_total_nm": round(self.stats.distance_nm, 4),
            "marker": self.pending_marker,
        }

        self.writer.writerow(row)
        self.file_handle.flush()

        self.pending_marker = None
        self.last_point = point
        self.last_write_monotonic = now

        return True

    def get_status(self) -> dict:
        if not self.active or self.stats is None:
            return {
                "active": False,
                "track_id": None,
                "duration_text": "0s",
                "distance_nm": 0.0,
                "distance_km": 0.0,
                "point_count": 0,
            }

        return {
            "active": True,
            "track_id": self.stats.track_id,
            "duration_text": duration_text(self.stats.duration_seconds),
            "distance_nm": self.stats.distance_nm,
            "distance_km": self.stats.distance_km,
            "point_count": self.stats.point_count,
        }

    def _point_quality_ok(self, point: dict) -> bool:
        sats = point.get("sats")
        hdop = point.get("hdop")

        try:
            sats_ok = sats is not None and int(sats) >= self.min_sats
        except (TypeError, ValueError):
            sats_ok = False

        try:
            hdop_ok = hdop is not None and float(hdop) <= self.max_hdop
        except (TypeError, ValueError):
            # Wenn HDOP fehlt, erlauben wir den Punkt vorerst.
            hdop_ok = True

        return sats_ok and hdop_ok

    def _write_index_row(self):
        assert self.stats is not None
        assert self.track_file is not None

        file_exists = self.index_file.exists()

        row = {
            "track_id": self.stats.track_id,
            "mode": self.stats.mode,
            "start_time_utc": self.stats.start_time_utc,
            "end_time_utc": self.stats.end_time_utc,
            "duration_seconds": round(self.stats.duration_seconds, 1),
            "duration_text": duration_text(self.stats.duration_seconds),
            "distance_m": round(self.stats.distance_m, 2),
            "distance_nm": round(self.stats.distance_nm, 4),
            "distance_km": round(self.stats.distance_km, 4),
            "point_count": self.stats.point_count,
            "start_lat": self.stats.start_lat,
            "start_lon": self.stats.start_lon,
            "end_lat": self.stats.end_lat,
            "end_lon": self.stats.end_lon,
            "track_file": str(self.track_file),
        }

        with self.index_file.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=TRACK_INDEX_FIELDNAMES)

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)
