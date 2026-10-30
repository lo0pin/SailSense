import time
from pathlib import Path
from contextlib import ExitStack

from sailsense.config import load_config
from sailsense.gps.gps_reader import GPSReader
from sailsense.weather.bme280_reader import BME280Reader
from sailsense.storage.csv_logger import CsvLogger
from sailsense.display.oled_display import OLEDDisplay


COMBINED_FIELDNAMES = [
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
    "weather_timestamp_utc",
    "temp_c",
    "humidity_pct",
    "pressure_hpa",
]


def format_value(value, suffix="", digits=1):
    if value is None:
        return "--"
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return f"{value}{suffix}"


def update_oled(oled, row):
    """
    Aktualisiert die OLED-Statusanzeige.
    Möglichst kurze Zeilen, weil 128x64 kein Romanformat ist.
    """
    if oled is None:
        return

    sats = row.get("sats") or "--"
    fix = row.get("fix_quality") or "--"

    speed_kn = format_value(row.get("speed_kn"), "kn", 1)
    temp_c = format_value(row.get("temp_c"), "C", 1)
    humidity = format_value(row.get("humidity_pct"), "%", 0)
    pressure = format_value(row.get("pressure_hpa"), "hPa", 1)

    lat = row.get("lat")
    lon = row.get("lon")

    if lat is not None and lon is not None:
        position_line = "Pos: OK"
    else:
        position_line = "Pos: --"

    oled.show_status(
        "SailSense LOG",
        [
            f"GPS: {sats} sat f{fix}",
            position_line,
            f"Spd: {speed_kn}",
            f"T:{temp_c} H:{humidity}",
            f"P:{pressure}",
        ],
    )


def main():
    config = load_config()

    gps_config = config["gps"]
    bme_config = config["bme280"]
    oled_config = config.get("oled", {})
    logging_config = config["logging"]

    gps_port = gps_config["port"]
    gps_baudrate = gps_config["baudrate"]

    bme_address = bme_config["i2c_address"]
    bme_interval = bme_config.get("read_interval_seconds", 10)

    oled_enabled = oled_config.get("enabled", False)
    oled_width = oled_config.get("width", 128)
    oled_height = oled_config.get("height", 64)
    oled_address = oled_config.get("i2c_address", 0x3C)
    oled_update_interval = oled_config.get("update_interval_seconds", 2)

    log_base_dir = Path(logging_config["log_base_dir"])
    combined_log_dir = log_base_dir / "combined"

    flush_after_write = logging_config.get("flush_after_write", True)

    print("SailSense Combined Logger startet")
    print(f"GPS: {gps_port} @ {gps_baudrate} Baud")
    print(f"BME280: I²C-Adresse {hex(bme_address)}, Intervall {bme_interval} s")
    print(f"OLED: {'aktiv' if oled_enabled else 'inaktiv'}")
    print(f"Log-Verzeichnis: {combined_log_dir}")
    print("Abbruch mit Strg+C")

    latest_weather = {
        "weather_timestamp_utc": None,
        "temp_c": None,
        "humidity_pct": None,
        "pressure_hpa": None,
    }

    last_weather_read = 0.0
    last_oled_update = 0.0

    try:
        with ExitStack() as stack:
            gps = stack.enter_context(GPSReader(gps_port, gps_baudrate))
            bme = stack.enter_context(BME280Reader(i2c_address=bme_address))

            logger = stack.enter_context(
                CsvLogger(
                    log_dir=combined_log_dir,
                    prefix="combined",
                    fieldnames=COMBINED_FIELDNAMES,
                    flush_after_write=flush_after_write,
                )
            )

            oled = None
            if oled_enabled:
                oled = stack.enter_context(
                    OLEDDisplay(
                        width=oled_width,
                        height=oled_height,
                        i2c_address=oled_address,
                    )
                )
                oled.show_status(
                    "SailSense",
                    [
                        "Logger startet",
                        "GPS wartet...",
                        "BME280 OK",
                    ],
                )

            print("BME280 stabilisiert sich kurz ...")
            for _ in range(3):
                _ = bme.read()
                time.sleep(1)

            weather = bme.read()
            latest_weather = {
                "weather_timestamp_utc": weather["timestamp_utc"],
                "temp_c": weather["temp_c"],
                "humidity_pct": weather["humidity_pct"],
                "pressure_hpa": weather["pressure_hpa"],
            }
            last_weather_read = time.monotonic()

            print("Logging läuft.")

            for gps_point in gps.read_points():
                now = time.monotonic()

                if now - last_weather_read >= bme_interval:
                    try:
                        weather = bme.read()
                        latest_weather = {
                            "weather_timestamp_utc": weather["timestamp_utc"],
                            "temp_c": weather["temp_c"],
                            "humidity_pct": weather["humidity_pct"],
                            "pressure_hpa": weather["pressure_hpa"],
                        }
                        last_weather_read = now
                    except Exception as error:
                        print(f"BME280-Lesefehler, verwende letzten Wert weiter: {error}")

                row = {
                    **gps_point,
                    **latest_weather,
                }

                logger.write_row(row)

                if oled_enabled and now - last_oled_update >= oled_update_interval:
                    update_oled(oled, row)
                    last_oled_update = now

                print(
                    f"{row['timestamp_utc']} | "
                    f"{row['lat']:.6f}, {row['lon']:.6f} | "
                    f"{row['speed_kn']} kn | "
                    f"{row['sats']} sats | "
                    f"{row['temp_c']} °C | "
                    f"{row['humidity_pct']} % | "
                    f"{row['pressure_hpa']} hPa"
                )

    except KeyboardInterrupt:
        print("\nCombined Logger beendet.")


if __name__ == "__main__":
    main()
