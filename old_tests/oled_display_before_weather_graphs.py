import board
import busio
import adafruit_ssd1306
import math

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
        Zeichnet einen kompakten SailSense-Barographen.

        Layout 128x64:
          Zeile 1: aktueller Druck + min/max
          Zeile 2: 1h/3h-Trend + Skalenbereich + Trend
          darunter: 24h-Barograph mit 96 Punkten
          rechts: Skalenwerte / Mittellinie

        1 gespeicherter 15-Minuten-Wert = 1 Pixel.
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

        display_pressure = current_pressure if current_pressure is not None else points[-1]

        def delta(intervals):
            if len(points) > intervals:
                return points[-1] - points[-1 - intervals]
            return None

        # 15-Minuten-Punkte: 4 = 1h, 12 = 3h, 96 = 24h
        delta_1h = delta(4)
        delta_3h = delta(12)
        delta_24h = delta(96)

        def fmt_delta(value):
            if value is None:
                return "--"
            sign = "+" if value >= 0 else ""
            return f"{sign}{value:.1f}"

        trend_source = delta_3h if delta_3h is not None else delta_1h

        if trend_source is None:
            trend_text = "neu"
        elif trend_source <= -1.0:
            trend_text = "fall"
        elif trend_source >= 1.0:
            trend_text = "steig"
        else:
            trend_text = "stab"

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
            center_label = "A"

        min_display_range = float(config.get("min_display_range_hpa", 10))

        max_deviation = max(abs(value - center_pressure) for value in points)
        display_range = max(min_display_range, max_deviation * 2)

        # Kleine Reserve gegen Randkleben
        display_range += 1.0

        low = center_pressure - display_range / 2
        high = center_pressure + display_range / 2

        # Kopfzeilen
        line1 = f"P{display_pressure:.1f}hPa mn{min_pressure:.0f} mx{max_pressure:.0f}"
        line2 = f"d1h{fmt_delta(delta_1h)} d3h{fmt_delta(delta_3h)} R{display_range:.0f} {trend_text}"

        self.draw.text((0, 0), line1[:22], font=self.font, fill=255)
        self.draw.text((0, 10), line2[:22], font=self.font, fill=255)

        # Graph-Bereich:
        # links 96 Pixel für 24h bei 15-Minuten-Werten,
        # rechts Skalenbeschriftung.
        graph_x = 0
        graph_y = 23

        # Für 128x64: 96 px Graph + rechter Skalenbereich.
        graph_w = min(96, self.width - 30)
        graph_h = self.height - graph_y - 1

        if graph_w < 40:
            graph_w = min(96, self.width)

        if graph_h < 16:
            graph_h = max(8, self.height - graph_y - 1)

        graph_right = graph_x + graph_w - 1
        graph_bottom = graph_y + graph_h - 1

        # Mittellinie gestrichelt
        mid_y = graph_y + graph_h // 2
        for x in range(graph_x, graph_x + graph_w):
            if x % 2 == 0:
                self.draw.point((x, mid_y), fill=255)

        # Zeitmarker bei -18h, -12h, -6h:
        # Nur je ein Pixel oberhalb und unterhalb der Mittellinie.
        # Bei 96 Punkten = 24h und 15-Minuten-Intervall:
        # 24 Punkte = 6h.
        for offset in (72, 48, 24):
            x = graph_x + graph_w - 1 - offset

            if graph_x <= x <= graph_right:
                if graph_y <= mid_y - 1 <= graph_bottom:
                    self.draw.point((x, mid_y - 1), fill=255)
                if graph_y <= mid_y + 1 <= graph_bottom:
                    self.draw.point((x, mid_y + 1), fill=255)

        values_to_draw = points[-graph_w:]

        plotted = []

        for index, pressure in enumerate(values_to_draw):
            x = graph_x + index

            if high == low:
                y = mid_y
            else:
                ratio = (pressure - low) / (high - low)
                ratio = max(0.0, min(1.0, ratio))
                y = graph_bottom - int(round(ratio * (graph_h - 1)))

            plotted.append((x, y))
            self.draw.point((x, y), fill=255)

        # Letzten Messpunkt hervorheben
        if plotted:
            lx, ly = plotted[-1]
            self.draw.rectangle(
                (
                    max(graph_x, lx - 1),
                    max(graph_y, ly - 1),
                    min(graph_right, lx + 1),
                    min(graph_bottom, ly + 1),
                ),
                outline=255,
                fill=0,
            )
            self.draw.point((lx, ly), fill=255)

        # rechte Skala
        scale_x = graph_x + graph_w + 3

        if scale_x < self.width - 20:
            self.draw.text((scale_x, graph_y), f"{high:.0f}", font=self.font, fill=255)
            self.draw.text((scale_x, max(graph_y, mid_y - 4)), f"{center_label}{center_pressure:.0f}", font=self.font, fill=255)
            self.draw.text((scale_x, max(graph_y, graph_bottom - 8)), f"{low:.0f}", font=self.font, fill=255)

        self._show()

    @staticmethod
    def _project_track_points(track_points, x0, y0, width, height):
        valid = []

        for point in track_points or []:
            try:
                lat = float(point["lat"])
                lon = float(point["lon"])
                valid.append((lat, lon))
            except (KeyError, TypeError, ValueError):
                continue

        if not valid:
            return []

        if len(valid) == 1:
            return [(x0 + width // 2, y0 + height // 2)]

        lat0 = sum(lat for lat, _ in valid) / len(valid)
        lon0 = sum(lon for _, lon in valid) / len(valid)

        lat_scale_m = 110540.0
        lon_scale_m = 111320.0 * math.cos(math.radians(lat0))

        local_points = []

        for lat, lon in valid:
            x = (lon - lon0) * lon_scale_m
            y = (lat - lat0) * lat_scale_m
            local_points.append((x, y))

        min_x = min(x for x, _ in local_points)
        max_x = max(x for x, _ in local_points)
        min_y = min(y for _, y in local_points)
        max_y = max(y for _, y in local_points)

        span_x = max_x - min_x
        span_y = max_y - min_y

        if span_x == 0 and span_y == 0:
            return [(x0 + width // 2, y0 + height // 2) for _ in local_points]

        usable_w = max(1, width - 4)
        usable_h = max(1, height - 4)

        scale_x = usable_w / span_x if span_x > 0 else float("inf")
        scale_y = usable_h / span_y if span_y > 0 else float("inf")
        scale = min(scale_x, scale_y)

        drawn_w = span_x * scale if span_x > 0 else 0
        drawn_h = span_y * scale if span_y > 0 else 0

        offset_x = x0 + 2 + (usable_w - drawn_w) / 2
        offset_y = y0 + 2 + (usable_h - drawn_h) / 2

        pixel_points = []

        for x, y in local_points:
            px = int(round(offset_x + (x - min_x) * scale))

            # Nord oben: größere Breite/latitude soll am Display weiter oben liegen.
            py = int(round(offset_y + drawn_h - (y - min_y) * scale))

            px = max(x0, min(x0 + width - 1, px))
            py = max(y0, min(y0 + height - 1, py))

            pixel_points.append((px, py))

        return pixel_points

    def show_track_map(self, track_points, title="Track", info_lines=None):
        """
        Zeichnet einen Track als vereinfachte Nord-oben-Karte.

        track_points:
            Liste von dicts mit lat/lon.

        Die Geometrie wird automatisch so skaliert, dass sie ins OLED passt.
        """
        info_lines = info_lines or []

        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        self.draw.text((0, 0), str(title)[:18], font=self.font, fill=255)

        bottom_h = 10 if info_lines else 0

        plot_x = 0
        plot_y = 11
        plot_w = self.width
        plot_h = self.height - plot_y - bottom_h - 1

        if plot_h < 10:
            plot_h = max(8, self.height - plot_y - 1)

        self.draw.rectangle(
            (plot_x, plot_y, plot_x + plot_w - 1, plot_y + plot_h - 1),
            outline=255,
            fill=0,
        )

        pixel_points = self._project_track_points(track_points, plot_x + 1, plot_y + 1, plot_w - 2, plot_h - 2)

        if not pixel_points:
            self.draw.text((4, plot_y + 8), "Keine Punkte", font=self.font, fill=255)
        elif len(pixel_points) == 1:
            x, y = pixel_points[0]
            self.draw.rectangle((x - 1, y - 1, x + 1, y + 1), outline=255, fill=255)
        else:
            previous = pixel_points[0]

            for current in pixel_points[1:]:
                self.draw.line((previous[0], previous[1], current[0], current[1]), fill=255)
                previous = current

            # Startmarker: kleines Quadrat
            sx, sy = pixel_points[0]
            self.draw.rectangle((sx - 1, sy - 1, sx + 1, sy + 1), outline=255, fill=255)

            # Endmarker: kleines X
            ex, ey = pixel_points[-1]
            self.draw.line((ex - 2, ey - 2, ex + 2, ey + 2), fill=255)
            self.draw.line((ex - 2, ey + 2, ex + 2, ey - 2), fill=255)

        # Nordpfeil rechts oben im Plot
        nx = self.width - 10
        ny = plot_y + 3
        if plot_h > 18:
            self.draw.line((nx, ny + 8, nx, ny), fill=255)
            self.draw.line((nx, ny, nx - 2, ny + 3), fill=255)
            self.draw.line((nx, ny, nx + 2, ny + 3), fill=255)
            self.draw.text((nx - 3, ny + 9), "N", font=self.font, fill=255)

        if info_lines:
            self.draw.text(
                (0, self.height - 10),
                str(info_lines[0])[:22],
                font=self.font,
                fill=255,
            )

        self._show()

    def sleep(self):
        """
        OLED ausschalten, ohne das gespeicherte Bild zu verlieren.
        """
        if hasattr(self.display, "poweroff"):
            self.display.poweroff()
        else:
            blank = Image.new("1", (self.width, self.height))
            self.display.image(blank)
            self.display.show()

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
