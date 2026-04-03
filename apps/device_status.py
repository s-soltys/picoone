import gc
import sys

from machine import freq

from core.display import BLACK, GRAY, GREEN, ORANGE, RED, BLUE, CYAN
from core.controls import A_LABEL, B_LABEL, HOME_HINT, X_LABEL
from core.temperature import CoreTemperatureSensor, ticks_diff, ticks_ms
from core.ui import (
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_field,
    draw_window_shell,
    fit_text,
)

SAMPLE_MS = 1000


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
        self.sensor = CoreTemperatureSensor(SAMPLE_MS)
        self.show_fahrenheit = False
        self.show_extra = False
        self.last_mem_text = "unknown"
        self.last_mem_sample_ms = -SAMPLE_MS
        self.boot_ms = ticks_ms()

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        frame = BLACK if monochrome and selected else GREEN
        detail = BLACK if monochrome and selected else CYAN
        mark = BLACK if monochrome and selected else RED
        lcd.rect(cx - 10, cy - 8, 20, 16, frame)
        lcd.fill_rect(cx - 6, cy - 4, 4, 8, detail)
        lcd.fill_rect(cx, cy - 1, 4, 5, mark)
        lcd.hline(cx - 2, cy + 6, 8, frame)

    def on_open(self, runtime):
        self.show_extra = False
        self._sample(force=True)
        self._sample_mem(force=True)

    def help_lines(self, runtime):
        return [
            "Status controls",
            B_LABEL + " sample now",
            A_LABEL + " toggle C/F",
            X_LABEL + " switch detail page",
            HOME_HINT,
        ]

    def _sample(self, force=False):
        self.sensor.sample(force)

    def _temp_text(self):
        if self.sensor.last_temp_c is None:
            return "Unavailable"

        if self.show_fahrenheit:
            value = (self.sensor.last_temp_c * 9 / 5) + 32
            return "{:.1f} F".format(value)
        return "{:.1f} C".format(self.sensor.last_temp_c)

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
        return self.last_mem_text

    def _sample_mem(self, force=False):
        now = ticks_ms()
        if not force and ticks_diff(now, self.last_mem_sample_ms) < SAMPLE_MS:
            return
        self.last_mem_sample_ms = now
        try:
            gc.collect()
            self.last_mem_text = str(gc.mem_free() // 1024) + " KB free"
        except Exception:
            self.last_mem_text = "unknown"

    def _fw_text(self):
        try:
            return sys.implementation.name + " " + sys.version.split()[0]
        except Exception:
            return "unknown"

    def step(self, runtime):
        buttons = runtime.buttons
        if buttons.pressed("A"):
            self.show_fahrenheit = not self.show_fahrenheit
        if buttons.pressed("X"):
            self.show_extra = not self.show_extra
        if buttons.pressed("B"):
            self._sample(force=True)
            self._sample_mem(force=True)
        else:
            self._sample(force=False)
            self._sample_mem(force=False)

        lcd = runtime.lcd
        draw_window_shell(lcd, "Device Status", runtime.wifi.status())

        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y, WINDOW_CONTENT_W, 16, "Core temperature", ORANGE)
        temp_color = RED if self.sensor.last_temp_c is not None and self.sensor.last_temp_c >= 60 else (ORANGE if self.sensor.last_temp_c is None else GREEN)
        lcd.text(fit_text(self._temp_text(), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 24, temp_color)

        if self.show_extra:
            if self.sensor.last_voltage is not None:
                voltage_text = "Sensor {:.3f} V".format(self.sensor.last_voltage)
                lcd.text(fit_text(voltage_text, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 40, GRAY)
            else:
                lcd.text(fit_text("Sensor not exposed by firmware", WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 40, GRAY)

            y = WINDOW_CONTENT_Y + 64
            lcd.text(fit_text("Wi-Fi " + self._wifi_text(runtime), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, BLACK)
            uptime_seconds = max(0, ticks_diff(ticks_ms(), self.boot_ms) // 1000)
            lcd.text(fit_text("Up    " + _format_uptime(uptime_seconds), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 18, BLACK)
            lcd.text(fit_text("FW    " + self._fw_text(), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 36, BLUE)
            lcd.text(fit_text("Page  extended", WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 54, GRAY)
        else:
            if self.sensor.last_voltage is not None:
                voltage_text = "Sensor {:.3f} V".format(self.sensor.last_voltage)
                lcd.text(fit_text(voltage_text, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 40, GRAY)
            else:
                lcd.text(fit_text("Sensor not exposed by firmware", WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 40, GRAY)

            y = WINDOW_CONTENT_Y + 64
            lcd.text(fit_text("CPU   " + self._freq_text(), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, BLACK)
            lcd.text(fit_text("RAM   " + self._mem_text(), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 18, BLACK)
            lcd.text(fit_text("Wi-Fi " + self._wifi_text(runtime), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 36, BLACK)
            lcd.text("Page  overview", WINDOW_CONTENT_X, y + 54, GRAY)

        note = "Approx sensor"
        if self.sensor.temp_error and self.sensor.last_temp_c is None:
            note = fit_text(self.sensor.temp_error, WINDOW_TEXT_CHARS)
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_BOTTOM - 18, WINDOW_CONTENT_W, 16, note, ORANGE)
        return None
