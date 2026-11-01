#!/usr/bin/env python3
import time
from gpiozero import LED

# BCM-Pins eintragen.
# Beispielwerte sind Platzhalter.
LEDS = {
    "green": 5,
    "red": 6,
    "yellow": 13,
}

print("=== SailSense LED Test ===")
print("Verwendet BCM-Pins:", LEDS)

objects = {}

try:
    for name, pin in LEDS.items():
        objects[name] = LED(pin)

    for name, led in objects.items():
        print(f"Teste LED: {name}")
        for _ in range(3):
            led.on()
            time.sleep(0.3)
            led.off()
            time.sleep(0.3)

    print("Alle LEDs gemeinsam 2 Sekunden EIN.")
    for led in objects.values():
        led.on()

    time.sleep(2)

    for led in objects.values():
        led.off()

    print("LED-Test fertig.")

finally:
    for led in objects.values():
        led.off()
        led.close()
