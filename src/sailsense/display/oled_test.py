import time

from sailsense.config import load_config
from sailsense.display.oled_display import OLEDDisplay


def main():
    config = load_config()

    oled_config = config["oled"]
    address = oled_config["i2c_address"]
    width = oled_config.get("width", 128)
    height = oled_config.get("height", 64)

    print(f"Teste OLED auf I²C-Adresse {hex(address)}")
    print(f"Auflösung: {width}x{height}")
    print("Abbruch mit Strg+C")

    try:
        with OLEDDisplay(width=width, height=height, i2c_address=address) as oled:
            oled.show_status(
                "SailSense",
                [
                    "OLED OK",
                    "GPS: bereit",
                    "BME280: bereit",
                    "I2C: 0x3C",
                ],
            )

            time.sleep(5)

            counter = 0

            while True:
                oled.show_status(
                    "SailSense",
                    [
                        f"Testlauf: {counter}",
                        "Display lebt",
                        "Kein Rauch",
                        "Gute Zeichen",
                    ],
                )

                print(f"OLED-Testlauf {counter}")
                counter += 1
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nOLED-Test beendet.")


if __name__ == "__main__":
    main()
