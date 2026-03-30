import time

from core.display import (
    SCREEN_W,
    SCREEN_H,
    BLACK,
    WHITE,
    GRAY,
    CYAN,
    YELLOW,
    DKGRN,
    TEAL,
    SLATE,
    RED,
    GREEN,
    BLUE,
    ORANGE,
    SILVER,
    LTGRAY,
    DARKGRAY,
    NAVY,
    SKY,
    AQUA,
    CREAM,
)
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

PANEL_BG = SILVER
PANEL_FIELD = LTGRAY
DESKTOP_BG = AQUA
TITLE_BG = NAVY
TITLE_HILITE = SKY
SELECTION_BG = NAVY


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
    title_x = 22
    title_w = len(title) * 8
    wifi_w = 76
    wifi_x = title_x + title_w + 14

    if clock_text is None:
        clock_text = menu_clock_text()
    clock_text = fit_text(clock_text, 6)
    clock_w = len(clock_text) * 8
    clock_box_w = max(40, clock_w + 22)
    clock_box_x = SCREEN_W - clock_box_w - 4
    glyph_x = clock_box_x + 4
    clock_x = glyph_x + 11

    return {
        "title": title,
        "title_x": title_x,
        "wifi_x": wifi_x,
        "wifi_w": wifi_w,
        "wifi_status_x": wifi_x + 42,
        "wifi_rect": (wifi_x - 4, 1, wifi_w, MENU_BAR_H - 2),
        "clock_text": clock_text,
        "clock_x": clock_x,
        "glyph_x": glyph_x,
        "clock_box": (clock_box_x, 1, clock_box_w, MENU_BAR_H - 2),
    }


def _draw_bevel_box(lcd, x, y, w, h, fill, pressed=False):
    if w <= 0 or h <= 0:
        return

    lcd.fill_rect(x, y, w, h, fill)
    if w < 2 or h < 2:
        return

    if pressed:
        top_outer = BLACK
        top_inner = DARKGRAY
        bottom_inner = LTGRAY
        bottom_outer = WHITE
    else:
        top_outer = WHITE
        top_inner = LTGRAY
        bottom_inner = DARKGRAY
        bottom_outer = BLACK

    lcd.hline(x, y, w - 1, top_outer)
    lcd.vline(x, y, h - 1, top_outer)
    lcd.hline(x, y + h - 1, w, bottom_outer)
    lcd.vline(x + w - 1, y, h, bottom_outer)

    if w > 2 and h > 2:
        lcd.hline(x + 1, y + 1, w - 2, top_inner)
        lcd.vline(x + 1, y + 1, h - 2, top_inner)
        lcd.hline(x + 1, y + h - 2, w - 2, bottom_inner)
        lcd.vline(x + w - 2, y + 1, h - 2, bottom_inner)


def _draw_win_logo(lcd, x, y, size=2):
    gap = 1
    lcd.fill_rect(x, y, size, size, RED)
    lcd.fill_rect(x + size + gap, y, size, size, YELLOW)
    lcd.fill_rect(x, y + size + gap, size, size, GREEN)
    lcd.fill_rect(x + size + gap, y + size + gap, size, size, BLUE)


def _draw_title_band(lcd, x, y, w, h, title, accent=None, logo=False):
    lcd.fill_rect(x, y, w, h, TITLE_BG)
    if w > 2 and h > 2:
        lcd.hline(x + 1, y + 1, w - 2, TITLE_HILITE)

    text_x = x + 4
    if logo:
        _draw_win_logo(lcd, x + 3, y + 2, 2)
        text_x = x + 12
    elif accent is not None and h > 4:
        lcd.fill_rect(x + 2, y + 2, 4, h - 4, accent)
        text_x = x + 10

    max_chars = max(1, (w - (text_x - x) - 4) // 8)
    lcd.text(fit_text(title, max_chars), text_x, y + max(0, (h - 8) // 2), WHITE)


def _draw_status_field(lcd, x, y, w, h, text, accent=None, text_color=BLACK):
    _draw_bevel_box(lcd, x, y, w, h, PANEL_FIELD, True)

    text_x = x + 4
    if accent is not None and h > 6:
        lcd.fill_rect(x + 3, y + 3, 4, h - 6, accent)
        text_x = x + 10

    max_chars = max(1, (w - (text_x - x) - 3) // 8)
    lcd.text(fit_text(text, max_chars), text_x, y + max(0, (h - 8) // 2), text_color)


def _status_accent(color):
    if color in (BLACK, GRAY, WHITE, PANEL_BG, PANEL_FIELD):
        return None
    return color


def draw_header(lcd, title, detail="", color=CYAN):
    max_title = max(1, (SCREEN_W // 8) - 8)
    title = fit_text(title, max_title)
    _draw_bevel_box(lcd, 0, 0, SCREEN_W, HEADER_H, PANEL_BG)
    _draw_title_band(lcd, 3, 3, SCREEN_W - 6, HEADER_H - 6, title, _status_accent(color))
    if detail:
        max_detail = max(1, min(10, (SCREEN_W // 8) - len(title) - 3))
        detail = fit_text(detail, max_detail)
        lcd.text(detail, right_x(detail, 6), TEXT_Y_HEADER, YELLOW)


def draw_footer(lcd, text, color=GRAY):
    footer_y = SCREEN_H - FOOTER_H
    _draw_bevel_box(lcd, 0, footer_y, SCREEN_W, FOOTER_H, PANEL_BG)
    _draw_status_field(lcd, 4, footer_y + 3, SCREEN_W - 8, FOOTER_H - 6, text, _status_accent(color))


def draw_footer_actions(lcd, left_text, right_text="", color=GRAY):
    footer_y = SCREEN_H - FOOTER_H
    _draw_bevel_box(lcd, 0, footer_y, SCREEN_W, FOOTER_H, PANEL_BG)
    if not right_text:
        _draw_status_field(lcd, 4, footer_y + 3, SCREEN_W - 8, FOOTER_H - 6, left_text, _status_accent(color))
        return

    field_y = footer_y + 3
    field_h = FOOTER_H - 6
    left_w = (SCREEN_W - 12) // 2
    right_w = SCREEN_W - left_w - 12
    accent = _status_accent(color)
    _draw_status_field(lcd, 4, field_y, left_w, field_h, left_text, accent)
    _draw_status_field(lcd, 8 + left_w, field_y, right_w, field_h, right_text, accent)


def draw_tile(lcd, x, y, w, h, title, selected, accent, icon_fn, monochrome=False):
    if monochrome:
        border = WHITE
        fill = WHITE if selected else BLACK
        text_color = BLACK if selected else WHITE
        lcd.fill_rect(x, y, w, h, fill)
        lcd.rect(x, y, w, h, border)
    else:
        fill = PANEL_BG
        text_color = WHITE if selected else BLACK
        _draw_bevel_box(lcd, x, y, w, h, fill, selected)
        if selected:
            lcd.fill_rect(x + 3, y + 3, w - 6, 8, TITLE_BG)
            lcd.fill_rect(x + 4, y + 4, 4, 6, accent)

    icon_fn(lcd, x + (w // 2), y + max(20, h // 3), selected, monochrome)

    max_chars = max(4, (w // 8) - 2)
    label = fit_text(title, max_chars)
    label_x = x + max(3, (w - (len(label) * 8)) // 2)
    label_y = y + h - 16
    if not monochrome and selected:
        lcd.fill_rect(label_x - 2, label_y - 1, (len(label) * 8) + 4, 11, SELECTION_BG)
    lcd.text(label, label_x, label_y, text_color)


def draw_empty_state(lcd, title, lines, accent=TEAL, footer=HOME_HINT):
    lcd.fill(DESKTOP_BG)
    draw_header(lcd, title, color=accent)
    panel_h = min(CONTENT_H, max(54, (len(lines) * 18) + 18))
    _draw_bevel_box(lcd, CONTENT_LEFT, CONTENT_TOP + 6, SCREEN_W - 8, panel_h, CREAM)
    y = CONTENT_TOP + 18
    for line in lines:
        lcd.text(fit_text(line, 26), CONTENT_LEFT + 8, y, BLACK)
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
    _draw_bevel_box(lcd, 0, 0, SCREEN_W, MENU_BAR_H, PANEL_BG)
    _draw_win_logo(lcd, 4, 3, 2)

    regions = menu_bar_regions(title, clock_text)
    title_w = (len(regions["title"]) * 8) + 8
    _draw_bevel_box(lcd, regions["title_x"] - 4, 1, title_w, MENU_BAR_H - 2, PANEL_BG)
    lcd.text(regions["title"], regions["title_x"], 3, BLACK)

    wifi_x, wifi_y, wifi_w, wifi_h = regions["wifi_rect"]
    _draw_bevel_box(lcd, wifi_x, wifi_y, wifi_w, wifi_h, PANEL_BG, active_menu == "wifi")
    lcd.text(MENU_WIFI_LABEL, regions["wifi_x"], 3, BLACK)

    status_text = _wifi_status_text(wifi_status)
    if status_text != "OFF":
        lcd.text(status_text, regions["wifi_status_x"], 3, BLACK)

    _draw_bevel_box(lcd, *regions["clock_box"], PANEL_FIELD, True)
    draw_wifi_glyph(lcd, regions["glyph_x"], 3, wifi_status)
    lcd.text(regions["clock_text"], regions["clock_x"], 3, BLACK)


def draw_menu_dropdown(lcd, x, y, w, items, selected_index=None):
    height = (len(items) * MENU_DROPDOWN_ROW_H) + 4
    _draw_bevel_box(lcd, x, y, w, height, PANEL_BG)

    for index in range(len(items)):
        item = items[index]
        row_y = y + 2 + (index * MENU_DROPDOWN_ROW_H)
        enabled = item.get("enabled", True)
        selected = enabled and index == selected_index
        if selected:
            lcd.fill_rect(x + 2, row_y, w - 4, MENU_DROPDOWN_ROW_H, SELECTION_BG)

        label = fit_text(item.get("label", ""), max(1, (w // 8) - 3))
        detail = fit_text(item.get("detail", ""), 5)
        label_color = WHITE if selected else (BLACK if enabled else GRAY)
        detail_color = WHITE if selected else DARKGRAY
        lcd.text(label, x + 4, row_y + 3, label_color)
        if detail:
            lcd.text(detail, right_x(detail, 4, w, x), row_y + 3, detail_color)


def draw_desktop_background(lcd):
    lcd.fill(DESKTOP_BG)


def draw_window_shell(lcd, title, wifi_status=None):
    draw_desktop_background(lcd)
    draw_menu_bar(lcd, MENU_TITLE, wifi_status)
    _draw_bevel_box(lcd, WINDOW_X, WINDOW_Y, WINDOW_W, WINDOW_H, PANEL_BG)
    lcd.fill_rect(WINDOW_X + 3, WINDOW_Y + WINDOW_TITLE_H + 1, WINDOW_W - 6, WINDOW_H - WINDOW_TITLE_H - 4, WHITE)
    _draw_title_band(lcd, WINDOW_X + 3, WINDOW_Y + 2, WINDOW_W - 6, WINDOW_TITLE_H - 3, fit_text(title, max(1, (WINDOW_W // 8) - 6)), logo=True)
    lcd.hline(WINDOW_X + 2, WINDOW_FOOTER_Y - 1, WINDOW_W - 4, GRAY)


def draw_window_footer(lcd, text, color=BLACK):
    lcd.fill_rect(WINDOW_X + 2, WINDOW_FOOTER_Y, WINDOW_W - 4, WINDOW_FOOTER_H, PANEL_BG)
    _draw_status_field(lcd, WINDOW_X + 4, WINDOW_FOOTER_Y + 2, WINDOW_W - 8, WINDOW_FOOTER_H - 4, text, _status_accent(color))


def draw_window_footer_actions(lcd, left_text, right_text="", color=BLACK):
    lcd.fill_rect(WINDOW_X + 2, WINDOW_FOOTER_Y, WINDOW_W - 4, WINDOW_FOOTER_H, PANEL_BG)
    if not right_text:
        _draw_status_field(lcd, WINDOW_X + 4, WINDOW_FOOTER_Y + 2, WINDOW_W - 8, WINDOW_FOOTER_H - 4, left_text, _status_accent(color))
        return

    field_y = WINDOW_FOOTER_Y + 2
    field_h = WINDOW_FOOTER_H - 4
    left_w = (WINDOW_W - 12) // 2
    right_w = WINDOW_W - left_w - 12
    accent = _status_accent(color)
    _draw_status_field(lcd, WINDOW_X + 4, field_y, left_w, field_h, left_text, accent)
    _draw_status_field(lcd, WINDOW_X + 8 + left_w, field_y, right_w, field_h, right_text, accent)


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
        _draw_bevel_box(lcd, cx - 16, y + 1, 32, 28, PANEL_BG)

    icon_fn(lcd, cx, cy, True, True)

    label = fit_text(title, max(4, (w // 8) - 1))
    label_w = len(label) * 8
    label_x = x + max(0, (w - label_w) // 2)
    label_y = y + h - 11
    if selected:
        lcd.fill_rect(label_x - 2, label_y - 1, label_w + 4, 11, SELECTION_BG)
        lcd.text(label, label_x, label_y, WHITE)
    else:
        lcd.text(label, label_x, label_y, WHITE)


def draw_mouse_pointer(lcd, x, y):
    outline = (
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
    fill = (
        (1, 2),
        (1, 3),
        (2, 3),
        (1, 4),
        (2, 4),
        (1, 5),
        (4, 6),
    )

    for dx, dy in fill:
        px = x + dx
        py = y + dy
        if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
            lcd.pixel(px, py, WHITE)

    for dx, dy in outline:
        px = x + dx
        py = y + dy
        if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
            lcd.pixel(px, py, BLACK)
