#!/usr/bin/env python3
import time
import board
import busio
from adafruit_bme280 import advanced as adafruit_bme280

ADDRESS = 0x76

print("=== SailSense BME280 Test ===")
print(f"Adresse: 0x{ADDRESS:02X}")

i2c = busio.I2C(board.SCL, board.SDA)

try:
    bme = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=ADDRESS)

    bme.sea_level_pressure = 1013.25
    bme.iir_filter = adafruit_bme280.IIR_FILTER_X16

    for i in range(10):
        print(
            f"{i+1:02d}: "
            f"{bme.temperature:6.2f} °C | "
            f"{bme.humidity:6.2f} % | "
            f"{bme.pressure:7.2f} hPa"
        )
        time.sleep(1)

    print("BME280 OK.")

except Exception as e:
    print("BME280 FEHLER:")
    print(repr(e))
    print("""
Prüfen:
- VCC am BME verbunden?
- GND gemeinsam?
- SDA/SCL richtig?
- Adresse wirklich 0x76?
- i2cdetect zeigt 0x76?
""")
    raise
