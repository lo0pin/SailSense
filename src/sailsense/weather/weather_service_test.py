import os
import time
from pathlib import Path

from sailsense.config import load_config
from sailsense.weather.bme280_reader import BME280Reader
from sailsense.weather.weather_service import WeatherService, WEATHER_FIELDNAMES
from sailsense.storage.csv_logger import CsvLogger


def main():
    config = load_config()

    bme_config = config["bme280"]
    service_config = config["weather_service"]
    logging_config = config["logging"]

    address = bme_config["i2c_address"]

    raw_interval = float(service_config.get("raw_read_interval_seconds", 10))
    display_window = float(service_config.get("display_average_seconds", 60))

    storage_interval = float(service_config.get("storage_interval_minutes", 15)) * 60

    # Für Tests kann man das Speicherintervall per Environment verkürzen.
    # Produktion bleibt 15 Minuten.
    storage_interval = float(
        os.getenv("SAILSENSE_WEATHER_STORAGE_INTERVAL", storage_interval)
    )

    history_points = int(service_config.get("history_points", 96))

    log_base_dir = Path(logging_config["log_base_dir"])
    weather_log_dir = log_base_dir / "weather"

    print("SailSense WeatherService-Test startet")
    print(f"BME280-Adresse: {hex(address)}")
    print(f"Rohmessung alle: {raw_interval} s")
    print(f"Anzeige-Mittelwert: {display_window} s")
    print(f"CSV-Speicherintervall: {storage_interval} s")
    print(f"History-Punkte: {history_points}")
    print(f"Log-Verzeichnis: {weather_log_dir}")
    print("Abbruch mit Strg+C")
    print()

    try:
        with BME280Reader(i2c_address=address) as bme:
            with CsvLogger(
                log_dir=weather_log_dir,
                prefix="weather_15min",
                fieldnames=WEATHER_FIELDNAMES,
                flush_after_write=True,
            ) as logger:

                service = WeatherService(
                    bme_reader=bme,
                    csv_logger=logger,
                    raw_read_interval_seconds=raw_interval,
                    display_average_seconds=display_window,
                    storage_interval_seconds=storage_interval,
                    history_points=history_points,
                )

                # Warm-up
                print("Sensor stabilisiert sich kurz ...")
                for _ in range(3):
                    service.tick(force_read=True)
                    time.sleep(1)

                last_print = 0.0

                while True:
                    snapshot = service.tick()
                    now = time.monotonic()

                    if snapshot is not None and now - last_print >= 5:
                        print(
                            f"{snapshot['timestamp_utc']} | "
                            f"1min Ø: {snapshot['temp_c']} °C | "
                            f"{snapshot['humidity_pct']} % | "
                            f"{snapshot['pressure_hpa']} hPa | "
                            f"Samples: {snapshot['sample_count']}"
                        )
                        last_print = now

                    time.sleep(1)

    except KeyboardInterrupt:
        print("\nWeatherService-Test beendet.")


if __name__ == "__main__":
    main()
