#!/usr/bin/env python3
import subprocess
import shutil

print("=== SailSense I2C Scan ===")

if not shutil.which("i2cdetect"):
    print("FEHLER: i2cdetect nicht gefunden. Installiere mit:")
    print("sudo apt install i2c-tools")
    raise SystemExit(1)

for mode in ["", "-r"]:
    cmd = ["i2cdetect"]
    if mode:
        cmd.append(mode)
    cmd += ["-y", "1"]

    print("\nBefehl:", " ".join(cmd))
    subprocess.run(cmd, check=False)

print("""
Erwartung im normalen alten Setup ungefähr:
0x3C = OLED alt
0x57 = RTC-EEPROM
0x68 = RTC, oft als UU
0x76 = BME280

OLED-only mit neuem Display:
0x3C sollte erscheinen.
""")
