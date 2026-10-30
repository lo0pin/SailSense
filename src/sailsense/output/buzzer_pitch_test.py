import time

from sailsense.config import load_config
from sailsense.output.buzzer import Buzzer


def main():
    config = load_config()
    buzzer_config = config["buzzer"]

    pin = buzzer_config["pin"]
    kind = buzzer_config.get("kind", "passive")
    active_high = buzzer_config.get("active_high", True)
    volume = buzzer_config.get("volume", 0.5)
    passive_frequency = buzzer_config.get("passive_frequency", 2200)
    frequencies = buzzer_config.get("frequencies", {})

    print("SailSense Buzzer-Pitch-Test")
    print(f"Pin: GPIO{pin}")
    print(f"Kind: {kind}")
    print(f"Active high: {active_high}")
    print(f"Volume: {volume}")
    print(f"Default frequency: {passive_frequency} Hz")
    print("Abbruch mit Strg+C")
    print()

    test_frequencies = [200, 300, 400, 500, 600, 700]

    try:
        with Buzzer(
            pin=pin,
            kind=kind,
            active_high=active_high,
            volume=volume,
            passive_frequency=passive_frequency,
            frequencies=frequencies,
        ) as buzzer:

            while True:
                print("Frequenzleiter:")
                for freq in test_frequencies:
                    print(f"{freq} Hz")
                    buzzer.beep(0.25, frequency=freq)
                    time.sleep(0.55)

                print()
                print("Muster mit konfigurierten Frequenzen:")
                for name in [
                    "click",
                    "ok",
                    "marker",
                    "track_start",
                    "track_stop",
                    "warning",
                    "error",
                    "alarm",
                ]:
                    print(name)
                    buzzer.play(name)
                    time.sleep(1.2)

                print()

    except KeyboardInterrupt:
        print("\nBuzzer-Pitch-Test beendet.")


if __name__ == "__main__":
    main()
