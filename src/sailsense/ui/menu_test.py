from signal import pause
from datetime import datetime

from sailsense.config import load_config
from sailsense.display.oled_display import OLEDDisplay
from sailsense.input.buttons import ButtonController, ButtonPins
from sailsense.ui.menu import MenuController, MenuScreen, MenuItem
from sailsense.system.power import poweroff, reboot


def now_text():
    return datetime.now().strftime("%H:%M:%S")


def render_menu(oled, screen, message=None):
    lines = []

    if message:
        lines.append(message[:21])
        lines.append("")
    else:
        visible_items = screen.items[:5]

        for index, item in enumerate(visible_items):
            cursor = ">" if index == screen.selected_index else " "
            lines.append(f"{cursor} {item.label}")

    oled.show_status(screen.title, lines)


def build_menu():
    root = MenuScreen("SailSense", [])

    status = MenuScreen("Status", [
        MenuItem("Logger: bereit"),
        MenuItem("GPS: bereit"),
        MenuItem("BME280: bereit"),
        MenuItem("OLED: OK"),
    ], parent=root)

    gps = MenuScreen("GPS", [
        MenuItem("Fix anzeigen"),
        MenuItem("Satelliten"),
        MenuItem("Position"),
        MenuItem("Speed/Kurs"),
    ], parent=root)

    weather = MenuScreen("Wetter", [
        MenuItem("Temperatur"),
        MenuItem("Feuchte"),
        MenuItem("Luftdruck"),
    ], parent=root)

    logging = MenuScreen("Logging", [
        MenuItem("Start/Stop"),
        MenuItem("Marker setzen"),
        MenuItem("Datei anzeigen"),
    ], parent=root)

    system = MenuScreen("System", [], parent=root)
    reboot_confirm = MenuScreen("Neustart?", [], parent=system)
    shutdown_confirm = MenuScreen("Ausschalten?", [], parent=system)

    def marker_action():
        return f"Marker {now_text()}"

    def info_action():
        return "SailSense v0.1"

    def do_reboot():
        reboot()
        return "Neustart..."

    def do_poweroff():
        poweroff()
        return "Fahre herunter..."

    reboot_confirm.items = [
        MenuItem("OK: Neustart", action=do_reboot),
        MenuItem("BACK: Abbrechen"),
    ]

    shutdown_confirm.items = [
        MenuItem("OK: Ausschalten", action=do_poweroff),
        MenuItem("BACK: Abbrechen"),
    ]

    system.items = [
        MenuItem("Info", action=info_action),
        MenuItem("Neustart", target=reboot_confirm),
        MenuItem("Herunterfahren", target=shutdown_confirm),
    ]

    logging.items[1] = MenuItem("Marker setzen", action=marker_action)

    root.items = [
        MenuItem("Status", target=status),
        MenuItem("GPS", target=gps),
        MenuItem("Wetter", target=weather),
        MenuItem("Logging", target=logging),
        MenuItem("System", target=system),
    ]

    return root


def main():
    config = load_config()

    oled_config = config["oled"]
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

    oled_width = oled_config.get("width", 128)
    oled_height = oled_config.get("height", 64)
    oled_address = oled_config.get("i2c_address", 0x3C)

    print("SailSense Menue-Test startet")
    print("UP/DOWN = bewegen, OK = auswaehlen, BACK = zurueck")
    print("Achtung: Neustart/Herunterfahren sind jetzt echt.")
    print("Abbruch mit Strg+C")

    try:
        with OLEDDisplay(
            width=oled_width,
            height=oled_height,
            i2c_address=oled_address,
        ) as oled:
            root = build_menu()

            menu = MenuController(
                root_screen=root,
                on_render=lambda screen, message=None: render_menu(oled, screen, message),
            )

            with ButtonController(
                pins=pins,
                bounce_time=bounce_time,
                hold_time=hold_time,
            ) as buttons:

                buttons.bind(
                    on_press=lambda name: {
                        "UP": menu.up,
                        "DOWN": menu.down,
                        "OK": menu.ok,
                        "BACK": menu.back,
                    }[name](),
                )

                menu.render()
                pause()

    except KeyboardInterrupt:
        print("\nMenue-Test beendet.")


if __name__ == "__main__":
    main()
