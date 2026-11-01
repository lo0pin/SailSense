import os
import time
from pathlib import Path
from contextlib import ExitStack
from dataclasses import dataclass, field

from sailsense.config import load_config
from sailsense.gps.gps_reader import GPSReader
from sailsense.weather.bme280_reader import BME280Reader
from sailsense.weather.weather_service import WeatherService, WEATHER_FIELDNAMES
from sailsense.storage.csv_logger import CsvLogger
from sailsense.display.oled_display import OLEDDisplay
from sailsense.input.buttons import ButtonController, ButtonPins
from sailsense.system.power import poweroff, reboot
from sailsense.output.status_led import StatusLED


@dataclass
class AppState:
    screen_index: int = 0
    system_menu_index: int = 0
    mode: str = "pages"  # pages, system_menu, shutdown_confirm, reboot_confirm
    marker: str | None = None
    gps_point_count: int = 0
    weather_history_count: int = 0
    start_monotonic: float = field(default_factory=time.monotonic)
    latest_gps: dict = field(default_factory=dict)
    latest_weather: dict = field(default_factory=dict)


SCREENS = ["Status", "GPS", "Wetter", "Logging", "System"]
SYSTEM_ITEMS = ["Info", "Neustart", "Herunterfahren"]


def format_value(value, suffix="", digits=1):
    if value is None:
        return "--"
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return f"{value}{suffix}"


def uptime_text(start_monotonic: float) -> str:
    seconds = int(time.monotonic() - start_monotonic)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def render_pages(oled: OLEDDisplay, state: AppState):
    gps = state.latest_gps
    weather = state.latest_weather
    screen = SCREENS[state.screen_index]

    sats = gps.get("sats") or "--"
    fix = gps.get("fix_quality") or "--"
    speed_kn = format_value(gps.get("speed_kn"), "kn", 1)
    course = format_value(gps.get("course_deg"), "deg", 0)
    alt = format_value(gps.get("alt_m"), "m", 1)
    hdop = format_value(gps.get("hdop"), "", 1)

    temp = format_value(weather.get("temp_c"), "C", 1)
    humidity = format_value(weather.get("humidity_pct"), "%", 0)
    pressure = format_value(weather.get("pressure_hpa"), "hPa", 1)
    weather_samples = weather.get("sample_count", "--")

    lat = gps.get("lat")
    lon = gps.get("lon")

    if screen == "Status":
        oled.show_status(
            "SailSense",
            [
                f"GPS: {sats} sat f{fix}",
                f"Spd: {speed_kn}",
                f"T:{temp} H:{humidity}",
                f"P:{pressure}",
                f"W15: {state.weather_history_count}",
            ],
        )

    elif screen == "GPS":
        if lat is not None and lon is not None:
            lat_line = f"Lat:{float(lat):.5f}"
            lon_line = f"Lon:{float(lon):.5f}"
        else:
            lat_line = "Lat: --"
            lon_line = "Lon: --"

        oled.show_status(
            "GPS",
            [
                f"Fix:{fix} Sat:{sats}",
                lat_line,
                lon_line,
                f"Alt:{alt}",
                f"HDOP:{hdop}",
            ],
        )

    elif screen == "Wetter":
        oled.show_status(
            "Wetter 1min",
            [
                f"Temp: {temp}",
                f"Feuchte: {humidity}",
                f"Druck: {pressure}",
                f"Samples: {weather_samples}",
                f"15mPkt: {state.weather_history_count}",
            ],
        )

    elif screen == "Logging":
        oled.show_status(
            "Logging",
            [
                "GPS Track: spaeter",
                f"GPS pts: {state.gps_point_count}",
                f"Uptime: {uptime_text(state.start_monotonic)}",
                "OK: Marker",
                "DOWN: weiter",
            ],
        )

    elif screen == "System":
        oled.show_status(
            "System",
            [
                "OK: Menue",
                "UP/DOWN: Seite",
                f"Uptime: {uptime_text(state.start_monotonic)}",
                "Shutdown dort",
            ],
        )


def render_system_menu(oled: OLEDDisplay, state: AppState):
    lines = []

    for index, item in enumerate(SYSTEM_ITEMS):
        cursor = ">" if index == state.system_menu_index else " "
        lines.append(f"{cursor} {item}")

    lines.append("")
    lines.append("BACK: zurueck")

    oled.show_status("Systemmenue", lines)


def render_confirm(oled: OLEDDisplay, title: str, action_text: str):
    oled.show_status(
        title,
        [
            action_text,
            "",
            "OK: Ja",
            "BACK: Nein",
        ],
    )


def render(oled: OLEDDisplay, state: AppState):
    if state.mode == "pages":
        render_pages(oled, state)
    elif state.mode == "system_menu":
        render_system_menu(oled, state)
    elif state.mode == "shutdown_confirm":
        render_confirm(oled, "Ausschalten?", "Pi herunterfahren")
    elif state.mode == "reboot_confirm":
        render_confirm(oled, "Neustart?", "Pi neu starten")


def make_button_handler(state: AppState, oled: OLEDDisplay, led=None):
    def handle_button(name: str):
        if state.mode == "pages":
            if name == "UP":
                state.screen_index = (state.screen_index - 1) % len(SCREENS)

            elif name == "DOWN":
                state.screen_index = (state.screen_index + 1) % len(SCREENS)

            elif name == "OK":
                current_screen = SCREENS[state.screen_index]

                if current_screen == "System":
                    state.mode = "system_menu"
                    state.system_menu_index = 0

                elif current_screen == "Logging":
                    state.marker = time.strftime("marker_%H%M%S")
                    oled.show_status("Marker", [state.marker, "gesetzt"])

                    if led is not None:
                        led.blink("yellow", times=2, on_time=0.1, off_time=0.1)
                        led.set_color("green")

                    time.sleep(0.4)

            elif name == "BACK":
                state.screen_index = 0

        elif state.mode == "system_menu":
            if name == "UP":
                state.system_menu_index = (state.system_menu_index - 1) % len(SYSTEM_ITEMS)

            elif name == "DOWN":
                state.system_menu_index = (state.system_menu_index + 1) % len(SYSTEM_ITEMS)

            elif name == "BACK":
                state.mode = "pages"

            elif name == "OK":
                selected = SYSTEM_ITEMS[state.system_menu_index]

                if selected == "Info":
                    oled.show_status(
                        "Info",
                        [
                            "SailSense v0.2",
                            f"GPS: {state.gps_point_count}",
                            f"W15: {state.weather_history_count}",
                            f"Up: {uptime_text(state.start_monotonic)}",
                        ],
                    )
                    time.sleep(1.2)

                elif selected == "Neustart":
                    state.mode = "reboot_confirm"

                elif selected == "Herunterfahren":
                    state.mode = "shutdown_confirm"

        elif state.mode == "shutdown_confirm":
            if name == "OK":
                oled.show_status("SailSense", ["Fahre herunter..."])
                if led is not None:
                    led.set_color("red")
                poweroff()
                return

            elif name == "BACK":
                state.mode = "system_menu"

        elif state.mode == "reboot_confirm":
            if name == "OK":
                oled.show_status("SailSense", ["Starte neu..."])
                if led is not None:
                    led.set_color("red")
                reboot()
                return

            elif name == "BACK":
                state.mode = "system_menu"

        render(oled, state)

    return handle_button


def main():
    config = load_config()

    gps_config = config["gps"]
    bme_config = config["bme280"]
    weather_service_config = config["weather_service"]
    oled_config = config["oled"]
    button_config = config["buttons"]
    led_config = config.get("status_led", {})
    logging_config = config["logging"]

    gps_port = gps_config["port"]
    gps_baudrate = gps_config["baudrate"]

    bme_address = bme_config["i2c_address"]

    raw_interval = float(weather_service_config.get("raw_read_interval_seconds", 10))
    display_window = float(weather_service_config.get("display_average_seconds", 60))
    storage_interval = float(weather_service_config.get("storage_interval_minutes", 15)) * 60
    storage_interval = float(
        os.getenv("SAILSENSE_WEATHER_STORAGE_INTERVAL", storage_interval)
    )
    history_points = int(weather_service_config.get("history_points", 96))

    oled_width = oled_config.get("width", 128)
    oled_height = oled_config.get("height", 64)
    oled_address = oled_config.get("i2c_address", 0x3C)
    oled_update_interval = oled_config.get("update_interval_seconds", 2)

    pins_config = button_config["pins"]
    pins = ButtonPins(
        up=pins_config["up"],
        down=pins_config["down"],
        ok=pins_config["ok"],
        back=pins_config["back"],
    )

    bounce_time = button_config.get("bounce_time_seconds", 0.05)
    hold_time = button_config.get("hold_time_seconds", 2.0)

    led_enabled = led_config.get("enabled", False)
    led_common = led_config.get("common", "anode")
    led_pins = led_config.get("pins", {})
    led_brightness = led_config.get("brightness", {})

    log_base_dir = Path(logging_config["log_base_dir"])
    weather_log_dir = log_base_dir / "weather"
    flush_after_write = logging_config.get("flush_after_write", True)

    state = AppState()

    last_oled_update = 0.0
    last_terminal_print = 0.0

    print("SailSense App startet")
    print(f"GPS: {gps_port} @ {gps_baudrate}")
    print(f"BME280: {hex(bme_address)}")
    print(f"Weather raw: {raw_interval}s, display Ø: {display_window}s, storage: {storage_interval}s")
    print(f"OLED: {hex(oled_address)} {oled_width}x{oled_height}")
    print(f"Weather logs: {weather_log_dir}")
    print("Abbruch mit Strg+C")

    try:
        with ExitStack() as stack:
            gps = stack.enter_context(GPSReader(gps_port, gps_baudrate))
            bme = stack.enter_context(BME280Reader(i2c_address=bme_address))
            oled = stack.enter_context(OLEDDisplay(oled_width, oled_height, oled_address))

            weather_logger = stack.enter_context(
                CsvLogger(
                    log_dir=weather_log_dir,
                    prefix="weather_15min",
                    fieldnames=WEATHER_FIELDNAMES,
                    flush_after_write=flush_after_write,
                )
            )

            weather_service = WeatherService(
                bme_reader=bme,
                csv_logger=weather_logger,
                raw_read_interval_seconds=raw_interval,
                display_average_seconds=display_window,
                storage_interval_seconds=storage_interval,
                history_points=history_points,
            )

            led = None
            if led_enabled:
                led = stack.enter_context(
                    StatusLED(
                        red_pin=led_pins["red"],
                        green_pin=led_pins["green"],
                        blue_pin=led_pins["blue"],
                        common=led_common,
                        red_brightness=led_brightness.get("red", 1.0),
                        green_brightness=led_brightness.get("green", 1.0),
                        blue_brightness=led_brightness.get("blue", 1.0),
                    )
                )
                led.blink("blue", times=2, on_time=0.15, off_time=0.15)

            buttons = stack.enter_context(
                ButtonController(
                    pins=pins,
                    bounce_time=bounce_time,
                    hold_time=hold_time,
                )
            )

            buttons.bind(on_press=make_button_handler(state, oled, led))

            oled.show_status(
                "SailSense",
                [
                    "App startet",
                    "WeatherService",
                    "GPS wartet...",
                    "Buttons OK",
                ],
            )

            print("BME280 stabilisiert sich kurz ...")
            for _ in range(3):
                weather_service.tick(force_read=True)
                time.sleep(1)

            if led is not None:
                led.set_color("green")

            print("App laeuft.")

            while True:
                now = time.monotonic()

                gps_point = gps.read_point()
                if gps_point is not None:
                    state.latest_gps = gps_point
                    state.gps_point_count += 1

                weather_average = weather_service.tick()
                if weather_average is not None:
                    state.latest_weather = weather_average

                state.weather_history_count = len(weather_service.get_history())

                if now - last_oled_update >= oled_update_interval and state.mode == "pages":
                    render(oled, state)
                    last_oled_update = now

                if now - last_terminal_print >= 5:
                    latest_gps = state.latest_gps
                    latest_weather = state.latest_weather

                    print(
                        f"GPS pts:{state.gps_point_count} | "
                        f"{latest_gps.get('sats', '--')} sats | "
                        f"{format_value(latest_gps.get('speed_kn'), 'kn', 1)} | "
                        f"{format_value(latest_weather.get('temp_c'), 'C', 1)} | "
                        f"{format_value(latest_weather.get('humidity_pct'), '%', 0)} | "
                        f"{format_value(latest_weather.get('pressure_hpa'), 'hPa', 1)} | "
                        f"W15:{state.weather_history_count}"
                    )

                    last_terminal_print = now

                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nSailSense App beendet.")


if __name__ == "__main__":
    main()
