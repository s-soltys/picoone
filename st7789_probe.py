import time

from machine import Pin, PWM, SPI


SCREEN_W = 240
SCREEN_H = 240

PIN_CS = 9
PIN_DC = 8
PIN_RST = 12
PIN_BL = 13
PIN_SCK = 10
PIN_MOSI = 11


def _log(message):
    print("[st7789-probe]", message)


class ST7789Probe:
    def __init__(self, baudrate=10_000_000):
        self.cs = Pin(PIN_CS, Pin.OUT)
        self.dc = Pin(PIN_DC, Pin.OUT)
        self.rst = Pin(PIN_RST, Pin.OUT)
        self.cs(1)
        self.dc(1)

        self.spi = SPI(
            1,
            baudrate=baudrate,
            polarity=0,
            phase=0,
            sck=Pin(PIN_SCK),
            mosi=Pin(PIN_MOSI),
            miso=None,
        )

        self.bl = PWM(Pin(PIN_BL))
        self.bl.freq(1000)

        self.led = None
        try:
            self.led = Pin("LED", Pin.OUT)
        except Exception:
            self.led = None

    def _blink(self, count):
        if self.led is None:
            return
        for _ in range(count):
            self.led.value(1)
            time.sleep(0.08)
            self.led.value(0)
            time.sleep(0.08)

    def backlight(self, value):
        value = max(0, min(1000, value))
        duty = int(value * 65535 / 1000)
        self.bl.duty_u16(duty)
        _log("backlight %d/1000" % value)

    def backlight_sweep(self, pause_s=2.0):
        _log("starting backlight sweep: watch the panel brightness")
        stages = (
            ("BL MIN", 0),
            ("BL LOW", 120),
            ("BL MID", 500),
            ("BL MAX", 1000),
        )
        for index, stage in enumerate(stages, 1):
            label, value = stage
            _log("%s for %.1fs" % (label, pause_s))
            self.backlight(value)
            self._blink(index)
            time.sleep(pause_s)
        _log("backlight sweep finished")

    def cmd(self, value):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([value]))
        self.cs(1)

    def data(self, payload):
        self.dc(1)
        self.cs(0)
        if isinstance(payload, int):
            self.spi.write(bytearray([payload]))
        else:
            self.spi.write(payload)
        self.cs(1)

    def reset(self):
        _log("hardware reset")
        self.rst(1)
        time.sleep(0.12)
        self.rst(0)
        time.sleep(0.12)
        self.rst(1)
        time.sleep(0.12)

    def init_panel(self, madctl):
        self.reset()

        init_steps = (
            (0x36, bytes([madctl])),
            (0x3A, b"\x05"),
            (0xB2, b"\x0C\x0C\x00\x33\x33"),
            (0xB7, b"\x35"),
            (0xBB, b"\x19"),
            (0xC0, b"\x2C"),
            (0xC2, b"\x01"),
            (0xC3, b"\x12"),
            (0xC4, b"\x20"),
            (0xC6, b"\x0F"),
            (0xD0, b"\xA4\xA1"),
            (0xE0, b"\xD0\x04\x0D\x11\x13\x2B\x3F\x54\x4C\x18\x0D\x0B\x1F\x23"),
            (0xE1, b"\xD0\x04\x0C\x11\x13\x2C\x3F\x44\x51\x2F\x1F\x1F\x20\x23"),
        )

        _log("init panel madctl=0x%02X" % madctl)
        for command, payload in init_steps:
            self.cmd(command)
            self.data(payload)

        self.cmd(0x21)
        self.cmd(0x11)
        time.sleep(0.12)
        self.cmd(0x29)
        time.sleep(0.02)

    def set_window(self, x0, y0, x1, y1):
        self.cmd(0x2A)
        self.data(bytearray([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self.cmd(0x2B)
        self.data(bytearray([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        self.cmd(0x2C)

    def fill_raw(self, color_hi, color_lo, x_offset=0, y_offset=0):
        self.set_window(x_offset, y_offset, x_offset + SCREEN_W - 1, y_offset + SCREEN_H - 1)
        chunk = bytearray(4096)
        for index in range(0, len(chunk), 2):
            chunk[index] = color_hi
            chunk[index + 1] = color_lo

        total_bytes = SCREEN_W * SCREEN_H * 2
        remaining = total_bytes
        self.dc(1)
        self.cs(0)
        while remaining > 0:
            write_len = len(chunk) if remaining >= len(chunk) else remaining
            self.spi.write(memoryview(chunk)[:write_len])
            remaining -= write_len
        self.cs(1)

    def sleep_cycle(self):
        self.cmd(0x10)
        time.sleep(0.12)
        self.cmd(0x11)
        time.sleep(0.12)


def run(pause_s=1.0):
    probe = ST7789Probe()
    _log("created probe on SPI1 pins cs=%d dc=%d rst=%d bl=%d sck=%d mosi=%d" % (PIN_CS, PIN_DC, PIN_RST, PIN_BL, PIN_SCK, PIN_MOSI))
    probe.backlight_sweep()
    probe.backlight(1000)

    attempts = (
        ("A swap @ y0 madctl 0x70", 0x70, 0, 0, ((0x00, 0x00, "black"), (0xFF, 0xFF, "white"), (0x00, 0xF8, "red"), (0xE0, 0x07, "green"), (0x1F, 0x00, "blue"))),
        ("B std  @ y0 madctl 0x70", 0x70, 0, 0, ((0x00, 0x00, "black"), (0xFF, 0xFF, "white"), (0xF8, 0x00, "red"), (0x07, 0xE0, "green"), (0x00, 0x1F, "blue"))),
        ("C swap @ y80 madctl 0x70", 0x70, 0, 80, ((0x00, 0x00, "black"), (0xFF, 0xFF, "white"), (0x00, 0xF8, "red"), (0xE0, 0x07, "green"), (0x1F, 0x00, "blue"))),
        ("D std  @ y80 madctl 0x70", 0x70, 0, 80, ((0x00, 0x00, "black"), (0xFF, 0xFF, "white"), (0xF8, 0x00, "red"), (0x07, 0xE0, "green"), (0x00, 0x1F, "blue"))),
        ("E swap @ y0 madctl 0x00", 0x00, 0, 0, ((0x00, 0x00, "black"), (0xFF, 0xFF, "white"), (0x00, 0xF8, "red"), (0xE0, 0x07, "green"), (0x1F, 0x00, "blue"))),
        ("F std  @ y0 madctl 0x00", 0x00, 0, 0, ((0x00, 0x00, "black"), (0xFF, 0xFF, "white"), (0xF8, 0x00, "red"), (0x07, 0xE0, "green"), (0x00, 0x1F, "blue"))),
    )

    for index, attempt in enumerate(attempts, 1):
        label, madctl, x_offset, y_offset, colors = attempt
        _log("attempt %d: %s" % (index, label))
        probe.init_panel(madctl)
        for color_hi, color_lo, name in colors:
            _log("fill %s with bytes 0x%02X 0x%02X offset=(%d,%d)" % (name, color_hi, color_lo, x_offset, y_offset))
            probe.fill_raw(color_hi, color_lo, x_offset, y_offset)
            probe._blink(index)
            time.sleep(pause_s)
        probe.sleep_cycle()

    _log("probe finished")


if __name__ == "__main__":
    run()
