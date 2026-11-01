import time
from datetime import datetime, timezone

import serial
import pynmea2

import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

from sailsense.config import load_config


def parse_i2c_address(value):
    """
    Erlaubt sowohl 0x3C als Zahl als auch "0x3C" als String.
    """
    if isinstance(value, int):
        return value

    if isinstance(value, str):
        return int(value, 16)

    raise ValueError(f"Ungültige I2C-Adresse: {value}")


def draw_lines(oled, lines):
    """
    Schreibt mehrere Textzeilen auf das OLED.
    """
    width = oled.width
    height = oled.height

    image = Image.new("1", (width, height))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    y = 0
    line_height = 10

    for line in lines:
        draw.text((0, y), line, font=font, fill=255)
        y += line_height

    oled.image(image)
    oled.show()


def format_float(value, decimals=6):
    if value is None:
        return "---"
    return f"{value:.{decimals}f}"


def main():
    config = load_config()

    gps_port = config["gps"]["port"]
    gps_baudrate = config["gps"]["baudrate"]

    oled_config = config.get("oled", {})
    oled_width = oled_config.get("width", 128)
    oled_height = oled_config.get("height", 64)
    oled_address = parse_i2c_address(oled_config.get("i2c_address", 0x3C))

    print(f"GPS: {gps_port} @ {gps_baudrate} Baud")
    print(f"OLED: {oled_width}x{oled_height} @ {hex(oled_address)}")

    i2c = busio.I2C(board.SCL, board.SDA)
    oled = adafruit_ssd1306.SSD1306_I2C(
        oled_width,
        oled_height,
        i2c,
        addr=oled_address,
    )

    oled.fill(0)
    oled.show()

    draw_lines(
        oled,
        [
            "SailSense",
            "GPS OLED Test",
            "Warte auf GPS...",
        ],
    )

    latest = {
        "timestamp_utc": None,
        "lat": None,
        "lon": None,
        "speed_kn": None,
        "course_deg": None,
        "fix_quality": None,
        "sats": None,
        "alt_m": None,
        "hdop": None,
        "status": "V",
    }

    last_display_update = 0.0

    with serial.Serial(gps_port, gps_baudrate, timeout=1) as ser:
        print("Lese GPS-Daten. Abbruch mit Strg+C.")

        while True:
            raw = ser.readline().decode("ascii", errors="replace").strip()

            if not raw:
                continue

            try:
                msg = pynmea2.parse(raw)
            except pynmea2.ParseError:
                continue

            if msg.sentence_type == "GGA":
                latest["fix_quality"] = getattr(msg, "gps_qual", None)
                latest["sats"] = getattr(msg, "num_sats", None)
                latest["alt_m"] = getattr(msg, "altitude", None)
                latest["hdop"] = getattr(msg, "horizontal_dil", None)

            elif msg.sentence_type == "RMC":
                latest["status"] = getattr(msg, "status", "V")

                if latest["status"] == "A":
                    latest["lat"] = getattr(msg, "latitude", None)
                    latest["lon"] = getattr(msg, "longitude", None)
                    latest["speed_kn"] = getattr(msg, "spd_over_grnd", None)
                    latest["course_deg"] = getattr(msg, "true_course", None)

                    try:
                        dt = datetime.combine(msg.datestamp, msg.timestamp)
                        latest["timestamp_utc"] = (
                            dt.replace(tzinfo=timezone.utc)
                            .isoformat()
                            .replace("+00:00", "Z")
                        )
                    except Exception:
                        latest["timestamp_utc"] = None

            now = time.time()

            # OLED nur ca. 1x pro Sekunde aktualisieren.
            if now - last_display_update < 1.0:
                continue

            last_display_update = now

            if latest["status"] == "A":
                lat = format_float(latest["lat"], 6)
                lon = format_float(latest["lon"], 6)

                speed_kn = latest["speed_kn"]
                try:
                    speed_text = f"{float(speed_kn):.1f} kn"
                except (TypeError, ValueError):
                    speed_text = "--- kn"

                sats = latest["sats"] or "--"
                fix = latest["fix_quality"] or "-"
                alt = latest["alt_m"] or "---"

                lines = [
                    "SailSense GPS",
                    f"Lat {lat}",
                    f"Lon {lon}",
                    f"Spd {speed_text}",
                    f"Sat {sats} Fix {fix}",
                    f"Alt {alt} m",
                ]

                print(" | ".join(lines))

            else:
                lines = [
                    "SailSense GPS",
                    "Kein Fix",
                    "Antenne raus?",
                    f"Sat {latest['sats'] or '--'}",
                    f"Fix {latest['fix_quality'] or '-'}",
                ]

                print("Kein gültiger GPS-Fix")

            draw_lines(oled, lines)


if __name__ == "__main__":
    main()
