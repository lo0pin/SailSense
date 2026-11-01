import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional


WEATHER_FIELDNAMES = [
    "timestamp_utc",
    "window_start_utc",
    "window_seconds",
    "sample_count",
    "temp_c",
    "humidity_pct",
    "pressure_hpa",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def average_weather(samples: list[dict]) -> Optional[dict]:
    if not samples:
        return None

    result = {}

    for key in ["temp_c", "humidity_pct", "pressure_hpa"]:
        values = [
            sample[key]
            for sample in samples
            if sample.get(key) is not None
        ]

        result[key] = round(sum(values) / len(values), 2) if values else None

    return result


class WeatherService:
    """
    Dauerlaufender Wetterdienst für SailSense.

    - liest Rohwerte in festem Intervall
    - bildet 1-Minuten-Mittelwert für Anzeige/App
    - schreibt 15-Minuten-Mittelwert in CSV
    - hält 24h-History aus gespeicherten Mittelwerten
    """

    def __init__(
        self,
        bme_reader,
        csv_logger,
        raw_read_interval_seconds: float = 10,
        display_average_seconds: float = 60,
        storage_interval_seconds: float = 900,
        history_points: int = 96,
    ):
        self.bme_reader = bme_reader
        self.csv_logger = csv_logger

        self.raw_read_interval_seconds = raw_read_interval_seconds
        self.display_average_seconds = display_average_seconds
        self.storage_interval_seconds = storage_interval_seconds

        self.raw_samples = deque()
        self.storage_samples = []
        self.history = deque(maxlen=history_points)

        self.current_average = None

        self.last_raw_read_monotonic = 0.0
        self.last_storage_write_monotonic = time.monotonic()
        self.storage_window_start_utc = utc_now_iso()

    def tick(self, force_read: bool = False, force_store: bool = False) -> Optional[dict]:
        """
        Wird regelmäßig aus der App aufgerufen.
        Liest nur dann wirklich vom Sensor, wenn das Rohintervall erreicht ist.
        """

        now = time.monotonic()

        should_read = (
            force_read
            or self.last_raw_read_monotonic == 0.0
            or now - self.last_raw_read_monotonic >= self.raw_read_interval_seconds
        )

        if should_read:
            sample = self.bme_reader.read()
            sample["_monotonic"] = now

            self.raw_samples.append(sample)
            self.storage_samples.append(sample)
            self.last_raw_read_monotonic = now

            self._prune_raw_samples(now)
            self.current_average = self._build_display_average()

        should_store = (
            force_store
            or now - self.last_storage_write_monotonic >= self.storage_interval_seconds
        )

        if should_store:
            self._store_average(now)

        return self.current_average

    def _prune_raw_samples(self, now: float):
        while self.raw_samples:
            oldest = self.raw_samples[0]
            age = now - oldest["_monotonic"]

            if age <= self.display_average_seconds:
                break

            self.raw_samples.popleft()

    def _build_display_average(self) -> Optional[dict]:
        samples = list(self.raw_samples)
        avg = average_weather(samples)

        if avg is None:
            return None

        avg.update(
            {
                "timestamp_utc": utc_now_iso(),
                "sample_count": len(samples),
                "window_seconds": self.display_average_seconds,
            }
        )

        return avg

    def _store_average(self, now: float):
        avg = average_weather(self.storage_samples)

        if avg is None:
            return

        row = {
            "timestamp_utc": utc_now_iso(),
            "window_start_utc": self.storage_window_start_utc,
            "window_seconds": round(now - self.last_storage_write_monotonic, 1),
            "sample_count": len(self.storage_samples),
            "temp_c": avg["temp_c"],
            "humidity_pct": avg["humidity_pct"],
            "pressure_hpa": avg["pressure_hpa"],
        }

        self.csv_logger.write_row(row)
        self.history.append(row)

        self.storage_samples = []
        self.storage_window_start_utc = row["timestamp_utc"]
        self.last_storage_write_monotonic = now

    def get_current_average(self) -> Optional[dict]:
        return self.current_average

    def get_history(self) -> list[dict]:
        return list(self.history)
