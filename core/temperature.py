import time

from machine import ADC


CONVERSION_FACTOR = 3.3 / 65535
TEMP_V27 = 0.706
TEMP_SLOPE = 0.001721
DEFAULT_SAMPLE_MS = 1000


def ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def ticks_diff(newer, older):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(newer, older)
    return newer - older


class CoreTemperatureSensor:
    def __init__(self, sample_ms=DEFAULT_SAMPLE_MS):
        self.sample_ms = sample_ms
        self.sensor = None
        self.sensor_checked = False
        self.temp_error = ""
        self.last_sample_ms = -sample_ms
        self.last_temp_c = None
        self.last_voltage = None

    def reset(self):
        self.last_sample_ms = -self.sample_ms
        self.last_temp_c = None
        self.last_voltage = None

    def _init_sensor(self):
        if self.sensor_checked:
            return

        self.sensor_checked = True
        candidates = []
        core_temp = getattr(ADC, "CORE_TEMP", None)
        if core_temp is not None:
            candidates.append(core_temp)
        candidates.append(4)

        last_error = ""
        for channel in candidates:
            try:
                sensor = ADC(channel)
                sensor.read_u16()
                self.sensor = sensor
                self.temp_error = ""
                return
            except Exception as exc:
                last_error = str(exc)

        self.temp_error = last_error or "sensor unavailable"

    def sample(self, force=False):
        now = ticks_ms()
        if not force and ticks_diff(now, self.last_sample_ms) < self.sample_ms:
            return self.last_temp_c

        self.last_sample_ms = now
        self._init_sensor()
        if self.sensor is None:
            self.last_temp_c = None
            self.last_voltage = None
            return None

        total = 0
        for _ in range(8):
            total += self.sensor.read_u16()
        reading = total / 8
        voltage = reading * CONVERSION_FACTOR
        self.last_voltage = voltage
        self.last_temp_c = 27 - (voltage - TEMP_V27) / TEMP_SLOPE
        return self.last_temp_c
