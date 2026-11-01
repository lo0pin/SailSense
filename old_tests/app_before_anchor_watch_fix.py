import os
import time
from pathlib import Path
from contextlib import ExitStack
from dataclasses import dataclass, field

from sailsense.config import load_config
from sailsense.gps.gps_reader import GPSReader
from sailsense.gps.track_manager import TrackManager
from sailsense.weather.bme280_reader import BME280Reader
from sailsense.weather.weather_service import WeatherService, WEATHER_FIELDNAMES
from sailsense.weather.history_loader import load_recent_weather_history
from sailsense.storage.csv_logger import CsvLogger
from sailsense.storage.track_index import (
    load_tracks_index,
    format_track_summary,
    format_track_detail_lines,
)
from sailsense.storage.track_points import load_track_points
from sailsense.display.oled_display import OLEDDisplay
from sailsense.display.weather_graphs import render_weather_overview, render_weather_graph
from sailsense.anchor.anchor_watch import AnchorWatch, save_anchor_runtime_settings
from sailsense.runtime_settings import (
    init_runtime_settings,
    render_settings_menu,
    change_current_setting,
    apply_oled_runtime_settings,
)
from sailsense.input.buttons import ButtonController, ButtonPins
from sailsense.system.power import poweroff, reboot
from sailsense.output.status_led import StatusLED
from sailsense.output.buzzer import Buzzer
from sailsense.export.gpx_exporter import export_track_csv_to_gpx


@dataclass
class AppState:
    screen_index: int = 0
    system_menu_index: int = 0
    mode: str = "pages"

    gps_point_count: int = 0
    weather_history_count: int = 0

    start_monotonic: float = field(default_factory=time.monotonic)

    latest_gps: dict = field(default_factory=dict)
    latest_weather: dict = field(default_factory=dict)

    weather_history: list = field(default_factory=list)
    barograph_config: dict = field(default_factory=dict)
    weather_graph_index: int = 0
    settings_menu_index: int = 0
    buzzer_signals: bool = True
    oled_timeout_seconds: float = 60.0
    oled_inverted: bool = False
    oled_contrast: int = 128
    led_heartbeat_enabled: bool = True
    anchor_watch: object = None
    anchor_edit_mode: str = ""
    anchor_stop_confirm: bool = False

    track_status: dict = field(default_factory=dict)
    track_list: list = field(default_factory=list)
    track_list_index: int = 0

    display_sleeping: bool = False
    last_button_monotonic: float = field(default_factory=time.monotonic)
    oled_timeout_seconds: float = 60.0
    led_heartbeat_interval_seconds: float = 20.0
    led_heartbeat_on_seconds: float = 0.15
    buzzer_key_clicks: bool = False


SCREENS = ["Status", "GPS", "Wetter", "Logging", "Tracks", "Anker", "Settings", "System"]
SYSTEM_ITEMS = ["Info", "Neustart", "Herunterfahren"]
WEATHER_GRAPHS = ["pressure", "temp", "humidity"]


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


def display_timeout_enabled(state: AppState) -> bool:
    return state.oled_timeout_seconds is not None and state.oled_timeout_seconds > 0


def wake_display(oled: OLEDDisplay, state: AppState):
    if state.display_sleeping:
        oled.wake()
        state.display_sleeping = False

    state.last_button_monotonic = time.monotonic()
    render(oled, state)


def sleep_display_if_needed(oled: OLEDDisplay, state: AppState):
    if not display_timeout_enabled(state):
        return

    if state.display_sleeping:
        return

    idle_seconds = time.monotonic() - state.last_button_monotonic

    if idle_seconds >= state.oled_timeout_seconds:
        oled.sleep()
        state.display_sleeping = True


def led_off(led):
    if led is None:
        return

    for method_name in ("off", "clear"):
        method = getattr(led, method_name, None)

        if callable(method):
            try:
                method()
                return
            except Exception:
                pass

    for color in ("off", "black", None):
        try:
            led.set_color(color)
            return
        except Exception:
            pass


def update_anchor_led(led, anchor_watch, now: float):
    """
    LED-Logik für Ankerwache.

    Normal aktiv/innerhalb:
      LED aus

    >90% Radius:
      gelb 50% Duty Cycle

    >100% Radius:
      rot/blau mit kurzen Dunkelpausen

    Akustischer Alarm wird separat behandelt.
    """
    if led is None or anchor_watch is None:
        return

    if not getattr(anchor_watch, "is_active", False):
        return

    zone = getattr(anchor_watch, "zone", "inside")

    if zone in ("inside", "off", "drop"):
        led_off(led)
        return

    if zone == "warning":
        # 50% Duty Cycle: 0.5s an, 0.5s aus
        phase = now % 1.0

        if phase < 0.5:
            led.set_color("yellow")
        else:
            led_off(led)

        return

    # Danger / outside_buffer / alarm:
    # rot 0.30s, dunkel 0.30s, blau 0.30s, dunkel 0.30s
    phase = now % 1.2

    if phase < 0.30:
        led.set_color("red")
    elif phase < 0.60:
        led_off(led)
    elif phase < 0.90:
        led.set_color("blue")
    else:
        led_off(led)


def render_anchor_page(oled: OLEDDisplay, state: AppState):
    anchor_watch = state.anchor_watch

    if anchor_watch is None:
        oled.show_status("Anker", ["deaktiviert"])
        return

    if getattr(anchor_watch, "is_active", False):
        dist = "--"
        radius = "--"
        ratio = "--"

        if anchor_watch.last_distance_m is not None:
            dist = f"{anchor_watch.last_distance_m:.0f}m"

        if anchor_watch.radius_m is not None:
            radius = f"{anchor_watch.radius_m:.0f}m"

        if anchor_watch.last_ratio is not None:
            ratio = f"{anchor_watch.last_ratio * 100:.0f}%"

        oled.show_status(
            "Anker",
            [
                "Wache aktiv",
                f"Dist: {dist} {ratio}",
                f"Radius: {radius}",
                anchor_watch.last_message[:21],
                "OK: oeffnen",
            ],
        )
        return

    oled.show_status(
        "Anker",
        [
            "Ankerwache",
            "OK: oeffnen",
            "BACK: Status",
        ],
    )


def render_anchor_watch_screen(oled: OLEDDisplay, state: AppState):
    anchor_watch = state.anchor_watch

    if anchor_watch is None:
        oled.show_status("Anker", ["deaktiviert"])
        return

    if state.anchor_stop_confirm:
        oled.show_status(
            "Anker Stop?",
            [
                "OK: stoppen",
                "BACK: weiter",
            ],
        )
        return

    if state.anchor_edit_mode == "radius":
        radius = "--"

        if anchor_watch.radius_m is not None:
            radius = f"{anchor_watch.radius_m:.0f}m"

        oled.show_status(
            "Radius",
            [
                f"Radius: {radius}",
                "UP/DOWN +/-1m",
                "OK: speichern",
                "BACK: speichern",
            ],
        )
        return

    if state.anchor_edit_mode == "buffer":
        oled.show_status(
            "Puffer",
            [
                f"Puffer: {anchor_watch.buffer_m:.0f}m",
                "UP/DOWN +/-1m",
                "OK: speichern",
                "BACK: speichern",
            ],
        )
        return

    oled.show_status("Anker", anchor_watch.status_lines())


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
        render_weather_overview(
            oled,
            history=state.weather_history,
            current_weather=state.latest_weather,
        )

    elif screen == "Logging":
        track = state.track_status or {}
        active = track.get("active", False)

        if active:
            oled.show_status(
                "GPS Track",
                [
                    "Status: AKTIV",
                    f"Dauer: {track.get('duration_text', '--')}",
                    f"Dist: {track.get('distance_nm', 0.0):.3f} nm",
                    f"Pts: {track.get('point_count', 0)}",
                    "OK: Marker",
                    "BACK: Stop?",
                ],
            )
        else:
            oled.show_status(
                "GPS Track",
                [
                    "Status: AUS",
                    f"GPS pts: {state.gps_point_count}",
                    f"Uptime: {uptime_text(state.start_monotonic)}",
                    "OK: Start?",
                    "DOWN: weiter",
                ],
            )

    elif screen == "Tracks":
        tracks = state.track_list or []

        if not tracks:
            oled.show_status(
                "Tracks",
                [
                    "Keine Tracks",
                    "OK: aktual.",
                    "DOWN: weiter",
                ],
            )
        else:
            lines = []

            for idx, row in enumerate(tracks[:4]):
                lines.append(format_track_summary(row, selected=(idx == 0)))

            lines.append("OK: Details")

            oled.show_status("Tracks", lines)

    elif screen == "Anker":
        render_anchor_page(oled, state)

    elif screen == "Settings":
        oled.show_status(
            "Settings",
            [
                "OK: Einstellungen",
                "UP/DOWN: Seite",
                "BACK: Status",
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


def render_track_browser(oled: OLEDDisplay, state: AppState):
    tracks = state.track_list or []

    if not tracks:
        oled.show_status(
            "Tracks",
            [
                "Keine Tracks",
                "gefunden",
                "",
                "BACK: zurueck",
            ],
        )
        return

    if state.track_list_index >= len(tracks):
        state.track_list_index = 0

    row = tracks[state.track_list_index]
    lines = format_track_detail_lines(
        row,
        index=state.track_list_index,
        total=len(tracks),
    )

    oled.show_status("Track Detail", lines)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def render_track_map(oled: OLEDDisplay, state: AppState):
    tracks = state.track_list or []

    if not tracks:
        oled.show_status("Track Karte", ["Keine Tracks", "BACK: zurueck"])
        return

    if state.track_list_index >= len(tracks):
        state.track_list_index = 0

    row = tracks[state.track_list_index]

    track_file = row.get("track_file")
    track_id = row.get("track_id", "track")

    if not track_file:
        oled.show_status("Track Karte", ["Keine Datei", track_id[-15:], "BACK"])
        return

    points = load_track_points(track_file, max_points=800)

    distance_nm = _safe_float(row.get("distance_nm"))
    point_count = row.get("point_count", "0")

    title = f"Karte {state.track_list_index + 1}/{len(tracks)}"
    info = f"{distance_nm:.2f}nm {point_count}pts"

    oled.show_track_map(
        points,
        title=title,
        info_lines=[info],
    )


def render_weather_graph_screen(oled: OLEDDisplay, state: AppState):
    if state.weather_graph_index >= len(WEATHER_GRAPHS):
        state.weather_graph_index = 0

    metric = WEATHER_GRAPHS[state.weather_graph_index]

    render_weather_graph(
        oled,
        history=state.weather_history,
        current_weather=state.latest_weather,
        metric=metric,
        config=state.barograph_config,
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

    elif state.mode == "track_start_confirm":
        render_confirm(oled, "Track starten?", "GPS-Track aufzeichnen")

    elif state.mode == "track_stop_confirm":
        render_confirm(oled, "Track stoppen?", "Aufzeichnung beenden")

    elif state.mode == "track_browser":
        render_track_browser(oled, state)

    elif state.mode == "weather_graph":
        render_weather_graph_screen(oled, state)

    elif state.mode == "anchor_watch":
        render_anchor_watch_screen(oled, state)

    elif state.mode == "settings_menu":
        render_settings_menu(oled, state)

    elif state.mode == "track_map":
        render_track_map(oled, state)


def make_button_handler(
    state: AppState,
    oled: OLEDDisplay,
    led=None,
    track_manager=None,
    gpx_output_dir=None,
    buzzer=None,
):
    def handle_button(name: str):
        # Wenn das Display schläft: erster Tastendruck weckt nur auf
        # und wird absichtlich NICHT als Menüaktion verarbeitet.
        if state.display_sleeping:
            wake_display(oled, state)
            return

        state.last_button_monotonic = time.monotonic()

        if state.buzzer_key_clicks:
            buzzer_play(buzzer, "click")

        if state.mode == "pages":
            if name == "UP":
                state.screen_index = (state.screen_index - 1) % len(SCREENS)

            elif name == "DOWN":
                state.screen_index = (state.screen_index + 1) % len(SCREENS)

            elif name == "BACK":
                current_screen = SCREENS[state.screen_index]

            if name == "BACK" and current_screen != "Status":
                logging_active = False

                if current_screen == "Logging" and track_manager is not None:
                    try:
                        status = track_manager.get_status()

                        if isinstance(status, dict):
                            logging_active = bool(status.get("active") or status.get("is_active"))
                        else:
                            logging_active = bool(
                                getattr(status, "active", False)
                                or getattr(status, "is_active", False)
                            )
                    except Exception:
                        logging_active = False

                # Sicherheitsausnahme:
                # Bei aktivem Track bleibt BACK auf Logging weiterhin "Track stoppen?".
                if not (current_screen == "Logging" and logging_active):
                    state.screen_index = 0
                    return

                if (
                    current_screen == "Logging"
                    and track_manager is not None
                    and track_manager.active
                ):
                    state.mode = "track_stop_confirm"
                else:
                    state.screen_index = 0

            elif name == "OK":
                current_screen = SCREENS[state.screen_index]

                if current_screen == "System":
                    state.mode = "system_menu"
                    state.system_menu_index = 0

                elif current_screen == "Anker":
                    state.mode = "anchor_watch"
                    state.anchor_edit_mode = ""
                    state.anchor_stop_confirm = False

                elif current_screen == "Settings":
                    state.mode = "settings_menu"
                    state.settings_menu_index = 0

                elif current_screen == "Wetter":
                    state.mode = "weather_graph"
                    state.weather_graph_index = 0

                elif current_screen == "Logging":
                    if track_manager is None:
                        oled.show_status("Track", ["nicht verfuegbar"])
                        time.sleep(0.8)

                    elif track_manager.active:
                        marker = time.strftime("marker_%H%M%S")
                        track_manager.set_marker(marker)

                        oled.show_status(
                            "Marker",
                            [
                                marker,
                                "gesetzt",
                                "naechster Punkt",
                            ],
                        )

                        buzzer_play(buzzer, "marker")

                        if led is not None:
                            led.blink("yellow", times=2, on_time=0.08, off_time=0.08)
                            led.set_color("green")

                        time.sleep(0.7)

                    else:
                        state.mode = "track_start_confirm"

                elif current_screen == "Tracks":
                    if track_manager is not None:
                        state.track_list = load_tracks_index(track_manager.index_file, limit=20)
                        state.track_list_index = 0

                    if state.track_list:
                        state.mode = "track_browser"
                    else:
                        oled.show_status("Tracks", ["Keine Tracks", "gefunden"])
                        time.sleep(0.8)

        elif state.mode == "anchor_watch":
            anchor_watch = state.anchor_watch

            if anchor_watch is None:
                if name == "BACK":
                    state.mode = "pages"
                return

            if state.anchor_stop_confirm:
                if name == "OK":
                    anchor_watch.stop()
                    state.anchor_stop_confirm = False
                    state.anchor_edit_mode = ""
                    state.mode = "pages"
                    led_off(led)

                elif name == "BACK":
                    state.anchor_stop_confirm = False

                return

            if state.anchor_edit_mode == "radius":
                if name == "UP":
                    anchor_watch.adjust_radius(+1)

                elif name == "DOWN":
                    anchor_watch.adjust_radius(-1)

                elif name in ("OK", "BACK"):
                    save_anchor_runtime_settings(anchor_watch)
                    state.anchor_edit_mode = ""

                return

            if state.anchor_edit_mode == "buffer":
                if name == "UP":
                    anchor_watch.adjust_buffer(+1)

                elif name == "DOWN":
                    anchor_watch.adjust_buffer(-1)

                elif name in ("OK", "BACK"):
                    save_anchor_runtime_settings(anchor_watch)
                    state.anchor_edit_mode = ""

                return

            if anchor_watch.mode == "OFF":
                if name == "OK":
                    ok = anchor_watch.set_drop(state.latest_gps)

                    if not ok:
                        oled.show_status(
                            "Anker",
                            [
                                "Drop fehlgeschl.",
                                anchor_watch.last_message[:21],
                            ],
                        )
                        time.sleep(0.4)

                elif name == "BACK":
                    state.mode = "pages"

                return

            if anchor_watch.mode == "DROP_SET":
                if name == "OK":
                    ok = anchor_watch.set_radius_from_current_position(
                        state.latest_gps
                    )

                    if ok:
                        save_anchor_runtime_settings(anchor_watch)
                    else:
                        oled.show_status(
                            "Anker",
                            [
                                "Radius fehlgeschl.",
                                anchor_watch.last_message[:21],
                            ],
                        )
                        time.sleep(0.4)

                elif name == "BACK":
                    anchor_watch.stop()
                    state.mode = "pages"

                return

            if anchor_watch.mode in ("ACTIVE", "ALARM"):
                if name == "UP":
                    state.anchor_edit_mode = "radius"

                elif name == "DOWN":
                    state.anchor_edit_mode = "buffer"

                elif name == "OK":
                    state.anchor_stop_confirm = True

                elif name == "BACK":
                    # Wache läuft im Hintergrund weiter.
                    state.mode = "pages"

                return

        elif state.mode == "weather_graph":
            if name == "DOWN":
                state.weather_graph_index = (state.weather_graph_index + 1) % len(WEATHER_GRAPHS)

            elif name == "UP":
                state.weather_graph_index = (state.weather_graph_index - 1) % len(WEATHER_GRAPHS)

            elif name == "BACK":
                state.mode = "pages"

            elif name == "OK":
                # In der Graphansicht bewusst keine Funktion.
                pass

        elif state.mode == "track_browser":
            tracks = state.track_list or []

            if name == "UP" and tracks:
                state.track_list_index = (state.track_list_index - 1) % len(tracks)

            elif name == "DOWN" and tracks:
                state.track_list_index = (state.track_list_index + 1) % len(tracks)

            elif name == "BACK":
                state.mode = "pages"

            elif name == "OK":
                state.mode = "track_map"

        elif state.mode == "track_map":
            tracks = state.track_list or []

            if name == "UP" and tracks:
                state.track_list_index = (state.track_list_index - 1) % len(tracks)

            elif name == "DOWN" and tracks:
                state.track_list_index = (state.track_list_index + 1) % len(tracks)

            elif name in ("BACK", "OK"):
                state.mode = "track_browser"

        elif state.mode == "settings_menu":
            if name == "DOWN":
                state.settings_menu_index = (
                    state.settings_menu_index + 1
                ) % 6

            elif name == "UP":
                state.settings_menu_index = (
                    state.settings_menu_index - 1
                ) % 6

            elif name == "OK":
                change_current_setting(
                    state,
                    oled=oled,
                    buzzer=buzzer,
                    led=led,
                )

            elif name == "BACK":
                state.mode = "pages"

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
                            "SailSense v0.3",
                            f"GPS: {state.gps_point_count}",
                            f"W15: {state.weather_history_count}",
                            f"Tracks: {len(state.track_list)}",
                            f"Up: {uptime_text(state.start_monotonic)}",
                        ],
                    )
                    time.sleep(1.2)

                elif selected == "Neustart":
                    state.mode = "reboot_confirm"

                elif selected == "Herunterfahren":
                    state.mode = "shutdown_confirm"

        elif state.mode == "track_start_confirm":
            if name == "OK":
                try:
                    stats = track_manager.start(mode="manual")
                    state.track_status = track_manager.get_status()
                    oled.show_status("Track", ["gestartet", stats.track_id[-15:]])

                    buzzer_play(buzzer, "track_start")

                    if led is not None:
                        if not getattr(state, "led_heartbeat_enabled", True):
                            return

                        led.blink("green", times=2, on_time=0.12, off_time=0.12)
                        led.set_color("green")

                    time.sleep(0.8)
                    state.mode = "pages"

                except Exception as exc:
                    oled.show_status("Track Fehler", [str(exc)[:20]])

                    buzzer_play(buzzer, "error")

                    if led is not None:
                        led.blink("red", times=3)
                        led.set_color("green")

                    time.sleep(1.2)
                    state.mode = "pages"

            elif name == "BACK":
                state.mode = "pages"

        elif state.mode == "track_stop_confirm":
            if name == "OK":
                try:
                    finished = track_manager.stop()

                    if finished:
                        gpx_path = None

                        try:
                            track_csv = track_manager.log_dir / f"{finished.track_id}.csv"
                            gpx_path = export_track_csv_to_gpx(
                                track_csv,
                                output_dir=gpx_output_dir,
                            )

                        except Exception as export_exc:
                            oled.show_status(
                                "GPX Fehler",
                                [
                                    finished.track_id[-15:],
                                    str(export_exc)[:20],
                                ],
                            )

                            buzzer_play(buzzer, "error")

                            if led is not None:
                                led.blink("red", times=3)
                                led.set_color("green")

                            time.sleep(1.5)

                        if gpx_path is not None:
                            oled.show_status(
                                "Track beendet",
                                [
                                    finished.track_id[-15:],
                                    f"{finished.distance_nm:.3f} nm",
                                    f"{finished.point_count} Punkte",
                                    "GPX exportiert",
                                ],
                            )
                        else:
                            oled.show_status(
                                "Track beendet",
                                [
                                    finished.track_id[-15:],
                                    f"{finished.distance_nm:.3f} nm",
                                    f"{finished.point_count} Punkte",
                                    "CSV gespeichert",
                                ],
                            )

                    buzzer_play(buzzer, "track_stop")

                    if led is not None:
                        led.blink("yellow", times=2, on_time=0.12, off_time=0.12)
                        led.set_color("green")

                    state.track_status = track_manager.get_status()
                    state.track_list = load_tracks_index(track_manager.index_file, limit=20)
                    state.track_list_index = 0

                    time.sleep(1.2)
                    state.mode = "pages"

                except Exception as exc:
                    oled.show_status("Track Fehler", [str(exc)[:20]])

                    buzzer_play(buzzer, "error")

                    if led is not None:
                        led.blink("red", times=3)
                        led.set_color("green")

                    time.sleep(1.2)
                    state.mode = "pages"

            elif name == "BACK":
                state.mode = "pages"

        elif state.mode == "shutdown_confirm":
            if name == "OK":
                oled.show_status("SailSense", ["Fahre herunter..."])

                buzzer_play(buzzer, "warning")
                time.sleep(0.15)

                if led is not None:
                    led.set_color("red")

                poweroff()
                return

            elif name == "BACK":
                state.mode = "system_menu"

        elif state.mode == "reboot_confirm":
            if name == "OK":
                oled.show_status("SailSense", ["Starte neu..."])

                buzzer_play(buzzer, "warning")
                time.sleep(0.15)

                if led is not None:
                    led.set_color("red")

                reboot()
                return

            elif name == "BACK":
                state.mode = "system_menu"

        render(oled, state)

    return handle_button


def buzzer_play(buzzer, pattern: str):
    """
    Buzzer-Muster sicher abspielen.
    Fehler beim Buzzer sollen die App nie töten.
    """
    if buzzer is None:
        return

    if pattern != "alarm" and not getattr(buzzer, "signals_enabled", True):
        return

    try:
        buzzer.play(pattern)
    except Exception as exc:
        print(f"Buzzer-Fehler: {exc}")


def update_status_led(led, state: AppState, track_manager, now: float):
    """
    Nicht-blockierende Status-LED-Logik.

    Kein Track:
        kurzer grüner Heartbeat alle X Sekunden.

    Track aktiv:
        grün dauerhaft.

    Event-Blinks wie Marker/Start/Stop bleiben davon unberührt;
    danach übernimmt dieser Heartbeat wieder den Normalzustand.
    """
    if led is None:
        return

    if track_manager is not None and track_manager.active:
        led.set_color("green")
        return

    interval = max(1.0, float(state.led_heartbeat_interval_seconds))
    on_time = max(0.05, float(state.led_heartbeat_on_seconds))

    phase = now % interval

    if phase < on_time:
        led.set_color("green")
    else:
        led.off()


def main():
    config = load_config()

    gps_config = config["gps"]
    bme_config = config["bme280"]
    weather_service_config = config["weather_service"]
    barograph_config = config.get("barograph", {})
    oled_config = config["oled"]
    button_config = config["buttons"]
    led_config = config.get("status_led", {})
    buzzer_config = config.get("buzzer", {})
    logging_config = config["logging"]
    track_config = config["track"]
    export_config = config.get("export", {})

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
    oled_timeout_seconds = float(oled_config.get("timeout_seconds", 60))

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
    led_heartbeat_interval = float(led_config.get("heartbeat_interval_seconds", 20))
    led_heartbeat_on = float(led_config.get("heartbeat_on_seconds", 0.15))

    buzzer_enabled = buzzer_config.get("enabled", False)
    buzzer_pin = buzzer_config.get("pin", 12)
    buzzer_kind = buzzer_config.get("kind", "passive")
    buzzer_active_high = buzzer_config.get("active_high", True)
    buzzer_volume = buzzer_config.get("volume", 0.18)
    buzzer_passive_frequency = buzzer_config.get("passive_frequency", 1800)
    buzzer_frequencies = buzzer_config.get("frequencies", {})
    buzzer_key_clicks = buzzer_config.get("key_clicks", False)

    log_base_dir = Path(logging_config["log_base_dir"])
    weather_log_dir = log_base_dir / "weather"

    gpx_output_dir = Path(
        export_config.get("gpx_output_dir", "/home/user/sailsense/data/exports")
    )
    gpx_output_dir.mkdir(parents=True, exist_ok=True)

    flush_after_write = logging_config.get("flush_after_write", True)

    state = AppState()
    init_runtime_settings(state, config)
    anchor_config = config.get("anchor_watch", {})
    anchor_watch = None

    if anchor_config.get("enabled", True):
        anchor_watch = AnchorWatch.from_config(anchor_config)

    state.anchor_watch = anchor_watch
    state.barograph_config = barograph_config
    state.oled_timeout_seconds = oled_timeout_seconds
    state.led_heartbeat_interval_seconds = led_heartbeat_interval
    state.led_heartbeat_on_seconds = led_heartbeat_on
    state.buzzer_key_clicks = buzzer_key_clicks
    state.last_button_monotonic = time.monotonic()

    last_oled_update = 0.0
    last_terminal_print = 0.0
    last_track_list_update = 0.0

    print("SailSense App startet")
    print(f"GPS: {gps_port} @ {gps_baudrate}")
    print(f"BME280: {hex(bme_address)}")
    print(
        f"Weather raw: {raw_interval}s, display Ø: {display_window}s, "
        f"storage: {storage_interval}s"
    )
    print(f"OLED: {hex(oled_address)} {oled_width}x{oled_height}, timeout {oled_timeout_seconds}s")
    print(f"Weather logs: {weather_log_dir}")
    print(f"GPX exports: {gpx_output_dir}")
    print("Abbruch mit Strg+C")

    try:
        with ExitStack() as stack:
            gps = stack.enter_context(GPSReader(gps_port, gps_baudrate))
            bme = stack.enter_context(BME280Reader(i2c_address=bme_address))
            oled = stack.enter_context(OLEDDisplay(oled_width, oled_height, oled_address))
            apply_oled_runtime_settings(oled, state)

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

            loaded_history = load_recent_weather_history(
                weather_log_dir,
                max_points=history_points,
            )

            for row in loaded_history:
                weather_service.history.append(row)

            state.weather_history = weather_service.get_history()
            state.weather_history_count = len(state.weather_history)
            print(f"Weather history geladen: {state.weather_history_count} Punkte")

            track_manager = TrackManager(
                log_dir=track_config["log_dir"],
                index_file=track_config["index_file"],
                point_interval_seconds=track_config.get("point_interval_seconds", 5),
                min_sats=track_config.get("min_sats", 5),
                max_hdop=track_config.get("max_hdop", 5.0),
            )

            state.track_status = track_manager.get_status()
            state.track_list = load_tracks_index(track_manager.index_file, limit=20)
            state.track_list_index = 0
            print(f"Trackliste geladen: {len(state.track_list)} Track(s)")

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

            buzzer = None

            if buzzer_enabled:
                buzzer = stack.enter_context(
                    Buzzer(
                        pin=buzzer_pin,
                        kind=buzzer_kind,
                        active_high=buzzer_active_high,
                        volume=buzzer_volume,
                        passive_frequency=buzzer_passive_frequency,
                        frequencies=buzzer_frequencies,
                    )
                )
                try:
                    buzzer.signals_enabled = bool(state.buzzer_signals)
                except Exception:
                    pass

            buttons = stack.enter_context(
                ButtonController(
                    pins=pins,
                    bounce_time=bounce_time,
                    hold_time=hold_time,
                )
            )

            buttons.bind(
                on_press=make_button_handler(
                    state,
                    oled,
                    led,
                    track_manager,
                    gpx_output_dir,
                    buzzer,
                )
            )

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
                led.off()

            print("App laeuft.")

            while True:
                now = time.monotonic()

                gps_point = gps.read_point()

                if gps_point is not None:
                    state.latest_gps = gps_point
                    if state.anchor_watch is not None:
                        anchor_event = state.anchor_watch.update(gps_point, now)

                        if anchor_event == "alarm_start":
                            state.mode = "anchor_watch"
                            state.anchor_edit_mode = ""
                            state.anchor_stop_confirm = False

                            try:
                                state.screen_index = SCREENS.index("Anker")
                            except ValueError:
                                pass

                            try:
                                oled.wake()
                            except Exception:
                                pass

                    state.gps_point_count += 1

                    if track_manager.active:
                        written = track_manager.add_point(gps_point)

                        if written and led is not None:
                            led.set_color("green")

                    state.track_status = track_manager.get_status()

                weather_average = weather_service.tick()

                if weather_average is not None:
                    state.latest_weather = weather_average

                state.weather_history = weather_service.get_history()
                state.weather_history_count = len(state.weather_history)

                if (
                    not state.display_sleeping
                    and now - last_oled_update >= oled_update_interval
                    and state.mode == "pages"
                ):
                    render(oled, state)
                    last_oled_update = now

                if now - last_track_list_update >= 10:
                    state.track_list = load_tracks_index(track_manager.index_file, limit=20)

                    if state.track_list_index >= len(state.track_list):
                        state.track_list_index = 0

                    last_track_list_update = now

                sleep_display_if_needed(oled, state)

                if (
                    state.anchor_watch is not None
                    and getattr(state.anchor_watch, "is_active", False)
                ):
                    update_anchor_led(led, state.anchor_watch, now)

                    if state.anchor_watch.alarm_sound_due(now):
                        buzzer_play(buzzer, "alarm")
                else:
                    update_status_led(led, state, track_manager, now)

                if now - last_terminal_print >= 5:
                    latest_gps = state.latest_gps
                    latest_weather = state.latest_weather
                    track = state.track_status or {}

                    track_text = "TRK:on" if track.get("active") else "TRK:off"

                    print(
                        f"GPS pts:{state.gps_point_count} | "
                        f"{latest_gps.get('sats', '--')} sats | "
                        f"{format_value(latest_gps.get('speed_kn'), 'kn', 1)} | "
                        f"{format_value(latest_weather.get('temp_c'), 'C', 1)} | "
                        f"{format_value(latest_weather.get('humidity_pct'), '%', 0)} | "
                        f"{format_value(latest_weather.get('pressure_hpa'), 'hPa', 1)} | "
                        f"W15:{state.weather_history_count} | "
                        f"{track_text}"
                    )

                    last_terminal_print = now

                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nSailSense App beendet.")


if __name__ == "__main__":
    main()
