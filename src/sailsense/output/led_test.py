import time

from sailsense.config import load_config
from sailsense.output.status_led import StatusLED


def main():
    config = load_config()
    led_config = config["status_led"]

    if not led_config.get("enabled", False):
        print("status_led.enabled ist false. Test wird trotzdem ausgeführt.")

    pins = led_config["pins"]
    brightness = led_config.get("brightness", {})
    common = led_config.get("common", "anode")
    delay = led_config.get("test_delay_seconds", 1.0)

    print("SailSense RGB-LED-Test startet")
    print(f"Common: {common}")
    print(f"Rot:   GPIO{pins['red']}")
    print(f"Grün:  GPIO{pins['green']}")
    print(f"Blau:  GPIO{pins['blue']}")
    print("Abbruch mit Strg+C")
    print()

    colors = [
        "red",
        "green",
        "blue",
        "yellow",
        "cyan",
        "magenta",
        "white",
        "off",
    ]

    try:
        with StatusLED(
            red_pin=pins["red"],
            green_pin=pins["green"],
            blue_pin=pins["blue"],
            common=common,
            red_brightness=brightness.get("red", 1.0),
            green_brightness=brightness.get("green", 1.0),
            blue_brightness=brightness.get("blue", 1.0),
        ) as led:
            while True:
                for color in colors:
                    print(f"Farbe: {color}")
                    led.set_color(color)
                    time.sleep(delay)

                print("Blinktest: grün")
                led.blink("green", times=3)

                print("Blinktest: rot")
                led.blink("red", times=3)

                print()

    except KeyboardInterrupt:
        print("\nLED-Test beendet.")


if __name__ == "__main__":
    main()
