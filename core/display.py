try:
    import lcd as _driver_module
except ImportError:
    _driver_module = None


SCREEN_W = 240
SCREEN_H = 240

# colors are BGR565 byte-swapped so raw framebuf bytes display correctly
RED = 0x00F8
GREEN = 0xE007
BLUE = 0x1F00
WHITE = 0xFFFF
BLACK = 0x0000
DKRED = 0x0090
PINK = 0x1FFC
DKGRN = 0x4004
YELLOW = 0xE0FF
CYAN = 0xFF07
GRAY = 0x1084
ORANGE = 0x20FD
PURPLE = 0x1660
TEAL = 0x6F04
RUST = 0x80C2
CRIMSON = 0x05B0
BROWN = 0x228A
GOLD = 0x40DD
SLATE = 0x8F52
INDIGO = 0x1E30
MARINE = 0xB903
AMBER = 0x00FE
OLIVE = 0xE063
MAROON = 0x0060
COPPER = 0xA0CA
SAND = 0x4BCD


def _resolve_driver_class():
    if _driver_module is None:
        raise ImportError("lcd module not found on device")

    for name in ("LCD", "PicoLCD13", "LCD_1inch3", "LCD_0inch96"):
        driver_cls = getattr(_driver_module, name, None)
        if driver_cls is not None:
            return driver_cls

    raise ImportError("lcd module does not export a supported display class")


class LCD:
    def __init__(self):
        driver_cls = _resolve_driver_class()
        self._lcd = driver_cls()
        self.width = getattr(self._lcd, "width", SCREEN_W)
        self.height = getattr(self._lcd, "height", SCREEN_H)
        if hasattr(self._lcd, "buffer"):
            self.buffer = self._lcd.buffer

    def __getattr__(self, name):
        return getattr(self._lcd, name)

    def display(self):
        if hasattr(self._lcd, "display"):
            return self._lcd.display()
        if hasattr(self._lcd, "show"):
            return self._lcd.show()
        return None

    def backlight(self, value):
        value = max(0, min(1000, value))

        if hasattr(self._lcd, "backlight"):
            return self._lcd.backlight(value)

        scaled = int(value * 65535 / 1000)
        if hasattr(self._lcd, "set_bl_pwm"):
            try:
                return self._lcd.set_bl_pwm(scaled)
            except TypeError:
                return self._lcd.set_bl_pwm(value)

        for attr_name in ("backlight_pwm", "bl"):
            pwm = getattr(self._lcd, attr_name, None)
            if pwm is not None and hasattr(pwm, "duty_u16"):
                return pwm.duty_u16(scaled)

        return None
