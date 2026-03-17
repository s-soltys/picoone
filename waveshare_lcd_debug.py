import time

try:
    from machine import Pin
except ImportError:
    Pin = None

import lcd as lcd_driver


SCREEN_W = 240
SCREEN_H = 240

BLACK = 0x0000
WHITE = 0xFFFF
STD_RED = 0xF800
STD_GREEN = 0x07E0
STD_BLUE = 0x001F
SWAP_RED = 0x00F8
SWAP_GREEN = 0xE007
SWAP_BLUE = 0x1F00
YELLOW = 0xFFE0
CYAN = 0x07FF


def _log(message):
    print("[lcd-debug]", message)


def _center_x(text):
    return max(0, (SCREEN_W - len(text) * 8) // 2)


def _make_led():
    if Pin is None:
        _log("machine.Pin unavailable")
        return None
    try:
        led = Pin("LED", Pin.OUT)
        _log("onboard LED ready")
        return led
    except Exception as exc:
        _log("onboard LED unavailable: %r" % (exc,))
        return None


def _blink(led, count):
    if led is None:
        return
    for _ in range(count):
        led.value(1)
        time.sleep(0.08)
        led.value(0)
        time.sleep(0.08)


def _resolve_display():
    _log("probing lcd.py exports")
    for name in ("LCD_1inch3", "LCD", "PicoLCD13", "LCD_0inch96"):
        display_cls = getattr(lcd_driver, name, None)
        if display_cls is not None:
            _log("using display class %s" % name)
            return display_cls(), name
    raise ImportError("lcd.py does not expose LCD_1inch3, LCD, PicoLCD13, or LCD_0inch96")


def _print_display_info(display, class_name):
    _log("class name: %s" % class_name)
    _log("type: %r" % (type(display),))
    _log("width: %r" % (getattr(display, "width", None),))
    _log("height: %r" % (getattr(display, "height", None),))
    methods = []
    for name in ("show", "display", "fill", "fill_rect", "rect", "line", "text", "backlight", "set_bl_pwm"):
        if hasattr(display, name):
            methods.append(name)
    _log("methods: %s" % (", ".join(methods) if methods else "none"))
    buffer_obj = getattr(display, "buffer", None)
    if buffer_obj is None:
        _log("buffer: none")
    else:
        try:
            size = len(buffer_obj)
        except TypeError:
            size = "unknown"
        _log("buffer bytes: %s" % size)


def _refresh(display, stage_name):
    called = []
    for method_name in ("show", "display"):
        method = getattr(display, method_name, None)
        if method is not None:
            _log("refreshing via %s for %s" % (method_name, stage_name))
            method()
            called.append(method_name)
    if not called:
        _log("no refresh method found for %s" % stage_name)


def _set_backlight(display, value):
    value = max(0, min(1000, value))
    scaled = int(value * 65535 / 1000)

    method = getattr(display, "backlight", None)
    if method is not None:
        _log("setting backlight via backlight(%d)" % value)
        method(value)
        return

    method = getattr(display, "set_bl_pwm", None)
    if method is not None:
        try:
            _log("setting backlight via set_bl_pwm(%d)" % scaled)
            method(scaled)
        except TypeError:
            _log("set_bl_pwm rejected 16-bit value, retrying with %d" % value)
            method(value)
        return

    for attr_name in ("backlight_pwm", "bl"):
        pwm = getattr(display, attr_name, None)
        if pwm is not None and hasattr(pwm, "duty_u16"):
            _log("setting backlight via %s.duty_u16(%d)" % (attr_name, scaled))
            pwm.duty_u16(scaled)
            return

    _log("no backlight control found")


def _draw_center_text(display, text, y, color):
    if hasattr(display, "text"):
        display.text(text, _center_x(text), y, color)


def _stage_fill(display, led, label, color, text_color, pause_s):
    _log("stage %s fill color 0x%04X" % (label, color))
    if hasattr(display, "fill"):
        display.fill(color)
    _draw_center_text(display, label, 108, text_color)
    _refresh(display, label)
    _blink(led, 1)
    time.sleep(pause_s)


def _stage_geometry(display, led, pause_s):
    _log("stage geometry")
    if hasattr(display, "fill"):
        display.fill(BLACK)
    if hasattr(display, "rect"):
        display.rect(0, 0, SCREEN_W, SCREEN_H, WHITE)
        display.rect(10, 10, SCREEN_W - 20, SCREEN_H - 20, CYAN)
    if hasattr(display, "line"):
        display.line(0, 0, SCREEN_W - 1, SCREEN_H - 1, STD_RED)
        display.line(0, SCREEN_H - 1, SCREEN_W - 1, 0, STD_GREEN)
    if hasattr(display, "hline"):
        display.hline(0, SCREEN_H // 2, SCREEN_W, STD_BLUE)
    if hasattr(display, "vline"):
        display.vline(SCREEN_W // 2, 0, SCREEN_H, STD_BLUE)
    _draw_center_text(display, "GEOMETRY", 22, YELLOW)
    _draw_center_text(display, "If visible, SPI flush works.", 200, WHITE)
    _refresh(display, "geometry")
    _blink(led, 2)
    time.sleep(pause_s)


def run(pause_s=0.9):
    _log("starting")
    led = _make_led()
    display, class_name = _resolve_display()
    _print_display_info(display, class_name)

    _set_backlight(display, 150)
    time.sleep(0.2)
    _set_backlight(display, 1000)

    stages = (
        ("BLACK", BLACK, WHITE),
        ("WHITE", WHITE, BLACK),
        ("STD RED", STD_RED, WHITE),
        ("STD GREEN", STD_GREEN, BLACK),
        ("STD BLUE", STD_BLUE, WHITE),
        ("SWAP RED", SWAP_RED, WHITE),
        ("SWAP GREEN", SWAP_GREEN, BLACK),
        ("SWAP BLUE", SWAP_BLUE, WHITE),
    )
    for label, color, text_color in stages:
        _stage_fill(display, led, label, color, text_color, pause_s)

    _stage_geometry(display, led, pause_s)
    _log("finished")


if __name__ == "__main__":
    run()
