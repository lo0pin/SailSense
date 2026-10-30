from dataclasses import dataclass
from typing import Callable

from gpiozero import Button


@dataclass
class ButtonPins:
    up: int
    down: int
    ok: int
    back: int


class ButtonController:
    """
    Verwaltet vier Buttons für SailSense.

    Anschlussprinzip:
        GPIO ---- Button ---- GND

    pull_up=True bedeutet:
        nicht gedrückt = HIGH
        gedrückt       = LOW
    """

    def __init__(
        self,
        pins: ButtonPins,
        bounce_time: float = 0.05,
        hold_time: float = 2.0,
    ):
        self.pins = pins
        self.bounce_time = bounce_time
        self.hold_time = hold_time

        self.buttons = {
            "UP": Button(
                pins.up,
                pull_up=True,
                bounce_time=bounce_time,
                hold_time=hold_time,
            ),
            "DOWN": Button(
                pins.down,
                pull_up=True,
                bounce_time=bounce_time,
                hold_time=hold_time,
            ),
            "OK": Button(
                pins.ok,
                pull_up=True,
                bounce_time=bounce_time,
                hold_time=hold_time,
            ),
            "BACK": Button(
                pins.back,
                pull_up=True,
                bounce_time=bounce_time,
                hold_time=hold_time,
            ),
        }

    def bind(
        self,
        on_press: Callable[[str], None] | None = None,
        on_release: Callable[[str], None] | None = None,
        on_hold: Callable[[str], None] | None = None,
    ):
        for name, button in self.buttons.items():
            if on_press is not None:
                button.when_pressed = self._make_callback(on_press, name)

            if on_release is not None:
                button.when_released = self._make_callback(on_release, name)

            if on_hold is not None:
                button.when_held = self._make_callback(on_hold, name)

    @staticmethod
    def _make_callback(callback, name: str):
        def wrapped():
            callback(name)

        return wrapped

    def close(self):
        for button in self.buttons.values():
            button.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
