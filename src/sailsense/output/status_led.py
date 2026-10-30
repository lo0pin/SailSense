import time
from gpiozero import PWMLED


class StatusLED:
    """
    RGB-Status-LED für SailSense.

    Unterstützt common anode und common cathode.

    Common anode:
        gemeinsamer Pin an 3V3
        Farbpin -> Widerstand -> GPIO
        GPIO LOW = Farbe an

    Common cathode:
        gemeinsamer Pin an GND
        GPIO -> Widerstand -> Farbpin
        GPIO HIGH = Farbe an
    """

    COLORS = {
        "off": (0, 0, 0),
        "red": (1, 0, 0),
        "green": (0, 1, 0),
        "blue": (0, 0, 1),
        "yellow": (1, 1, 0),
        "cyan": (0, 1, 1),
        "magenta": (1, 0, 1),
        "white": (1, 1, 1),
    }

    def __init__(
        self,
        red_pin: int,
        green_pin: int,
        blue_pin: int,
        common: str = "anode",
        red_brightness: float = 1.0,
        green_brightness: float = 1.0,
        blue_brightness: float = 1.0,
    ):
        if common not in ("anode", "cathode"):
            raise ValueError("common muss 'anode' oder 'cathode' sein.")

        self.common = common

        # common anode: GPIO LOW schaltet ein
        active_high = common == "cathode"

        self.red_brightness = self._clamp(red_brightness)
        self.green_brightness = self._clamp(green_brightness)
        self.blue_brightness = self._clamp(blue_brightness)

        self.red = PWMLED(red_pin, active_high=active_high, initial_value=0)
        self.green = PWMLED(green_pin, active_high=active_high, initial_value=0)
        self.blue = PWMLED(blue_pin, active_high=active_high, initial_value=0)

        self.off()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def set_rgb(self, red: float, green: float, blue: float):
        self.red.value = self._clamp(red) * self.red_brightness
        self.green.value = self._clamp(green) * self.green_brightness
        self.blue.value = self._clamp(blue) * self.blue_brightness

    def set_color(self, color: str):
        color = color.lower()

        if color not in self.COLORS:
            raise ValueError(f"Unbekannte Farbe: {color}")

        red, green, blue = self.COLORS[color]
        self.set_rgb(red, green, blue)

    def off(self):
        self.set_rgb(0, 0, 0)

    def blink(self, color: str, times: int = 3, on_time: float = 0.2, off_time: float = 0.2):
        for _ in range(times):
            self.set_color(color)
            time.sleep(on_time)
            self.off()
            time.sleep(off_time)

    def close(self):
        self.off()
        self.red.close()
        self.green.close()
        self.blue.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
