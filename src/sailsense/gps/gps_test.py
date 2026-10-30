import serial
import pynmea2

from sailsense.config import load_config


def main():
    config = load_config()

    port = config["gps"]["port"]
    baudrate = config["gps"]["baudrate"]

    print(f"Lese GPS-Daten von {port} mit {baudrate} Baud ...")
    print("Abbruch mit Strg+C")

    with serial.Serial(port, baudrate, timeout=1) as ser:
        while True:
            raw = ser.readline().decode("ascii", errors="replace").strip()

            if not raw:
                continue

            print(raw)

            try:
                msg = pynmea2.parse(raw)
            except pynmea2.ParseError:
                continue

            if msg.sentence_type == "RMC":
                print("Status:", getattr(msg, "status", None))
                print("Breite:", getattr(msg, "latitude", None))
                print("Länge:", getattr(msg, "longitude", None))
                print("Geschwindigkeit kn:", getattr(msg, "spd_over_grnd", None))
                print("Kurs:", getattr(msg, "true_course", None))

            elif msg.sentence_type == "GGA":
                print("Fix:", getattr(msg, "gps_qual", None))
                print("Satelliten:", getattr(msg, "num_sats", None))
                print("Höhe:", getattr(msg, "altitude", None), getattr(msg, "altitude_units", None))


if __name__ == "__main__":
    main()
