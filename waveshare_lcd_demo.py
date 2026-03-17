import time

try:
    from machine import Pin
except ImportError:
    Pin = None

import lcd as lcd_driver


SCREEN_W = 240
SCREEN_H = 240

# Common RGB565 values used by Waveshare-style examples.
BLACK = 0x0000
BLUE = 0x001F
RED = 0xF800
GREEN = 0x07E0
CYAN = 0x07FF
MAGENTA = 0xF81F
YELLOW = 0xFFE0
WHITE = 0xFFFF


def _center_x(text):
    return max(0, (SCREEN_W - len(text) * 8) // 2)


def _refresh(display):
    if hasattr(display, "show"):
        display.show()
    elif hasattr(display, "display"):
        display.display()


def _set_backlight(display, value):
    value = max(0, min(1000, value))
    scaled = int(value * 65535 / 1000)

    if hasattr(display, "backlight"):
        display.backlight(value)
        return

    if hasattr(display, "set_bl_pwm"):
        try:
            display.set_bl_pwm(scaled)
        except TypeError:
            display.set_bl_pwm(value)
        return

    for attr_name in ("backlight_pwm", "bl"):
        pwm = getattr(display, attr_name, None)
        if pwm is not None and hasattr(pwm, "duty_u16"):
            pwm.duty_u16(scaled)
            return


def _resolve_display():
    for name in ("LCD_1inch3", "LCD", "PicoLCD13", "LCD_0inch96"):
        display_cls = getattr(lcd_driver, name, None)
        if display_cls is not None:
            return display_cls()
    raise ImportError("lcd.py does not expose LCD_1inch3, LCD, PicoLCD13, or LCD_0inch96")


def _draw_solid(display, color, label, label_color):
    display.fill(color)
    display.text("Waveshare Demo", _center_x("Waveshare Demo"), 92, label_color)
    display.text(label, _center_x(label), 116, label_color)
    _refresh(display)


def _draw_test_pattern(display, frame):
    display.fill(BLACK)
    display.rect(0, 0, SCREEN_W, SCREEN_H, WHITE)
    display.rect(10, 10, SCREEN_W - 20, SCREEN_H - 20, CYAN)
    display.line(0, 0, SCREEN_W - 1, SCREEN_H - 1, RED)
    display.line(0, SCREEN_H - 1, SCREEN_W - 1, 0, GREEN)
    display.hline(0, SCREEN_H // 2, SCREEN_W, BLUE)
    display.vline(SCREEN_W // 2, 0, SCREEN_H, BLUE)

    display.text("Pico 2 W", _center_x("Pico 2 W"), 22, YELLOW)
    display.text("LCD 1.3 direct test", _center_x("LCD 1.3 direct test"), 38, WHITE)

    colors = (RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, WHITE)
    bar_w = SCREEN_W // len(colors)
    for index, color in enumerate(colors):
        display.fill_rect(index * bar_w, 148, bar_w, 16, color)

    box_size = 24
    box_left = 16 + ((frame * 7) % (SCREEN_W - 32 - box_size))
    display.fill_rect(box_left, 96, box_size, box_size, YELLOW)
    display.rect(box_left, 96, box_size, box_size, WHITE)

    display.text("If this renders,", _center_x("If this renders,"), 188, WHITE)
    display.text("the raw lcd driver works.", _center_x("the raw lcd driver works."), 204, WHITE)
    _refresh(display)


def demo_cycle():
    led = None
    if Pin is not None:
        try:
            led = Pin("LED", Pin.OUT)
        except Exception:
            led = None

    display = _resolve_display()
    _set_backlight(display, 1000)

    solid_screens = (
        ("RED", RED, WHITE),
        ("GREEN", GREEN, BLACK),
        ("BLUE", BLUE, WHITE),
        ("WHITE", WHITE, BLACK),
        ("BLACK", BLACK, WHITE),
    )
    for label, color, label_color in solid_screens:
        _draw_solid(display, color, label, label_color)
        if led is not None:
            led.value(0 if color == BLACK else 1)
        time.sleep(0.4)

    for frame in range(40):
        _draw_test_pattern(display, frame)
        if led is not None:
            led.value(frame % 2)
        time.sleep(0.08)

    _draw_test_pattern(display, 0)
    if led is not None:
        led.value(1)


def run():
    display = _resolve_display()
    _set_backlight(display, 1000)
    _draw_test_pattern(display, 0)


if __name__ == "__main__":
    run()
