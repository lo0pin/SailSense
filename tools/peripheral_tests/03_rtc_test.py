#!/usr/bin/env python3
import subprocess
from pathlib import Path

print("=== SailSense RTC Test ===")

rtc_base = Path("/sys/class/rtc")

if rtc_base.exists():
    rtcs = sorted(rtc_base.glob("rtc*"))
    print("Gefundene RTCs:", ", ".join(r.name for r in rtcs) or "keine")

    for rtc in rtcs:
        name = rtc.name
        date_file = rtc / "date"
        time_file = rtc / "time"
        name_file = rtc / "name"

        print(f"\n{name}:")
        if name_file.exists():
            print("Name:", name_file.read_text().strip())
        if date_file.exists():
            print("Datum:", date_file.read_text().strip())
        if time_file.exists():
            print("Zeit:", time_file.read_text().strip())
else:
    print("/sys/class/rtc nicht gefunden.")

print("\nBefehl: hwclock -r")
result = subprocess.run(["sudo", "hwclock", "-r"], text=True, capture_output=True)

if result.returncode == 0:
    print(result.stdout.strip())
    print("RTC OK.")
else:
    print("RTC FEHLER:")
    print(result.stderr.strip())
    print("""
Prüfen:
- i2cdetect zeigt bei 0x68 idealerweise UU
- Batterie eingesetzt?
- RTC korrekt im System eingebunden?
""")
