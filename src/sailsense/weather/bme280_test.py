import time

from sailsense.config import load_config
from sailsense.weather.bme280_reader import BME280Reader


def main():
    config = load_config()
    address = config["bme280"]["i2c_address"]
    interval = config["bme280"].get("read_interval_seconds", 10)

    print(f"Lese BME280 auf I²C-Adresse {hex(address)}")
    print(f"Intervall: {interval} s")
    print("Erste Messwerte werden zum Stabilisieren verworfen.")
    print("Abbruch mit Strg+C")

    try:
        with BME280Reader(i2c_address=address) as bme:
            # Warm-up: erste Messungen verwerfen
            for _ in range(3):
                _ = bme.read()
                time.sleep(1)

            while True:
                data = bme.read()

                print(
                    f"{data['timestamp_utc']} | "
                    f"{data['temp_c']} °C | "
                    f"{data['humidity_pct']} % | "
                    f"{data['pressure_hpa']} hPa"
                )

                time.sleep(interval)

    except KeyboardInterrupt:
        print("\nBME280-Test beendet.")


if __name__ == "__main__":
    main()
