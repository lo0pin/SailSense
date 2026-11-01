#!/usr/bin/env python3
import time
from gpiozero import Button

# BCM-Pins eintragen.
# pull_up=True bedeutet: Button zieht beim Drücken nach GND.
BUTTONS = {
    "up": 17,
    "down":27,
    "ok": 22,
    "back": 23,
}

PULL_UP = True
DURATION = 30

print("=== SailSense Button Test ===")
print("BCM-Pins:", BUTTONS)
print(f"Dauer: {DURATION}s")
print("Drücke nacheinander die Tasten. Ausgabe erscheint sofort.")

buttons = {}

try:
    for name, pin in BUTTONS.items():
        btn = Button(pin, pull_up=PULL_UP, bounce_time=0.05)
        buttons[name] = btn

        btn.when_pressed = lambda n=name: print(f"PRESSED : {n}")
        btn.when_released = lambda n=name: print(f"RELEASED: {n}")

    start = time.time()
    while time.time() - start < DURATION:
        states = " | ".join(
            f"{name}={'DOWN' if btn.is_pressed else 'up'}"
            for name, btn in buttons.items()
        )
        print(states)
        time.sleep(1)

    print("Button-Test fertig.")

finally:
    for btn in buttons.values():
        btn.close()
