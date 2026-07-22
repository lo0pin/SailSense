from __future__ import annotations

import math
import time
from dataclasses import dataclass


EARTH_RADIUS_M = 6371000.0


def _get(point, *names, default=None):
    if point is None:
        return default

    if isinstance(point, dict):
        for name in names:
            if name in point:
                return point.get(name)

    for name in names:
        if hasattr(point, name):
            return getattr(point, name)

    return default


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def haversine_m(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c


@dataclass
class AnchorFix:
    lat: float
    lon: float
    sats: int | None = None
    hdop: float | None = None
    speed_kn: float | None = None
    timestamp: float = 0.0


class AnchorWatch:
    """
    Ankerwache mit getrennten Zonen:

      radius_m:
        eigentlicher Schwojkreis / Kettenradius ab Drop-Punkt

      radius_m * warn_ratio:
        gelbe optische Warnung

      radius_m * danger_ratio:
        rot/blau optische Warnung

      radius_m + buffer_m:
        akustischer Alarm erst nach Zeit + Punkten außerhalb

    Modi:
      OFF
      DROP_SET
      ACTIVE
      ALARM
      STOP_CONFIRM
      EDIT_RADIUS
      EDIT_BUFFER
    """

    def __init__(
        self,
        radius_m=None,
        buffer_m=10.0,
        min_radius_m=20.0,
        warn_ratio=0.90,
        danger_ratio=1.00,
        required_outside_seconds=30.0,
        required_outside_points=5,
        min_sats=5,
        max_hdop=5.0,
        alarm_repeat_seconds=3.0,
        radius_step_m=5.0,
        buffer_step_m=1.0,
    ):
        self.configured_radius_m = _float_or_none(radius_m)

        self.buffer_m = float(buffer_m)
        self.min_radius_m = float(min_radius_m)
        self.warn_ratio = float(warn_ratio)
        self.danger_ratio = float(danger_ratio)

        self.required_outside_seconds = float(required_outside_seconds)
        self.required_outside_points = int(required_outside_points)

        self.min_sats = int(min_sats)
        self.max_hdop = float(max_hdop)

        self.alarm_repeat_seconds = float(alarm_repeat_seconds)
        self.radius_step_m = float(radius_step_m)
        self.buffer_step_m = float(buffer_step_m)

        self.mode = "OFF"
        self.previous_mode = "OFF"

        self.drop_fix: AnchorFix | None = None
        self.last_fix: AnchorFix | None = None

        # Ungepufferter Radius.
        self.radius_m: float | None = self.configured_radius_m

        self.last_distance_m: float | None = None
        self.last_ratio: float | None = None
        self.zone = "off"

        self.outside_since: float | None = None
        self.outside_points = 0
        self.last_alarm_sound = 0.0
        self.last_message = "bereit"

    @classmethod
    def from_config(cls, config):
        config = config or {}

        return cls(
            radius_m=config.get("radius_m"),
            buffer_m=config.get("buffer_m", 10.0),
            min_radius_m=config.get("min_radius_m", 20.0),
            warn_ratio=config.get("warn_ratio", 0.90),
            danger_ratio=config.get("danger_ratio", 1.00),
            required_outside_seconds=config.get("required_outside_seconds", 30.0),
            required_outside_points=config.get("required_outside_points", 5),
            min_sats=config.get("min_sats", 5),
            max_hdop=config.get("max_hdop", 5.0),
            alarm_repeat_seconds=config.get("alarm_repeat_seconds", 3.0),
            radius_step_m=config.get("radius_step_m", 5.0),
            buffer_step_m=config.get("buffer_step_m", 1.0),
        )

    @property
    def is_active(self):
        return self.mode in ("ACTIVE", "ALARM")

    @property
    def alarm_active(self):
        return self.mode == "ALARM"

    @property
    def alarm_radius_m(self):
        if self.radius_m is None:
            return None

        return self.radius_m + self.buffer_m

    def _fix_from_point(self, point):
        lat = _float_or_none(_get(point, "lat", "latitude"))
        lon = _float_or_none(_get(point, "lon", "lng", "longitude"))

        if lat is None or lon is None:
            return None

        sats = _int_or_none(_get(point, "sats", "satellites", "num_sats"))
        hdop = _float_or_none(_get(point, "hdop"))
        speed_kn = _float_or_none(
            _get(point, "speed_kn", "speed", "speed_knots")
        )

        timestamp = _float_or_none(_get(point, "timestamp", "time"))
        if timestamp is None:
            timestamp = time.time()

        return AnchorFix(
            lat=lat,
            lon=lon,
            sats=sats,
            hdop=hdop,
            speed_kn=speed_kn,
            timestamp=timestamp,
        )

    def _fix_quality_ok(self, fix):
        if fix is None:
            self.last_message = "kein GPS"
            return False

        if fix.sats is not None and fix.sats < self.min_sats:
            self.last_message = f"GPS schwach {fix.sats}s"
            return False

        if fix.hdop is not None and fix.hdop > self.max_hdop:
            self.last_message = f"HDOP {fix.hdop:.1f}"
            return False

        return True

    def set_drop(self, point):
        fix = self._fix_from_point(point)

        if not self._fix_quality_ok(fix):
            return False

        self.drop_fix = fix
        self.last_fix = fix
        self.last_distance_m = None
        self.last_ratio = None
        self.zone = "drop"
        self.outside_since = None
        self.outside_points = 0
        self.mode = "DROP_SET"
        self.last_message = "Drop gesetzt"
        return True

    def set_radius_from_current_position(self, point):
        if self.drop_fix is None:
            self.last_message = "kein Drop"
            return False

        fix = self._fix_from_point(point)

        if not self._fix_quality_ok(fix):
            return False

        distance = haversine_m(
            self.drop_fix.lat,
            self.drop_fix.lon,
            fix.lat,
            fix.lon,
        )

        self.last_fix = fix
        self.last_distance_m = distance
        self.radius_m = max(self.min_radius_m, distance)
        self.configured_radius_m = self.radius_m
        self.last_ratio = distance / self.radius_m if self.radius_m > 0 else None

        self.outside_since = None
        self.outside_points = 0
        self.zone = "inside"
        self.mode = "ACTIVE"
        self.last_message = "Wache aktiv"
        return True

    def stop(self):
        self.mode = "OFF"
        self.previous_mode = "OFF"
        self.drop_fix = None
        self.last_fix = None
        self.last_distance_m = None
        self.last_ratio = None
        self.zone = "off"
        self.outside_since = None
        self.outside_points = 0
        self.last_alarm_sound = 0.0
        self.last_message = "gestoppt"

    def enter_stop_confirm(self):
        if self.mode in ("ACTIVE", "ALARM", "DROP_SET"):
            self.previous_mode = self.mode
            self.mode = "STOP_CONFIRM"
            self.last_message = "Stop?"

    def cancel_stop_confirm(self):
        if self.mode == "STOP_CONFIRM":
            self.mode = self.previous_mode
            self.last_message = "laeuft"

    def enter_radius_edit(self):
        if self.radius_m is None:
            self.radius_m = self.min_radius_m

        self.previous_mode = self.mode
        self.mode = "EDIT_RADIUS"

    def enter_buffer_edit(self):
        self.previous_mode = self.mode
        self.mode = "EDIT_BUFFER"

    def finish_edit(self):
        if self.mode in ("EDIT_RADIUS", "EDIT_BUFFER"):
            self.mode = self.previous_mode if self.previous_mode else "ACTIVE"
            self.last_message = "gespeichert"

    def cancel_edit(self):
        self.finish_edit()

    def adjust_radius(self, direction):
        if self.radius_m is None:
            self.radius_m = self.min_radius_m

        self.radius_m += direction * self.radius_step_m
        self.radius_m = max(self.min_radius_m, self.radius_m)
        self.configured_radius_m = self.radius_m

    def adjust_buffer(self, direction):
        self.buffer_m += direction * self.buffer_step_m
        self.buffer_m = max(0.0, self.buffer_m)

    def update(self, point, now=None):
        now = time.monotonic() if now is None else float(now)

        if self.mode not in ("ACTIVE", "ALARM"):
            return None

        if self.drop_fix is None or self.radius_m is None:
            self.mode = "OFF"
            self.zone = "off"
            self.last_message = "ungueltig"
            return "stopped"

        fix = self._fix_from_point(point)

        if not self._fix_quality_ok(fix):
            return None

        self.last_fix = fix
        distance = haversine_m(
            self.drop_fix.lat,
            self.drop_fix.lon,
            fix.lat,
            fix.lon,
        )

        self.last_distance_m = distance
        self.last_ratio = distance / self.radius_m if self.radius_m > 0 else None

        alarm_radius = self.radius_m + self.buffer_m

        if distance >= alarm_radius:
            zone = "outside_buffer"
        elif distance >= self.radius_m * self.danger_ratio:
            zone = "danger"
        elif distance >= self.radius_m * self.warn_ratio:
            zone = "warning"
        else:
            zone = "inside"

        old_zone = self.zone
        self.zone = zone

        if distance >= alarm_radius:
            if self.outside_since is None:
                self.outside_since = now
                self.outside_points = 1
            else:
                self.outside_points += 1

            outside_seconds = now - self.outside_since

            if (
                self.mode != "ALARM"
                and outside_seconds >= self.required_outside_seconds
                and self.outside_points >= self.required_outside_points
            ):
                self.mode = "ALARM"
                self.last_message = "ALARM ausserhalb"
                return "alarm_start"

            self.last_message = "ausserhalb+puffer"
            return "outside_buffer"

        self.outside_since = None
        self.outside_points = 0

        if self.mode != "ALARM":
            if zone == "danger":
                self.last_message = "Kette voll"
            elif zone == "warning":
                self.last_message = "Kette spannt"
            else:
                self.last_message = "innerhalb"

        if zone != old_zone:
            return f"zone_{zone}"

        return zone

    def alarm_sound_due(self, now=None):
        now = time.monotonic() if now is None else float(now)

        if self.mode != "ALARM":
            return False

        if now - self.last_alarm_sound >= self.alarm_repeat_seconds:
            self.last_alarm_sound = now
            return True

        return False

    def status_lines(self):
        if self.mode == "OFF":
            return [
                "Status: aus",
                "OK: Drop setzen",
                "BACK: zurueck",
            ]

        if self.mode == "DROP_SET":
            return [
                "Drop gesetzt",
                "Boot zuruecktreiben",
                "Kette auf Zug",
                "OK: Radius setzen",
                "BACK: abbrechen",
            ]

        if self.mode == "STOP_CONFIRM":
            return [
                "Ankerwache stoppen?",
                "OK: stoppen",
                "BACK: weiter",
            ]

        if self.mode == "EDIT_RADIUS":
            radius = "--" if self.radius_m is None else f"{self.radius_m:.0f}m"
            return [
                "Radius einstellen",
                f"Radius: {radius}",
                "UP/DOWN +/-",
                "OK: speichern",
                "BACK: fertig",
            ]

        if self.mode == "EDIT_BUFFER":
            return [
                "Puffer einstellen",
                f"Puffer: {self.buffer_m:.0f}m",
                "UP/DOWN +/-",
                "OK: speichern",
                "BACK: fertig",
            ]

        dist = "--"
        radius = "--"
        alarm_radius = "--"
        ratio = "--"

        if self.last_distance_m is not None:
            dist = f"{self.last_distance_m:.0f}m"

        if self.radius_m is not None:
            radius = f"{self.radius_m:.0f}m"

        if self.alarm_radius_m is not None:
            alarm_radius = f"{self.alarm_radius_m:.0f}m"

        if self.last_ratio is not None:
            ratio = f"{self.last_ratio * 100:.0f}%"

        if self.mode == "ALARM":
            title = "ALARM"
        else:
            title = "aktiv"

        return [
            f"Status: {title}",
            f"Dist: {dist} {ratio}",
            f"Radius: {radius}",
            f"Alarm: {alarm_radius}",
            self.last_message[:21],
            "OK Stop UP/DN Edit",
        ]


def save_anchor_runtime_settings(watch, path="/home/user/sailsense/config/settings.yaml"):
    """
    Speichert Radius und Puffer dauerhaft in config/settings.yaml.
    """
    if watch is None:
        return

    from pathlib import Path
    import yaml

    settings_path = Path(path)
    data = yaml.safe_load(settings_path.read_text()) or {}

    anchor = data.setdefault("anchor_watch", {})

    if watch.radius_m is not None:
        anchor["radius_m"] = float(watch.radius_m)

    anchor["buffer_m"] = float(watch.buffer_m)
    anchor["radius_step_m"] = float(watch.radius_step_m)
    anchor["buffer_step_m"] = float(watch.buffer_step_m)

    settings_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    )
