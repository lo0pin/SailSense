import serial
import pynmea2

PORT = "/dev/ttyACM0"
BAUD = 9600

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    print(f"Lese GPS-Daten von {PORT} ...")

    while True:
        raw = ser.readline().decode("ascii", errors="replace").strip()

        if not raw:
            continue

        print(raw)

        try:
            msg = pynmea2.parse(raw)

            if msg.sentence_type == "GGA":
                print("Fix:", msg.gps_qual)
                print("Satelliten:", msg.num_sats)
                print("Höhe:", msg.altitude, msg.altitude_units)

            if msg.sentence_type == "RMC":
                print("Status:", msg.status)
                print("Breite:", msg.latitude)
                print("Länge:", msg.longitude)
                print("Geschwindigkeit kn:", msg.spd_over_grnd)
                print("Kurs:", msg.true_course)

        except pynmea2.ParseError:
            pass
