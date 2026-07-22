import board
import busio
import adafruit_ssd1306

from PIL import Image, ImageDraw, ImageFont


class OLEDDisplay:
    def __init__(self, width=128, height=64, i2c_address=0x3C):
        self.width = int(width)
        self.height = int(height)
        self.i2c_address = i2c_address

        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.display = adafruit_ssd1306.SSD1306_I2C(
            self.width,
            self.height,
            self.i2c,
            addr=self.i2c_address,
        )

        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default()

        self.clear()

    def clear(self):
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        self._show()

    def _show(self):
        self.display.image(self.image)
        self.display.show()

    def show_lines(self, lines):
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        line_height = 10
        max_lines = self.height // line_height

        for index, line in enumerate(lines[:max_lines]):
            text = str(line)
            self.draw.text((0, index * line_height), text[:22], font=self.font, fill=255)

        self._show()

    def show_status(self, title, lines):
        output = [str(title)] + [str(line) for line in lines]
        self.show_lines(output)

    @staticmethod
    def _float_or_none(value):
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_delta(value):
        if value is None:
            return "--"
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:.1f}"

    def show_barograph(self, history, current_weather=None, config=None):
        """
        Zeichnet einen einfachen Barographen.

        history:
            Liste von 15-Minuten-Wetterpunkten mit pressure_hpa

        current_weather:
            laufender 1-Minuten-Mittelwert, nur für Textanzeige

        config:
            barograph-Konfiguration aus settings.yaml
        """
        config = config or {}
        current_weather = current_weather or {}

        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        points = []

        for row in history or []:
            pressure = self._float_or_none(row.get("pressure_hpa"))
            if pressure is not None:
                points.append(pressure)

        current_pressure = self._float_or_none(current_weather.get("pressure_hpa"))

        if not points and current_pressure is not None:
            points = [current_pressure]

        if not points:
            self.show_status("Barograph", ["Noch keine", "Wetterdaten"])
            return

        min_pressure = min(points)
        max_pressure = max(points)
        avg_pressure = sum(points) / len(points)

        delta_1h = None
        delta_3h = None
        delta_24h = None

        # Bei 15-Minuten-Punkten:
        # 1h = 4 Intervalle, also aktueller Punkt minus Punkt vor 4 Schritten.
        if len(points) >= 5:
            delta_1h = points[-1] - points[-5]
        if len(points) >= 13:
            delta_3h = points[-1] - points[-13]
        if len(points) >= 96:
            delta_24h = points[-1] - points[-96]

        display_pressure = current_pressure if current_pressure is not None else points[-1]

        midline_mode = config.get("midline_mode", "rolling_24h_mean")
        manual_reference = self._float_or_none(config.get("manual_reference_hpa"))
        gps_norm_reference = self._float_or_none(config.get("gps_norm_reference_hpa"))

        if midline_mode == "manual" and manual_reference is not None:
            center_pressure = manual_reference
            center_label = "M"
        elif midline_mode == "gps_norm_now" and gps_norm_reference is not None:
            center_pressure = gps_norm_reference
            center_label = "N"
        else:
            center_pressure = avg_pressure
            center_label = "Ø"

        min_display_range = float(config.get("min_display_range_hpa", 10))

        max_deviation = max(abs(value - center_pressure) for value in points)
        display_range = max(min_display_range, max_deviation * 2)

        # Etwas Luft, wenn Werte exakt am Rand liegen.
        display_range += 1.0

        low = center_pressure - display_range / 2
        high = center_pressure + display_range / 2

        # Header
        self.draw.text((0, 0), f"P {display_pressure:.1f}hPa", font=self.font, fill=255)
        self.draw.text(
            (0, 10),
            f"min {min_pressure:.0f} max {max_pressure:.0f}",
            font=self.font,
            fill=255,
        )

        # Graph-Bereich
        graph_x = 0
        graph_y = 23
        graph_w = min(96, self.width)
        graph_h = self.height - graph_y - 1

        if graph_h < 16:
            graph_h = max(8, self.height - graph_y - 1)

        # Mittellinie, bewusst statisch in der Displaymitte
        mid_y = graph_y + graph_h // 2
        for x in range(graph_x, graph_x + graph_w):
            if x % 2 == 0:
                self.draw.point((x, mid_y), fill=255)

        # Kleine Info rechts, falls Platz
        if self.width >= 120:
            right_x = 98
            self.draw.text((right_x, 23), f"{center_label}{center_pressure:.0f}", font=self.font, fill=255)
            self.draw.text((right_x, 34), f"1h{self._format_delta(delta_1h)}", font=self.font, fill=255)
            self.draw.text((right_x, 45), f"3h{self._format_delta(delta_3h)}", font=self.font, fill=255)

        values_to_draw = points[-graph_w:]

        for index, pressure in enumerate(values_to_draw):
            x = graph_x + index

            if high == low:
                y = mid_y
            else:
                ratio = (pressure - low) / (high - low)
                ratio = max(0.0, min(1.0, ratio))
                y = graph_y + graph_h - 1 - int(round(ratio * (graph_h - 1)))

            self.draw.point((x, y), fill=255)

        self._show()

    def sleep(self):
        """
        OLED strom-/einbrennschonend ausschalten.
        Das Bild im Speicher bleibt erhalten.
        """
        if hasattr(self.display, "poweroff"):
            self.display.poweroff()
        else:
            # Fallback: Bild löschen, falls poweroff nicht verfügbar ist.
            self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
            self._show()

    def wake(self):
        """
        OLED wieder einschalten und letztes Bild erneut anzeigen.
        """
        if hasattr(self.display, "poweron"):
            self.display.poweron()

        self._show()

    def close(self):
        self.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
