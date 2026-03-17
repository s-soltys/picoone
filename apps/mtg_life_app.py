from core.display import BLACK, WHITE, GRAY, RED, GREEN, CYAN
from core.controls import A_LABEL, B_LABEL, X_LABEL, Y_LABEL
from core.ui import (
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_window_shell,
    draw_window_footer,
    fit_text,
    right_x,
)


SEGMENTS = {
    "0": "abcedf",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
    "-": "g",
}


class MTGLifeCounterApp:
    app_id = "mtg-life"
    title = "MTG Life"
    accent = RED
    launch_mode = "window"

    def __init__(self):
        self.life = [40, 40, 40, 40]
        self.selected = 0
        self.reset_latched = False

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else (WHITE if monochrome else RED)
        detail = BLACK if monochrome and selected else (WHITE if monochrome else GREEN)
        lcd.rect(cx - 9, cy - 8, 18, 18, ink)
        lcd.vline(cx, cy - 7, 16, detail)
        lcd.hline(cx - 8, cy + 1, 16, detail)
        lcd.fill_rect(cx - 3, cy - 3, 6, 6, detail)

    def on_open(self, runtime):
        self.reset_latched = False

    def _grid_rect(self, index):
        gap = 6
        top = WINDOW_CONTENT_Y + 18
        width = (WINDOW_CONTENT_W - gap) // 2
        height = (WINDOW_CONTENT_BOTTOM - top - 26 - gap) // 2
        col = index % 2
        row = index // 2
        x = WINDOW_CONTENT_X + (col * (width + gap))
        y = top + (row * (height + gap))
        return x, y, width, height

    def _set_selected(self, row, col):
        row = max(0, min(1, row))
        col = max(0, min(1, col))
        self.selected = (row * 2) + col

    def _move_selected(self, dx=0, dy=0):
        row = self.selected // 2
        col = self.selected % 2
        self._set_selected(row + dy, col + dx)

    def _adjust_selected(self, delta):
        self.life[self.selected] += delta

    def _reset_match(self):
        for index in range(4):
            self.life[index] = 40

    def _draw_segment_char(self, lcd, x, y, char, color):
        width = 14
        height = 24
        thick = 2
        segments = SEGMENTS.get(char, "")

        if "a" in segments:
            lcd.fill_rect(x + thick, y, width - (thick * 2), thick, color)
        if "b" in segments:
            lcd.fill_rect(x + width - thick, y + thick, thick, (height // 2) - thick, color)
        if "c" in segments:
            lcd.fill_rect(x + width - thick, y + (height // 2), thick, (height // 2) - thick, color)
        if "d" in segments:
            lcd.fill_rect(x + thick, y + height - thick, width - (thick * 2), thick, color)
        if "e" in segments:
            lcd.fill_rect(x, y + (height // 2), thick, (height // 2) - thick, color)
        if "f" in segments:
            lcd.fill_rect(x, y + thick, thick, (height // 2) - thick, color)
        if "g" in segments:
            lcd.fill_rect(x + thick, y + (height // 2) - 1, width - (thick * 2), thick, color)

    def _draw_total(self, lcd, x, y, width, value, color):
        text = str(value)
        if len(text) > 3:
            text = "999" if value > 0 else "-99"

        char_w = 16
        total_w = len(text) * char_w
        start_x = x + max(2, (width - total_w) // 2)
        for index in range(len(text)):
            self._draw_segment_char(lcd, start_x + (index * char_w), y, text[index], color)

    def _draw_player_panel(self, lcd, index):
        x, y, w, h = self._grid_rect(index)
        selected = index == self.selected
        life = self.life[index]
        fill = BLACK if selected else WHITE
        border = CYAN if selected else BLACK
        text_color = WHITE if selected else BLACK
        sub_color = CYAN if selected else GRAY

        lcd.fill_rect(x, y, w, h, fill)
        lcd.rect(x, y, w, h, border)
        lcd.text("P" + str(index + 1), x + 6, y + 5, sub_color)
        if life <= 0:
            lcd.text("OUT", x + w - 30, y + 5, RED if selected else BLACK)
        else:
            lcd.text("40", x + w - 22, y + 5, sub_color)

        self._draw_total(lcd, x, y + 20, w, life, text_color)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if buttons.repeat("LEFT", 180, 100):
            self._move_selected(dx=-1)
        if buttons.repeat("RIGHT", 180, 100):
            self._move_selected(dx=1)
        if buttons.repeat("UP", 180, 100):
            self._move_selected(dy=-1)
        if buttons.repeat("DOWN", 180, 100):
            self._move_selected(dy=1)

        reset_combo = buttons.down("X") and buttons.down("Y")
        if reset_combo:
            if not self.reset_latched:
                self._reset_match()
                self.reset_latched = True
        else:
            self.reset_latched = False
            if buttons.repeat("A", 260, 110):
                self._adjust_selected(-1)
            if buttons.repeat("B", 260, 110):
                self._adjust_selected(1)
            if buttons.repeat("X", 260, 110):
                self._adjust_selected(-5)
            if buttons.repeat("Y", 260, 110):
                self._adjust_selected(5)

        draw_window_shell(lcd, "MTG Life Counter", runtime.wifi.status())
        lcd.text("Commander / 4 players", WINDOW_CONTENT_X, WINDOW_CONTENT_Y, BLACK)
        lcd.text(fit_text("X+Y reset", 10), right_x("X+Y reset", 0, WINDOW_CONTENT_W, WINDOW_CONTENT_X), WINDOW_CONTENT_Y, GRAY)

        for index in range(4):
            self._draw_player_panel(lcd, index)

        legend_y = WINDOW_CONTENT_BOTTOM - 18
        lcd.text(fit_text(A_LABEL + " -1", 11), WINDOW_CONTENT_X, legend_y, BLACK)
        lcd.text(fit_text(B_LABEL + " +1", 12), WINDOW_CONTENT_X + 88, legend_y, BLACK)
        lcd.text(fit_text(X_LABEL + " -5", 6), WINDOW_CONTENT_X, legend_y + 10, GRAY)
        lcd.text(fit_text(Y_LABEL + " +5", 6), WINDOW_CONTENT_X + 88, legend_y + 10, GRAY)
        draw_window_footer(lcd, "D-pad seat", BLACK)
        return None
