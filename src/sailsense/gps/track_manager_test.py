import time

from sailsense.config import load_config
from sailsense.gps.gps_reader import GPSReader
from sailsense.gps.track_manager import TrackManager


def main():
    config = load_config()

    gps_config = config["gps"]
    track_config = config["track"]

    gps_port = gps_config["port"]
    gps_baudrate = gps_config["baudrate"]

    duration_seconds = 60

    manager = TrackManager(
        log_dir=track_config["log_dir"],
        index_file=track_config["index_file"],
        point_interval_seconds=track_config.get("point_interval_seconds", 5),
        min_sats=track_config.get("min_sats", 5),
        max_hdop=track_config.get("max_hdop", 5.0),
    )

    print("SailSense TrackManager-Test")
    print(f"GPS: {gps_port} @ {gps_baudrate}")
    print(f"Dauer: {duration_seconds} s")
    print(f"Track-Intervall: {track_config.get('point_interval_seconds', 5)} s")
    print(f"Min. Satelliten: {track_config.get('min_sats', 5)}")
    print(f"Max. HDOP: {track_config.get('max_hdop', 5.0)}")
    print("Abbruch mit Strg+C")
    print()

    try:
        with GPSReader(gps_port, gps_baudrate) as gps:
            stats = manager.start(mode="test")
            print(f"Track gestartet: {stats.track_id}")

            start = time.monotonic()
            last_print = 0.0

            while time.monotonic() - start < duration_seconds:
                point = gps.read_point()

                if point is not None:
                    written = manager.add_point(point)

                    status = manager.get_status()

                    if written:
                        print(
                            f"GESCHRIEBEN | "
                            f"{point.get('timestamp_utc')} | "
                            f"{point.get('sats')} sats | "
                            f"{point.get('speed_kn')} kn | "
                            f"{status['point_count']} pts | "
                            f"{status['distance_nm']:.4f} nm"
                        )

                    elif time.monotonic() - last_print >= 5:
                        print(
                            f"GPS live     | "
                            f"{point.get('timestamp_utc')} | "
                            f"{point.get('sats')} sats | "
                            f"{point.get('speed_kn')} kn | "
                            f"{status['point_count']} pts"
                        )
                        last_print = time.monotonic()

                time.sleep(0.1)

            finished = manager.stop()
            print()
            print("Track beendet:")
            print(f"ID:       {finished.track_id}")
            print(f"Dauer:    {finished.duration_seconds:.1f} s")
            print(f"Punkte:   {finished.point_count}")
            print(f"Distanz:  {finished.distance_nm:.4f} nm / {finished.distance_km:.4f} km")

    except KeyboardInterrupt:
        print("\nAbbruch.")
        finished = manager.stop()
        if finished:
            print(f"Track sauber beendet: {finished.track_id}")


if __name__ == "__main__":
    main()
