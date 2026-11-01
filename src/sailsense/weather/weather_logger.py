import time
from pathlib import Path

from sailsense.config import load_config
from sailsense.storage.csv_logger import CsvLogger
from sailsense.weather.bme280_reader import BME280Reader


WEATHER_FIELDNAMES = [
    "timestamp_utc",
    "temp_c",
    "humidity_pct",
    "pressure_hpa",
]


def main():
    config = load_config()

    bme_config = config["bme280"]
    logging_config = config["logging"]

    address = bme_config["i2c_address"]
    interval = bme_config.get("read_interval_seconds", 10)

    log_base_dir = Path(logging_config["log_base_dir"])
    weather_log_dir = log_base_dir / "weather"

    flush_after_write = logging_config.get("flush_after_write", True)

    print("SailSense Wetter-Logger startet")
    print(f"BME280-Adresse: {hex(address)}")
    print(f"Intervall: {interval} s")
    print(f"Log-Verzeichnis: {weather_log_dir}")
    print("Abbruch mit Strg+C")

    try:
        with BME280Reader(i2c_address=address) as bme:
            with CsvLogger(
                log_dir=weather_log_dir,
                prefix="weather",
                fieldnames=WEATHER_FIELDNAMES,
                flush_after_write=flush_after_write,
            ) as logger:

                # Warm-up: erste Messungen verwerfen
                for _ in range(3):
                    _ = bme.read()
                    time.sleep(1)

                while True:
                    data = bme.read()
                    logger.write_row(data)

                    print(
                        f"{data['timestamp_utc']} | "
                        f"{data['temp_c']} °C | "
                        f"{data['humidity_pct']} % | "
                        f"{data['pressure_hpa']} hPa"
                    )

                    time.sleep(interval)

    except KeyboardInterrupt:
        print("\nWetter-Logger beendet.")


if __name__ == "__main__":
    main()
