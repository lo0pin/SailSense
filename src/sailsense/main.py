from pathlib import Path

from sailsense.config import load_config
from sailsense.gps.gps_reader import GPSReader
from sailsense.storage.csv_logger import CsvLogger


GPS_FIELDNAMES = [
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
]


def main():
    config = load_config()

    gps_config = config["gps"]
    logging_config = config["logging"]

    gps_port = gps_config["port"]
    gps_baudrate = gps_config["baudrate"]

    log_base_dir = Path(logging_config["log_base_dir"])
    gps_log_dir = log_base_dir / "gps"

    flush_after_write = logging_config.get("flush_after_write", True)

    print("SailSense GPS-Logger startet")
    print(f"GPS-Port: {gps_port}")
    print(f"Baudrate: {gps_baudrate}")
    print(f"Log-Verzeichnis: {gps_log_dir}")
    print("Abbruch mit Strg+C")

    with GPSReader(gps_port, gps_baudrate) as gps:
        with CsvLogger(
            log_dir=gps_log_dir,
            prefix="gps",
            fieldnames=GPS_FIELDNAMES,
            flush_after_write=flush_after_write,
        ) as logger:

            for point in gps.read_points():
                logger.write_row(point)

                lat = point["lat"]
                lon = point["lon"]
                speed_kn = point["speed_kn"]
                sats = point["sats"]
                fix = point["fix_quality"]

                print(
                    f"{point['timestamp_utc']} | "
                    f"{lat:.6f}, {lon:.6f} | "
                    f"{speed_kn} kn | "
                    f"{sats} sats | "
                    f"fix {fix}"
                )


if __name__ == "__main__":
    main()
