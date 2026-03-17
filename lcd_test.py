import time

from machine import Pin

from core.display import BLACK, BLUE, CYAN, GRAY, GREEN, LCD, RED, SCREEN_H, SCREEN_W, WHITE, YELLOW


def _center_x(text):
    return max(0, (SCREEN_W - len(text) * 8) // 2)


def _write_centered(lcd, text, y, color):
    lcd.text(text, _center_x(text), y, color)


def _set_led(led, state):
    if led is None:
        return
    led.value(1 if state else 0)


def _draw_solid(lcd, name, fill_color, text_color):
    lcd.fill(fill_color)
    _write_centered(lcd, "LCD TEST", 88, text_color)
    _write_centered(lcd, name, 112, text_color)
    lcd.display()


def _draw_test_card(lcd, frame):
    lcd.fill(BLACK)
    lcd.rect(0, 0, SCREEN_W, SCREEN_H, WHITE)
    lcd.rect(8, 8, SCREEN_W - 16, SCREEN_H - 16, GRAY)
    lcd.hline(0, SCREEN_H // 2, SCREEN_W, GRAY)
    lcd.vline(SCREEN_W // 2, 0, SCREEN_H, GRAY)
    lcd.line(0, 0, SCREEN_W - 1, SCREEN_H - 1, WHITE)
    lcd.line(0, SCREEN_H - 1, SCREEN_W - 1, 0, WHITE)

    _write_centered(lcd, "Pico 2 W", 22, CYAN)
    _write_centered(lcd, "Waveshare LCD 1.3", 38, WHITE)
    _write_centered(lcd, "240x240 ST7789", 54, WHITE)

    bar_y = 150
    bar_h = 18
    colors = (RED, GREEN, BLUE, YELLOW, CYAN, WHITE)
    labels = ("R", "G", "B", "Y", "C", "W")
    bar_w = SCREEN_W // len(colors)
    for index, color in enumerate(colors):
        x = index * bar_w
        lcd.fill_rect(x, bar_y, bar_w, bar_h, color)
        label_color = BLACK if color in (GREEN, YELLOW, CYAN, WHITE) else WHITE
        lcd.text(labels[index], x + (bar_w // 2) - 4, bar_y + 5, label_color)

    _write_centered(lcd, "If you see colors, lines,", 184, WHITE)
    _write_centered(lcd, "and the moving square,", 198, WHITE)
    _write_centered(lcd, "the LCD path is working.", 212, WHITE)

    sweep_w = 18
    sweep_span = SCREEN_W - 40 - sweep_w
    sweep_x = 20 + ((frame * 9) % sweep_span)
    lcd.fill_rect(sweep_x, 96, sweep_w, sweep_w, YELLOW)
    lcd.rect(sweep_x, 96, sweep_w, sweep_w, WHITE)
    lcd.display()


def run():
    led = None
    try:
        led = Pin("LED", Pin.OUT)
    except Exception:
        led = None

    lcd = LCD()

    for level in (200, 500, 1000):
        lcd.backlight(level)
        lcd.fill(BLACK)
        _write_centered(lcd, "LCD TEST", 92, WHITE)
        _write_centered(lcd, "Backlight %d%%" % (level // 10), 116, CYAN)
        lcd.display()
        _set_led(led, level >= 500)
        time.sleep(0.35)

    solid_screens = (
        ("RED", RED, WHITE),
        ("GREEN", GREEN, BLACK),
        ("BLUE", BLUE, WHITE),
        ("WHITE", WHITE, BLACK),
        ("BLACK", BLACK, WHITE),
    )
    for name, fill_color, text_color in solid_screens:
        _draw_solid(lcd, name, fill_color, text_color)
        _set_led(led, fill_color != BLACK)
        time.sleep(0.45)

    for frame in range(28):
        _draw_test_card(lcd, frame)
        _set_led(led, frame % 2 == 0)
        time.sleep(0.08)

    _draw_test_card(lcd, 0)
    _set_led(led, True)


if __name__ == "__main__":
    run()
