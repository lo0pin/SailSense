#!/usr/bin/env python3
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 9600
SECONDS = 20

print("=== SailSense GPS Test ===")
print(f"Port: {PORT}")
print(f"Baud: {BAUD}")
print(f"Dauer: {SECONDS}s")

gga_seen = False
rmc_seen = False
lines_seen = 0

try:
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        start = time.time()

        while time.time() - start < SECONDS:
            raw = ser.readline()

            if not raw:
                continue

            try:
                line = raw.decode("ascii", errors="replace").strip()
            except Exception:
                line = str(raw)

            if not line:
                continue

            lines_seen += 1

            if line.startswith(("$GPGGA", "$GNGGA")):
                gga_seen = True
                print("GGA:", line)

            elif line.startswith(("$GPRMC", "$GNRMC")):
                rmc_seen = True
                print("RMC:", line)

            elif lines_seen <= 10:
                print("RAW:", line)

    print("\nZusammenfassung:")
    print("NMEA-Zeilen:", lines_seen)
    print("GGA gesehen:", gga_seen)
    print("RMC gesehen:", rmc_seen)

    if lines_seen == 0:
        print("GPS FEHLER: keine Daten empfangen.")
    elif not (gga_seen or rmc_seen):
        print("GPS WARNUNG: Daten da, aber keine GGA/RMC-Sätze erkannt.")
    else:
        print("GPS OK.")

except Exception as e:
    print("GPS FEHLER:")
    print(repr(e))
    print("""
Prüfen:
- Ist der Port richtig? Häufig: /dev/ttyACM0 oder /dev/ttyAMA0 oder /dev/serial0
- GPS VCC/GND verbunden?
- TX vom GPS an RX des Pi?
- Baudrate 9600?
""")
    raise
