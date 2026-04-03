import time

from core.display import (
    SCREEN_W,
    SCREEN_H,
    BLACK,
    WHITE,
    GRAY,
    CYAN,
    YELLOW,
    TEAL,
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

TASKBAR_H = 20
TASKBAR_Y = SCREEN_H - TASKBAR_H
TASKBAR_START_W = 50
TASKBAR_TRAY_W = 68
START_MENU_W = 152
START_MENU_ROW_H = 16
DESKTOP_TOP = 2
DESKTOP_BOTTOM = TASKBAR_Y - 2

WINDOW_X = 6
WINDOW_Y = 6
WINDOW_W = SCREEN_W - (WINDOW_X * 2)
WINDOW_H = TASKBAR_Y - WINDOW_Y - 4
WINDOW_TITLE_H = 14
WINDOW_FOOTER_H = 16
WINDOW_CONTENT_X = WINDOW_X + 6
WINDOW_CONTENT_Y = WINDOW_Y + WINDOW_TITLE_H + 8
WINDOW_CONTENT_W = WINDOW_W - 12
WINDOW_CONTENT_BOTTOM = WINDOW_Y + WINDOW_H - WINDOW_FOOTER_H - 5
WINDOW_CONTENT_H = WINDOW_CONTENT_BOTTOM - WINDOW_CONTENT_Y
WINDOW_FOOTER_Y = WINDOW_Y + WINDOW_H - WINDOW_FOOTER_H
WINDOW_TEXT_CHARS = max(1, WINDOW_CONTENT_W // 8)

PANEL_BG = SILVER
PANEL_FIELD = LTGRAY
DESKTOP_BG = AQUA
TITLE_BG = NAVY
TITLE_HILITE = SKY
SELECTION_BG = NAVY
LIST_ROW_H = 14


def fit_text(text, max_chars):
    if text is None:
        return ""
    text = str(text)
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
        return "Pico"

    if not now or len(now) < 5:
        return "Pico"

    if now[0] < 2024:
        return "Pico"
    return "{:02d}:{:02d}".format(now[3], now[4])


def taskbar_regions(task_label="", clock_text=None):
    if clock_text is None:
        clock_text = menu_clock_text()
    clock_text = fit_text(clock_text, 6)

    start_rect = (2, TASKBAR_Y + 2, TASKBAR_START_W, TASKBAR_H - 4)
    tray_rect = (SCREEN_W - TASKBAR_TRAY_W - 2, TASKBAR_Y + 2, TASKBAR_TRAY_W, TASKBAR_H - 4)

    task_x = start_rect[0] + start_rect[2] + 4
    task_w = tray_rect[0] - task_x - 4
    if task_w < 36:
        task_w = 0

    return {
        "start_rect": start_rect,
        "task_rect": (task_x, TASKBAR_Y + 2, task_w, TASKBAR_H - 4),
        "tray_rect": tray_rect,
        "clock_text": clock_text,
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


def _split_label_lines(text, max_chars):
    text = str(text)
    if len(text) <= max_chars:
        return [text]

    if " " in text:
        words = text.split()
        if len(words) == 2 and len(words[0]) <= max_chars and len(words[1]) <= max_chars:
            return words

        first = words[0]
        second = " ".join(words[1:])
        if len(first) <= max_chars and len(second) <= max_chars:
            return [first, second]

    return [fit_text(text, max_chars)]


def _draw_window_controls(lcd, x, y):
    button_w = 10
    gap = 2
    names = ("min", "max", "close")
    for index, name in enumerate(names):
        bx = x + (index * (button_w + gap))
        _draw_bevel_box(lcd, bx, y, button_w, 10, PANEL_BG)
        if name == "min":
            lcd.hline(bx + 2, y + 7, 6, BLACK)
        elif name == "max":
            lcd.rect(bx + 2, y + 2, 6, 5, BLACK)
        else:
            lcd.line(bx + 2, y + 2, bx + 7, y + 7, BLACK)
            lcd.line(bx + 7, y + 2, bx + 2, y + 7, BLACK)


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


def draw_button(lcd, x, y, w, h, label, pressed=False, fill=PANEL_BG, text_color=BLACK):
    _draw_bevel_box(lcd, x, y, w, h, fill, pressed)
    label = fit_text(label, max(1, (w - 6) // 8))
    lcd.text(label, x + max(2, (w - (len(label) * 8)) // 2), y + max(0, (h - 8) // 2), text_color)


def draw_field(lcd, x, y, w, h, text, accent=None, text_color=BLACK):
    _draw_status_field(lcd, x, y, w, h, text, accent, text_color)


def draw_list_row(lcd, x, y, w, label, selected=False, lead="", detail="", text_color=BLACK, detail_color=GRAY):
    if selected:
        lcd.fill_rect(x, y, w, LIST_ROW_H, SELECTION_BG)
        text_color = WHITE
        detail_color = WHITE
    else:
        lcd.fill_rect(x, y, w, LIST_ROW_H, WHITE)

    lead_w = 0
    if lead:
        lcd.text(fit_text(lead, 2), x + 2, y + 3, text_color)
        lead_w = 12

    label_chars = max(1, ((w - lead_w - 8) // 8) - (len(detail) + 1 if detail else 0))
    lcd.text(fit_text(label, label_chars), x + 2 + lead_w, y + 3, text_color)
    if detail:
        lcd.text(fit_text(detail, 8), right_x(detail, 4, w, x), y + 3, detail_color)


def draw_dialog(lcd, title, lines, buttons=None, selected_button=0, width=176):
    buttons = buttons or []
    width = min(width, SCREEN_W - 20)
    line_count = max(1, len(lines))
    content_h = max(44, line_count * 16)
    button_h = 24 if buttons else 0
    height = 22 + content_h + button_h + 10
    x = (SCREEN_W - width) // 2
    y = max(6, (TASKBAR_Y - height) // 2)

    _draw_bevel_box(lcd, x, y, width, height, PANEL_BG)
    _draw_title_band(lcd, x + 3, y + 2, width - 6, 12, title, logo=True)

    text_y = y + 22
    max_chars = max(1, (width - 18) // 8)
    for line in lines:
        lcd.text(fit_text(line, max_chars), x + 9, text_y, BLACK)
        text_y += 16

    if not buttons:
        return

    button_w = max(44, min(68, (width - 16 - (len(buttons) - 1) * 6) // len(buttons)))
    row_w = (button_w * len(buttons)) + ((len(buttons) - 1) * 6)
    bx = x + max(8, (width - row_w) // 2)
    by = y + height - 28
    for index, label in enumerate(buttons):
        draw_button(lcd, bx + index * (button_w + 6), by, button_w, 18, label, index == selected_button)


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


def draw_taskbar(lcd, wifi_status=None, active_task="", focus=None, start_open=False):
    _draw_bevel_box(lcd, 0, TASKBAR_Y, SCREEN_W, TASKBAR_H, PANEL_BG)
    regions = taskbar_regions(active_task)

    sx, sy, sw, sh = regions["start_rect"]
    _draw_bevel_box(lcd, sx, sy, sw, sh, PANEL_BG, start_open or focus == "start")
    _draw_win_logo(lcd, sx + 4, sy + 4, 2)
    lcd.text("Start", sx + 14, sy + 5, BLACK)

    if active_task:
        tx, ty, tw, th = regions["task_rect"]
        if tw > 0:
            _draw_bevel_box(lcd, tx, ty, tw, th, PANEL_BG, True)
            lcd.text(fit_text(active_task, max(1, (tw - 8) // 8)), tx + 4, ty + 5, BLACK)

    tray_x, tray_y, tray_w, tray_h = regions["tray_rect"]
    _draw_bevel_box(lcd, tray_x, tray_y, tray_w, tray_h, PANEL_FIELD, True)
    if focus == "tray":
        lcd.rect(tray_x + 2, tray_y + 2, tray_w - 4, tray_h - 4, SELECTION_BG)
    draw_wifi_glyph(lcd, tray_x + 5, tray_y + 5, wifi_status)
    clock_text = regions["clock_text"]
    lcd.text(clock_text, right_x(clock_text, 5, tray_w, tray_x), tray_y + 5, BLACK)


def draw_start_menu(lcd, items, selected_index=0):
    width = START_MENU_W
    height = 24 + (len(items) * START_MENU_ROW_H) + 6
    x = 2
    y = TASKBAR_Y - height - 2
    _draw_bevel_box(lcd, x, y, width, height, PANEL_BG)
    lcd.fill_rect(x + 2, y + 2, 16, height - 4, TITLE_BG)
    _draw_win_logo(lcd, x + 5, y + 6, 3)
    lcd.text("PicoOS", x + 24, y + 6, BLACK)

    row_x = x + 20
    row_w = width - 24
    row_y = y + 22
    for index, item in enumerate(items):
        selected = index == selected_index
        if selected:
            lcd.fill_rect(row_x + 2, row_y, row_w - 4, START_MENU_ROW_H, SELECTION_BG)
        label_color = WHITE if selected else BLACK
        detail_color = WHITE if selected else GRAY
        label = fit_text(item.get("label", ""), max(1, (row_w // 8) - 4))
        detail = fit_text(item.get("detail", ""), 7)
        lcd.text(label, row_x + 4, row_y + 4, label_color)
        if detail:
            lcd.text(detail, right_x(detail, 4, row_w, row_x), row_y + 4, detail_color)
        row_y += START_MENU_ROW_H


def draw_desktop_background(lcd):
    lcd.fill(DESKTOP_BG)


def draw_window_shell(lcd, title, wifi_status=None):
    draw_desktop_background(lcd)
    draw_taskbar(lcd, wifi_status, title)

    _draw_bevel_box(lcd, WINDOW_X, WINDOW_Y, WINDOW_W, WINDOW_H, PANEL_BG)
    lcd.fill_rect(
        WINDOW_X + 3,
        WINDOW_Y + WINDOW_TITLE_H + 1,
        WINDOW_W - 6,
        WINDOW_H - WINDOW_TITLE_H - 4,
        WHITE,
    )

    title_w = WINDOW_W - 42
    _draw_title_band(
        lcd,
        WINDOW_X + 3,
        WINDOW_Y + 2,
        title_w,
        WINDOW_TITLE_H - 1,
        fit_text(title, max(1, (title_w - 16) // 8)),
        logo=True,
    )
    _draw_window_controls(lcd, WINDOW_X + WINDOW_W - 37, WINDOW_Y + 4)
    lcd.hline(WINDOW_X + 2, WINDOW_FOOTER_Y - 1, WINDOW_W - 4, GRAY)


def draw_window_footer(lcd, text, color=BLACK):
    lcd.fill_rect(WINDOW_X + 2, WINDOW_FOOTER_Y, WINDOW_W - 4, WINDOW_FOOTER_H, PANEL_BG)
    _draw_status_field(
        lcd,
        WINDOW_X + 4,
        WINDOW_FOOTER_Y + 2,
        WINDOW_W - 8,
        WINDOW_FOOTER_H - 4,
        text,
        _status_accent(color),
    )


def draw_window_footer_actions(lcd, left_text, right_text="", color=BLACK):
    lcd.fill_rect(WINDOW_X + 2, WINDOW_FOOTER_Y, WINDOW_W - 4, WINDOW_FOOTER_H, PANEL_BG)
    if not right_text:
        _draw_status_field(
            lcd,
            WINDOW_X + 4,
            WINDOW_FOOTER_Y + 2,
            WINDOW_W - 8,
            WINDOW_FOOTER_H - 4,
            left_text,
            _status_accent(color),
        )
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


def draw_desktop_icon(lcd, x, y, w, h, title, selected, icon_fn):
    cx = x + (w // 2)
    cy = y + 14
    if selected:
        _draw_bevel_box(lcd, cx - 18, y + 2, 36, 30, PANEL_BG)

    icon_fn(lcd, cx, cy, True, True)

    lines = _split_label_lines(title, max(4, (w // 8) - 1))
    line_y = y + h - (19 if len(lines) > 1 else 11)
    for line in lines:
        label_w = len(line) * 8
        label_x = x + max(0, (w - label_w) // 2)
        if selected:
            lcd.fill_rect(label_x - 2, line_y - 1, label_w + 4, 10, SELECTION_BG)
        lcd.text(line, label_x, line_y, WHITE)
        line_y += 9


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
