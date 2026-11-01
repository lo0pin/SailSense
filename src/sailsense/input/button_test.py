from signal import pause
from datetime import datetime

from sailsense.config import load_config
from sailsense.input.buttons import ButtonController, ButtonPins


def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def main():
    config = load_config()

    button_config = config["buttons"]
    pins_config = button_config["pins"]

    pins = ButtonPins(
        up=pins_config["up"],
        down=pins_config["down"],
        ok=pins_config["ok"],
        back=pins_config["back"],
    )

    bounce_time = button_config.get("bounce_time_seconds", 0.05)
    hold_time = button_config.get("hold_time_seconds", 2.0)

    print("SailSense Button-Test startet")
    print("GPIO-Belegung:")
    print(f"  UP:   GPIO{pins.up}")
    print(f"  DOWN: GPIO{pins.down}")
    print(f"  OK:   GPIO{pins.ok}")
    print(f"  BACK: GPIO{pins.back}")
    print()
    print("Drücke die Buttons. Abbruch mit Strg+C.")
    print()

    def on_press(name: str):
        print(f"{timestamp()} | {name:<5} gedrückt")

    def on_release(name: str):
        print(f"{timestamp()} | {name:<5} losgelassen")

    def on_hold(name: str):
        print(f"{timestamp()} | {name:<5} lange gedrückt")

    try:
        with ButtonController(
            pins=pins,
            bounce_time=bounce_time,
            hold_time=hold_time,
        ) as buttons:
            buttons.bind(
                on_press=on_press,
                on_release=on_release,
                on_hold=on_hold,
            )

            pause()

    except KeyboardInterrupt:
        print("\nButton-Test beendet.")


if __name__ == "__main__":
    main()
