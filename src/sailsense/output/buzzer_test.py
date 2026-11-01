import time

from sailsense.config import load_config
from sailsense.output.buzzer import Buzzer


def main():
    config = load_config()
    buzzer_config = config["buzzer"]

    pin = buzzer_config["pin"]
    kind = buzzer_config.get("kind", "active")
    active_high = buzzer_config.get("active_high", True)
    volume = buzzer_config.get("volume", 0.5)

    print("SailSense Buzzer-Test")
    print(f"Pin: GPIO{pin}")
    print(f"Kind: {kind}")
    print(f"Active high: {active_high}")
    print(f"Volume: {volume}")
    print("Abbruch mit Strg+C")
    print()

    patterns = [
        "click",
        "ok",
        "marker",
        "track_start",
        "track_stop",
        "warning",
        "error",
        "alarm",
    ]

    try:
        with Buzzer(
            pin=pin,
            kind=kind,
            active_high=active_high,
            volume=volume,
        ) as buzzer:

            while True:
                for pattern in patterns:
                    print(f"Muster: {pattern}")
                    buzzer.play(pattern)
                    time.sleep(1.5)

                print()

    except KeyboardInterrupt:
        print("\nBuzzer-Test beendet.")


if __name__ == "__main__":
    main()
