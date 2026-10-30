import time
import threading
import queue

from gpiozero import OutputDevice, PWMOutputDevice


class Buzzer:
    """
    Nicht-blockierender Buzzer/Summer für SailSense.

    kind="active":
        GPIO HIGH/LOW schaltet aktiven Buzzer ein/aus.
        Tonhöhe ist hardwareseitig fest.

    kind="passive":
        PWM-Signal für passiven Piezo.
        Tonhöhe wird über Frequenz gesteuert.
    """

    PATTERNS = {
        # bewusst sehr subtil
        "click": [(0.015, 0.0)],

        # kurze, freundliche Bestätigung
        "ok": [(0.035, 0.0)],

        # Marker: zwei sehr kurze Ticks
        "marker": [(0.030, 0.035), (0.030, 0.0)],

        # Trackstart: kurzer Doppelton, aber nicht laut/lang
        "track_start": [(0.045, 0.045), (0.070, 0.0)],

        # Trackstop: etwas tiefer/länger, aber ruhig
        "track_stop": [(0.080, 0.0)],

        # Warnung/Fehler hörbar, aber noch nicht Alarm
        "warning": [(0.070, 0.060), (0.070, 0.0)],
        "error": [(0.110, 0.070), (0.110, 0.0)],

        # ALARM bleibt absichtlich deutlich
        "alarm": [(0.300, 0.120), (0.300, 0.120), (0.300, 0.300)],
    }

    DEFAULT_FREQUENCIES = {
        "click": 2600,
        "ok": 2200,
        "marker": 3000,
        "track_start": 1800,
        "track_stop": 1200,
        "warning": 1600,
        "error": 900,
        "alarm": 2500,
    }

    def __init__(
        self,
        pin: int,
        kind: str = "active",
        active_high: bool = True,
        volume: float = 0.5,
        passive_frequency: int = 2000,
        frequencies: dict | None = None,
    ):
        if kind not in ("active", "passive"):
            raise ValueError("kind muss 'active' oder 'passive' sein.")

        self.pin = int(pin)
        self.kind = kind
        self.active_high = bool(active_high)
        self.volume = max(0.0, min(1.0, float(volume)))
        self.passive_frequency = int(passive_frequency)
        self.frequencies = dict(self.DEFAULT_FREQUENCIES)

        if frequencies:
            self.frequencies.update(frequencies)

        if self.kind == "active":
            self.device = OutputDevice(
                self.pin,
                active_high=self.active_high,
                initial_value=False,
            )
        else:
            self.device = PWMOutputDevice(
                self.pin,
                active_high=self.active_high,
                initial_value=0,
                frequency=self.passive_frequency,
            )

        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def _set_frequency(self, frequency: int | None):
        if self.kind != "passive":
            return

        if frequency is None:
            frequency = self.passive_frequency

        self.device.frequency = int(frequency)

    def _on(self):
        if self.kind == "active":
            self.device.on()
        else:
            self.device.value = self.volume

    def _off(self):
        if self.kind == "active":
            self.device.off()
        else:
            self.device.value = 0

    def _run(self):
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:
                continue

            pattern, frequency = item

            for on_time, off_time in pattern:
                if self._stop_event.is_set():
                    break

                self._set_frequency(frequency)
                self._on()
                time.sleep(max(0.0, float(on_time)))
                self._off()

                if off_time:
                    time.sleep(max(0.0, float(off_time)))

            self._queue.task_done()

    def play(self, name: str, frequency: int | None = None):
        pattern = self.PATTERNS.get(name)

        if pattern is None:
            raise ValueError(f"Unbekanntes Buzzer-Muster: {name}")

        if frequency is None:
            frequency = self.frequencies.get(name, self.passive_frequency)

        self._queue.put((pattern, frequency))

    def beep(self, seconds: float = 0.1, frequency: int | None = None):
        self._queue.put(([(seconds, 0.0)], frequency or self.passive_frequency))

    def off(self):
        self._off()

    def close(self):
        self._stop_event.set()
        self._queue.put(None)
        self._off()
        self.device.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
