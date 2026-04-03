import gc
import sys
import time

from machine import ADC, freq

from core.display import BLACK, CYAN, GRAY, GREEN, ORANGE, RED
from core.controls import A_LABEL, B_LABEL
from core.ui import (
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_field,
    draw_window_footer_actions,
    draw_window_shell,
    fit_text,
)


CONVERSION_FACTOR = 3.3 / 65535
TEMP_V27 = 0.706
TEMP_SLOPE = 0.001721
SAMPLE_MS = 1000


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _ticks_diff(newer, older):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(newer, older)
    return newer - older


def _format_uptime(total_seconds):
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)


class DeviceStatusApp:
    app_id = "device-status"
    title = "Status"
    accent = GREEN
    launch_mode = "window"

    def __init__(self):
        self.sensor = None
        self.sensor_checked = False
        self.temp_error = ""
        self.last_sample_ms = -SAMPLE_MS
        self.last_temp_c = None
        self.last_voltage = None
        self.show_fahrenheit = False
        self.boot_ms = _ticks_ms()

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        frame = BLACK if monochrome and selected else GREEN
        detail = BLACK if monochrome and selected else CYAN
        mark = BLACK if monochrome and selected else RED
        lcd.rect(cx - 10, cy - 8, 20, 16, frame)
        lcd.fill_rect(cx - 6, cy - 4, 4, 8, detail)
        lcd.fill_rect(cx, cy - 1, 4, 5, mark)
        lcd.hline(cx - 2, cy + 6, 8, frame)

    def on_open(self, runtime):
        self._sample(force=True)

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

        if last_error:
            self.temp_error = last_error
        else:
            self.temp_error = "sensor unavailable"

    def _sample(self, force=False):
        now = _ticks_ms()
        if not force and _ticks_diff(now, self.last_sample_ms) < SAMPLE_MS:
            return

        self.last_sample_ms = now
        self._init_sensor()
        if self.sensor is None:
            self.last_temp_c = None
            self.last_voltage = None
            return

        total = 0
        for _ in range(8):
            total += self.sensor.read_u16()
        reading = total / 8
        voltage = reading * CONVERSION_FACTOR
        self.last_voltage = voltage
        self.last_temp_c = 27 - (voltage - TEMP_V27) / TEMP_SLOPE

    def _temp_text(self):
        if self.last_temp_c is None:
            return "Unavailable"

        if self.show_fahrenheit:
            value = (self.last_temp_c * 9 / 5) + 32
            return "{:.1f} F".format(value)
        return "{:.1f} C".format(self.last_temp_c)

    def _wifi_text(self, runtime):
        status = runtime.wifi.status()
        if not status.get("supported"):
            return "No module"
        if status.get("connected"):
            return status.get("ssid") or "Connected"
        if status.get("connecting"):
            return status.get("target") or "Joining"
        if status.get("active"):
            return "Ready"
        return "Off"

    def _freq_text(self):
        try:
            return str(freq() // 1000000) + " MHz"
        except Exception:
            return "unknown"

    def _mem_text(self):
        try:
            return str(gc.mem_free() // 1024) + " KB free"
        except Exception:
            return "unknown"

    def _fw_text(self):
        try:
            return sys.implementation.name + " " + sys.version.split()[0]
        except Exception:
            return "unknown"

    def step(self, runtime):
        buttons = runtime.buttons
        if buttons.pressed("A"):
            self.show_fahrenheit = not self.show_fahrenheit
        if buttons.pressed("B"):
            self._sample(force=True)
        else:
            self._sample(force=False)

        lcd = runtime.lcd
        draw_window_shell(lcd, "Device Status", runtime.wifi.status())

        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y, WINDOW_CONTENT_W, 16, "Core temperature", ORANGE)
        temp_color = RED if self.last_temp_c is not None and self.last_temp_c >= 60 else (ORANGE if self.last_temp_c is None else GREEN)
        lcd.text(fit_text(self._temp_text(), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 24, temp_color)

        if self.last_voltage is not None:
            voltage_text = "Sensor {:.3f} V".format(self.last_voltage)
            lcd.text(fit_text(voltage_text, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 40, GRAY)
        else:
            lcd.text(fit_text("Sensor not exposed by firmware", WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 40, GRAY)

        y = WINDOW_CONTENT_Y + 64
        lcd.text(fit_text("CPU   " + self._freq_text(), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, BLACK)
        lcd.text(fit_text("RAM   " + self._mem_text(), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 18, BLACK)
        lcd.text(fit_text("Wi-Fi " + self._wifi_text(runtime), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 36, BLACK)
        uptime_seconds = max(0, _ticks_diff(_ticks_ms(), self.boot_ms) // 1000)
        lcd.text(fit_text("Up    " + _format_uptime(uptime_seconds), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 54, BLACK)
        lcd.text(fit_text("FW    " + self._fw_text(), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 72, CYAN)

        note = "Approx sensor"
        if self.temp_error and self.last_temp_c is None:
            note = fit_text(self.temp_error, WINDOW_TEXT_CHARS)
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_BOTTOM - 18, WINDOW_CONTENT_W, 16, note, ORANGE)
        draw_window_footer_actions(lcd, A_LABEL + " C/F", B_LABEL + " sample", BLACK)
        return None
