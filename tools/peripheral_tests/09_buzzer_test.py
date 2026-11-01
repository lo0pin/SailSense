#!/usr/bin/env python3
import time
from gpiozero import PWMOutputDevice

# BCM-Pin eintragen.
BUZZER_PIN = 12

VOLUME = 0.15
TONES = [
    (880, 0.08),
    (0,   0.08),
    (1175, 0.08),
    (0,   0.15),
    (988, 0.12),
]

print("=== SailSense passiver Buzzer Test ===")
print(f"BCM-Pin: {BUZZER_PIN}")

buzzer = None

try:
    buzzer = PWMOutputDevice(BUZZER_PIN, frequency=1000, initial_value=0)

    for freq, duration in TONES:
        if freq <= 0:
            buzzer.value = 0
        else:
            buzzer.frequency = freq
            buzzer.value = VOLUME

        print(f"freq={freq}Hz dauer={duration}s")
        time.sleep(duration)

    buzzer.value = 0
    print("Buzzer-Test fertig.")

finally:
    if buzzer:
        buzzer.value = 0
        buzzer.close()
