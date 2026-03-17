import time

from core.display import SCREEN_W, SCREEN_H, BLACK, WHITE, GRAY, CYAN, YELLOW, DKGRN, TEAL, SLATE
from core.controls import HOME_HINT


HEADER_H = 18
FOOTER_H = 18
CONTENT_TOP = HEADER_H + 6
CONTENT_BOTTOM = SCREEN_H - FOOTER_H - 4
CONTENT_H = CONTENT_BOTTOM - CONTENT_TOP
CONTENT_LEFT = 4
CONTENT_RIGHT = SCREEN_W - 4
TEXT_Y_HEADER = 5
TEXT_Y_FOOTER = SCREEN_H - FOOTER_H + 5

MENU_TITLE = "PicoOS"
MENU_WIFI_LABEL = "Wi-Fi"
MENU_BAR_H = 14
DESKTOP_TOP = MENU_BAR_H + 1
MENU_DROPDOWN_ROW_H = 14

WINDOW_X = 2
WINDOW_Y = MENU_BAR_H + 3
WINDOW_W = SCREEN_W - (WINDOW_X * 2)
WINDOW_H = SCREEN_H - WINDOW_Y - 2
WINDOW_TITLE_H = 12
WINDOW_FOOTER_H = 14
WINDOW_CONTENT_X = WINDOW_X + 6
WINDOW_CONTENT_Y = WINDOW_Y + WINDOW_TITLE_H + 6
WINDOW_CONTENT_W = WINDOW_W - 12
WINDOW_CONTENT_BOTTOM = WINDOW_Y + WINDOW_H - WINDOW_FOOTER_H - 4
WINDOW_CONTENT_H = WINDOW_CONTENT_BOTTOM - WINDOW_CONTENT_Y
WINDOW_FOOTER_Y = WINDOW_Y + WINDOW_H - WINDOW_FOOTER_H
WINDOW_TEXT_CHARS = max(1, WINDOW_CONTENT_W // 8)


def fit_text(text, max_chars):
    if text is None:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[: max_chars - 1] + "."


def center_x(text, width=SCREEN_W, left=0):
    return max(left, left + ((width - len(text) * 8) // 2))


def right_x(text, margin=4, width=SCREEN_W, left=0):
    return max(left + margin, left + width - (len(text) * 8) - margin)


def menu_clock_text():
    try:
        now = time.localtime()
    except Exception:
        return MENU_TITLE

    if not now or len(now) < 5:
        return MENU_TITLE

    year = now[0]
    if year < 2024:
        return MENU_TITLE
    return "{:02d}:{:02d}".format(now[3], now[4])


def menu_bar_regions(title=MENU_TITLE, clock_text=None):
    title = fit_text(title, 8)
    title_x = 16
    title_w = len(title) * 8
    wifi_w = (len(MENU_WIFI_LABEL) * 8) + 8
    wifi_x = title_x + title_w + 10

    if clock_text is None:
        clock_text = menu_clock_text()
    clock_text = fit_text(clock_text, 6)
    clock_w = len(clock_text) * 8
    glyph_x = SCREEN_W - 12
    clock_x = max(wifi_x + wifi_w + 8, glyph_x - 4 - clock_w)

    return {
        "title": title,
        "title_x": title_x,
        "wifi_x": wifi_x,
        "wifi_w": wifi_w,
        "wifi_rect": (wifi_x - 2, 1, wifi_w, MENU_BAR_H - 2),
        "clock_text": clock_text,
        "clock_x": clock_x,
        "glyph_x": glyph_x,
    }


def draw_header(lcd, title, detail="", color=CYAN):
    max_title = max(1, (SCREEN_W // 8) - 8)
    title = fit_text(title, max_title)
    lcd.fill_rect(0, 0, SCREEN_W, HEADER_H, BLACK)
    lcd.hline(0, HEADER_H - 1, SCREEN_W, color)
    lcd.text(title, 4, TEXT_Y_HEADER, color)
    if detail:
        max_detail = max(1, min(10, (SCREEN_W // 8) - len(title) - 3))
        detail = fit_text(detail, max_detail)
        lcd.text(detail, right_x(detail), TEXT_Y_HEADER, WHITE)


def draw_footer(lcd, text, color=GRAY):
    max_chars = max(1, (SCREEN_W // 8) - 2)
    text = fit_text(text, max_chars)
    lcd.fill_rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H, BLACK)
    lcd.hline(0, SCREEN_H - FOOTER_H, SCREEN_W, color)
    lcd.text(text, 4, TEXT_Y_FOOTER, color)


def draw_footer_actions(lcd, left_text, right_text="", color=GRAY):
    lcd.fill_rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H, BLACK)
    lcd.hline(0, SCREEN_H - FOOTER_H, SCREEN_W, color)
    if not right_text:
        lcd.text(fit_text(left_text, max(1, (SCREEN_W // 8) - 2)), 4, TEXT_Y_FOOTER, color)
        return

    half_chars = max(1, ((SCREEN_W // 2) - 8) // 8)
    left_text = fit_text(left_text, half_chars)
    right_text = fit_text(right_text, half_chars)
    lcd.text(left_text, 4, TEXT_Y_FOOTER, color)
    lcd.text(right_text, right_x(right_text), TEXT_Y_FOOTER, color)


def draw_tile(lcd, x, y, w, h, title, selected, accent, icon_fn, monochrome=False):
    if monochrome:
        border = WHITE
        fill = WHITE if selected else BLACK
        text_color = BLACK if selected else WHITE
    else:
        border = YELLOW if selected else GRAY
        fill = SLATE if selected else DKGRN
        text_color = accent if selected else WHITE

    lcd.fill_rect(x, y, w, h, fill)
    lcd.rect(x, y, w, h, border)
    icon_fn(lcd, x + (w // 2), y + max(20, h // 3), selected, monochrome)

    max_chars = max(4, (w // 8) - 2)
    label = fit_text(title, max_chars)
    lcd.text(label, x + max(3, (w - (len(label) * 8)) // 2), y + h - 16, text_color)


def draw_empty_state(lcd, title, lines, accent=TEAL, footer=HOME_HINT):
    lcd.fill(BLACK)
    draw_header(lcd, title, color=accent)
    y = CONTENT_TOP + 12
    for line in lines:
        lcd.text(fit_text(line, 28), CONTENT_LEFT, y, WHITE)
        y += 18
    draw_footer(lcd, footer)


def _wifi_status_text(status):
    if not status or not status.get("supported"):
        return "OFF"
    if status.get("connected"):
        return "ON"
    if status.get("connecting"):
        return "JOIN"
    if status.get("active"):
        return "READY"
    return "OFF"


def draw_wifi_glyph(lcd, x, y, status):
    if not status or not status.get("supported"):
        lcd.hline(x, y + 5, 9, BLACK)
        lcd.hline(x, y + 1, 9, BLACK)
        return

    if status.get("connected"):
        bars = 3
    elif status.get("connecting"):
        bars = 2
    elif status.get("active"):
        bars = 1
    else:
        bars = 0

    for index in range(3):
        bar_h = (index + 1) * 2
        bar_x = x + (index * 3)
        bar_y = y + 6 - bar_h
        color = BLACK if index < bars else GRAY
        lcd.fill_rect(bar_x, bar_y, 2, bar_h, color)
    if bars == 0:
        lcd.hline(x, y + 1, 8, BLACK)


def draw_menu_bar(lcd, title=MENU_TITLE, wifi_status=None, active_menu=None, clock_text=None):
    lcd.fill_rect(0, 0, SCREEN_W, MENU_BAR_H, WHITE)
    lcd.hline(0, MENU_BAR_H - 1, SCREEN_W, BLACK)
    lcd.fill_rect(3, 3, 8, 8, BLACK)

    regions = menu_bar_regions(title, clock_text)
    lcd.text(regions["title"], regions["title_x"], 3, BLACK)

    wifi_x, wifi_y, wifi_w, wifi_h = regions["wifi_rect"]
    if active_menu == "wifi":
        lcd.fill_rect(wifi_x, wifi_y, wifi_w, wifi_h, BLACK)
        menu_text_color = WHITE
    else:
        menu_text_color = BLACK
    lcd.text(MENU_WIFI_LABEL, regions["wifi_x"], 3, menu_text_color)

    status_text = _wifi_status_text(wifi_status)
    if status_text != "OFF":
        lcd.text(status_text, regions["wifi_x"] + 42, 3, GRAY if active_menu == "wifi" else BLACK)

    draw_wifi_glyph(lcd, regions["glyph_x"], 3, wifi_status)
    lcd.text(regions["clock_text"], regions["clock_x"], 3, BLACK)


def draw_menu_dropdown(lcd, x, y, w, items, selected_index=None):
    height = (len(items) * MENU_DROPDOWN_ROW_H) + 4
    lcd.fill_rect(x, y, w, height, WHITE)
    lcd.rect(x, y, w, height, BLACK)

    for index in range(len(items)):
        item = items[index]
        row_y = y + 2 + (index * MENU_DROPDOWN_ROW_H)
        enabled = item.get("enabled", True)
        selected = enabled and index == selected_index
        if selected:
            lcd.fill_rect(x + 1, row_y, w - 2, MENU_DROPDOWN_ROW_H, BLACK)

        label = fit_text(item.get("label", ""), max(1, (w // 8) - 3))
        detail = fit_text(item.get("detail", ""), 5)
        label_color = WHITE if selected else (BLACK if enabled else GRAY)
        detail_color = WHITE if selected else GRAY
        lcd.text(label, x + 4, row_y + 3, label_color)
        if detail:
            lcd.text(detail, right_x(detail, 4, w, x), row_y + 3, detail_color)


def draw_desktop_background(lcd):
    lcd.fill(WHITE)
    for y in range(DESKTOP_TOP + 10, SCREEN_H, 18):
        lcd.hline(0, y, SCREEN_W, GRAY)


def draw_window_shell(lcd, title, wifi_status=None):
    draw_desktop_background(lcd)
    draw_menu_bar(lcd, MENU_TITLE, wifi_status)
    lcd.fill_rect(WINDOW_X, WINDOW_Y, WINDOW_W, WINDOW_H, WHITE)
    lcd.rect(WINDOW_X, WINDOW_Y, WINDOW_W, WINDOW_H, BLACK)

    for y in range(WINDOW_Y + 2, WINDOW_Y + WINDOW_TITLE_H - 1, 2):
        lcd.hline(WINDOW_X + 14, y, WINDOW_W - 28, GRAY)

    lcd.fill_rect(WINDOW_X + 4, WINDOW_Y + 3, 6, 6, BLACK)
    title = fit_text(title, max(1, (WINDOW_W // 8) - 8))
    title_x = center_x(title, WINDOW_W, WINDOW_X)
    lcd.fill_rect(title_x - 3, WINDOW_Y + 1, (len(title) * 8) + 6, 10, WHITE)
    lcd.text(title, title_x, WINDOW_Y + 2, BLACK)
    lcd.hline(WINDOW_X + 1, WINDOW_FOOTER_Y, WINDOW_W - 2, BLACK)


def draw_window_footer(lcd, text, color=BLACK):
    max_chars = max(1, (WINDOW_CONTENT_W // 8) - 1)
    lcd.fill_rect(WINDOW_X + 1, WINDOW_FOOTER_Y + 1, WINDOW_W - 2, WINDOW_FOOTER_H - 1, WHITE)
    lcd.text(fit_text(text, max_chars), WINDOW_CONTENT_X, WINDOW_FOOTER_Y + 3, color)


def draw_window_footer_actions(lcd, left_text, right_text="", color=BLACK):
    lcd.fill_rect(WINDOW_X + 1, WINDOW_FOOTER_Y + 1, WINDOW_W - 2, WINDOW_FOOTER_H - 1, WHITE)
    if not right_text:
        lcd.text(fit_text(left_text, max(1, (WINDOW_CONTENT_W // 8) - 1)), WINDOW_CONTENT_X, WINDOW_FOOTER_Y + 3, color)
        return

    half_chars = max(1, ((WINDOW_CONTENT_W // 2) - 8) // 8)
    left_text = fit_text(left_text, half_chars)
    right_text = fit_text(right_text, half_chars)
    lcd.text(left_text, WINDOW_CONTENT_X, WINDOW_FOOTER_Y + 3, color)
    lcd.text(right_text, right_x(right_text, 8, WINDOW_W, WINDOW_X), WINDOW_FOOTER_Y + 3, color)


def draw_window_empty_state(lcd, title, lines, wifi_status=None, footer=HOME_HINT):
    draw_window_shell(lcd, title, wifi_status)
    y = WINDOW_CONTENT_Y + 12
    for line in lines:
        lcd.text(fit_text(line, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, BLACK)
        y += 18
    draw_window_footer(lcd, footer)


def draw_desktop_icon(lcd, x, y, w, h, title, selected, icon_fn):
    cx = x + (w // 2)
    cy = y + 12
    if selected:
        lcd.rect(cx - 14, y + 2, 28, 24, BLACK)

    icon_fn(lcd, cx, cy, True, True)

    label = fit_text(title, max(4, (w // 8) - 1))
    label_w = len(label) * 8
    label_x = x + max(0, (w - label_w) // 2)
    label_y = y + h - 11
    if selected:
        lcd.fill_rect(label_x - 2, label_y - 1, label_w + 4, 11, BLACK)
        lcd.text(label, label_x, label_y, WHITE)
    else:
        lcd.text(label, label_x, label_y, BLACK)


def draw_mouse_pointer(lcd, x, y):
    shape = (
        (0, 0),
        (0, 1),
        (1, 1),
        (0, 2),
        (1, 2),
        (2, 2),
        (0, 3),
        (1, 3),
        (2, 3),
        (3, 3),
        (0, 4),
        (1, 4),
        (2, 4),
        (0, 5),
        (1, 5),
        (0, 6),
        (3, 5),
        (4, 6),
        (5, 7),
        (3, 6),
        (2, 7),
    )
    for dx, dy in shape:
        px = x + dx
        py = y + dy
        if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
            lcd.pixel(px, py, BLACK)
