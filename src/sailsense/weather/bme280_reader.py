from datetime import datetime, timezone
from typing import Optional

import board
import busio
import adafruit_bme280.advanced as adafruit_bme280


class BME280Reader:
    """
    Liest Temperatur, Luftfeuchtigkeit und Luftdruck vom BME280 über I²C.
    """

    def __init__(self, i2c_address: int = 0x76):
        self.i2c_address = i2c_address
        self.i2c = None
        self.sensor = None

    def __enter__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.sensor = adafruit_bme280.Adafruit_BME280_I2C(
            self.i2c,
            address=self.i2c_address,
        )

        # Sinnvolle Grundeinstellungen für ruhiges Logging
        self.sensor.sea_level_pressure = 1013.25
        self.sensor.mode = adafruit_bme280.MODE_NORMAL
        self.sensor.standby_period = adafruit_bme280.STANDBY_TC_1000
        self.sensor.iir_filter = adafruit_bme280.IIR_FILTER_X16
        self.sensor.overscan_pressure = adafruit_bme280.OVERSCAN_X16
        self.sensor.overscan_humidity = adafruit_bme280.OVERSCAN_X1
        self.sensor.overscan_temperature = adafruit_bme280.OVERSCAN_X2

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # busio.I2C hat auf Blinka nicht überall ein explizites close.
        # Daher hier bewusst nichts Dramatisches.
        pass

    @staticmethod
    def _round_or_none(value: Optional[float], digits: int = 2):
        if value is None:
            return None
        return round(float(value), digits)

    def read(self) -> dict:
        if self.sensor is None:
            raise RuntimeError("BME280Reader muss mit 'with BME280Reader(...) as bme:' verwendet werden.")

        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "temp_c": self._round_or_none(self.sensor.temperature, 2),
            "humidity_pct": self._round_or_none(self.sensor.relative_humidity, 2),
            "pressure_hpa": self._round_or_none(self.sensor.pressure, 2),
        }
