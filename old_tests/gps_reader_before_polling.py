from datetime import datetime, timezone
from typing import Iterator, Optional

import serial
import pynmea2


class GPSReader:
    """
    Liest NMEA-Daten von einem GPS/GNSS-Empfänger und liefert
    strukturierte GPS-Datensätze auf Basis von RMC + GGA.
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None

        self.latest_gga = {
            "alt_m": None,
            "sats": None,
            "fix_quality": None,
            "hdop": None,
        }

    def __enter__(self):
        self.serial_connection = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.timeout,
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()

    @staticmethod
    def _to_float(value) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _timestamp_from_rmc(msg) -> str:
        """
        Baut aus RMC-Datum und RMC-Uhrzeit einen UTC-Zeitstempel.
        Falls das fehlschlägt, wird die aktuelle Systemzeit verwendet.
        """
        try:
            dt = datetime.combine(msg.datestamp, msg.timestamp)
            return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        except Exception:
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def read_points(self) -> Iterator[dict]:
        """
        Generator: liefert pro gültigem RMC-Satz einen GPS-Datensatz.
        """
        if self.serial_connection is None:
            raise RuntimeError("GPSReader muss mit 'with GPSReader(...) as gps:' verwendet werden.")

        while True:
            raw = self.serial_connection.readline().decode("ascii", errors="replace").strip()

            if not raw:
                continue

            try:
                msg = pynmea2.parse(raw)
            except pynmea2.ParseError:
                continue

            if msg.sentence_type == "GGA":
                self.latest_gga["alt_m"] = self._to_float(getattr(msg, "altitude", None))
                self.latest_gga["sats"] = getattr(msg, "num_sats", None)
                self.latest_gga["fix_quality"] = getattr(msg, "gps_qual", None)
                self.latest_gga["hdop"] = self._to_float(getattr(msg, "horizontal_dil", None))

            elif msg.sentence_type == "RMC":
                status = getattr(msg, "status", None)

                # A = active/valid, V = void/invalid
                if status != "A":
                    continue

                speed_kn = self._to_float(getattr(msg, "spd_over_grnd", None))
                speed_kmh = speed_kn * 1.852 if speed_kn is not None else None

                yield {
                    "timestamp_utc": self._timestamp_from_rmc(msg),
                    "lat": getattr(msg, "latitude", None),
                    "lon": getattr(msg, "longitude", None),
                    "speed_kn": speed_kn,
                    "speed_kmh": speed_kmh,
                    "course_deg": self._to_float(getattr(msg, "true_course", None)),
                    "alt_m": self.latest_gga["alt_m"],
                    "sats": self.latest_gga["sats"],
                    "fix_quality": self.latest_gga["fix_quality"],
                    "hdop": self.latest_gga["hdop"],
                }
