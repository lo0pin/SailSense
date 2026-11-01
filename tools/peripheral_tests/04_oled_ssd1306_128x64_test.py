#!/usr/bin/env python3
import time
import board
import busio
from PIL import Image, ImageDraw
import adafruit_ssd1306

ADDRESS = 0x3C
WIDTH = 128
HEIGHT = 64

print("=== SailSense OLED SSD1306 128x64 Test ===")

i2c = busio.I2C(board.SCL, board.SDA)

try:
    display = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=ADDRESS)

    display.fill(0)
    display.show()

    image = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=255, fill=0)
    draw.text((8, 8), "SailSense", fill=255)
    draw.text((8, 24), "SSD1306 OK", fill=255)
    draw.text((8, 40), "128x64 0x3C", fill=255)

    display.image(image)
    display.show()

    print("Anzeige sollte 10 Sekunden sichtbar sein.")
    time.sleep(10)

    display.fill(0)
    display.show()

    print("OLED SSD1306 OK.")

except Exception as e:
    print("OLED SSD1306 FEHLER:")
    print(repr(e))
    print("""
Prüfen:
- i2cdetect zeigt 0x3C?
- VCC/GND/SDA/SCL korrekt?
- Service wirklich gestoppt?
""")
    raise
