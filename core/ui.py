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


def fit_text(text, max_chars):
    if text is None:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[: max_chars - 1] + "."


def center_x(text, width=SCREEN_W):
    return max(0, (width - len(text) * 8) // 2)


def right_x(text, margin=4):
    return max(margin, SCREEN_W - (len(text) * 8) - margin)


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
